"""Import XLSX de la mise en forme documentée, sans recalculer une formule."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re
import unicodedata
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from .referentiel import CATALOGUE, DIMS, LEVELS, REGIONS, TABLES
from .qualite import reconcile

VERSION = "1.0.0"
EXPECTED_SHEETS = {"PRESCOLAIRE", *(f"Feuil{n}" for n in range(1, 14))}
COUNT_UNITS = {"eleves", "ecoles", "salles", "structures", "personnes"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def slug(value):
    base = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return "-".join(re.findall(r"[a-z0-9]+", base.lower()))


def metadata(path):
    return dict(source=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                imported_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), importer_version=VERSION)


def workbook_checks(path):
    """Limiter les documents décompressés, refuser les contenus actifs et les objets incorporés."""
    require(path.stat().st_size <= 12_000_000, "Fichier trop volumineux (limite de 12 Mo).")
    try:
        with ZipFile(path) as z:
            items = z.infolist()
            require(len(items) < 2500 and sum(i.file_size for i in items) < 32_000_000,
                    "Le contenu décompressé dépasse la limite d’import.")
            require(not any(any(s in i.filename.lower() for s in ("vbaproject", "/embeddings/", "/activex/", "/macrosheets/"))
                            for i in items), "Contenu actif ou objet incorporé refusé.")
            require(not any(i.flag_bits & 1 for i in items), "Le classeur est chiffré.")
            for i in items:
                if i.filename.lower().endswith((".xml", ".rels")):
                    xml = z.read(i)
                    require(b"\x00" not in xml, "Encodage XML incompatible avec le gabarit UTF-8.")
                    require(not re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", xml, flags=re.I), "Déclarations XML externes refusées.")
                    if i.filename.startswith("xl/worksheets/sheet") and i.filename.endswith(".xml"):
                        # Vérifier les références avant qu'openpyxl matérialise les cellules fusionnées.
                        for col, row in re.findall(br'\b(?:ref|r)="(?:[^"]*:)?([A-Z]{1,3})([0-9]{1,7})"', xml):
                            require(len(col) < 3 and (len(col)==1 or col <= b"DP") and int(row) <= 500,
                                    "Dimensions de feuille hors du gabarit pris en charge.")
    except BadZipFile as exc:
        raise ValueError("Le fichier ne contient pas de classeur XLSX lisible.") from exc


def canonical(axis, raw):
    token = slug(raw)
    if token in {"total", "total-general", "national", "burkina-faso"}:
        return "national" if axis == "region" else "total"
    token = token.removeprefix("total-")
    token = {"haut-bassins":"hauts-bassins", "g":"garcons", "f":"filles", "t":"total"}.get(token, token)
    valid = {"region": REGIONS, "sex": ("garcons", "filles", "total"),
             "status": ("public", "prive", "communautaire"), "area": ("urbain", "rural", "indetermine"),
             "level": (*LEVELS["primaire"], *LEVELS["prescolaire"])}
    require(token in valid[axis], f"Modalité {axis} inconnue dans la table. Vérifier les libellés du gabarit.")
    return token


def end_year(value):
    match = re.fullmatch(r"(\d{4})(?:[-/](\d{4}|\d{2}))?", value)
    require(match, "En-tête de période non reconnu.")
    start = int(match[1])
    if not match[2]:
        return start
    year = int(match[2])
    year += (start // 100) * 100 if year < 100 else 0
    require(year == start+1, "Année scolaire non consécutive.")
    return year


def normalize(raw, unit, format_code):
    if raw is None:
        return None, "missing", []
    transforms = []
    if isinstance(raw, str):
        token = raw.strip()
        if token.lower() in ("", "-", "—", "nd", "n.d.", "n/d", "non disponible"):
            return None, "missing", []
        if token.lower() in ("n/a", "s.o.", "sans objet", "non applicable"):
            return None, "not_applicable", []
        if not re.fullmatch(r"\d+(?:[.,]\d+)?", token):
            return None, "invalid", []
        value = float(token.replace(",", "."))
        transforms.append("texte_numerique")
    elif type(raw) in (int, float):
        value = raw
    else:
        return None, "invalid", []
    if "%" in format_code and unit == "pourcent":
        value *= 100
        transforms.append("format_pourcent_vers_points")
    if not math.isfinite(value) or value < 0 or (unit in COUNT_UNITS and value != int(value)):
        return None, "invalid", transforms
    return int(value) if unit in COUNT_UNITS else value, "available", transforms


class Reader:
    def __init__(self, path, book, cached):
        self.path, self.book, self.cached = path, book, cached
        self.meta = metadata(path)
        self.meta["version"] = self.meta["sha256"]
        self.observations, self.anomalies, self.tables = [], [], []
        self.visited = {s: set() for s in book.sheetnames}
        self.checks = Counter()
        self.formulas = 0

    def note(self, code, message, cell, table=None, severity="warning", **extra):
        self.anomalies.append(dict(code=code,message=message,severity=severity,sheet=cell.parent.title,
                                   cell=cell.coordinate,table=table.id if table else None,region=None,year=None) | extra)

    def isolate(self, cell, table=None):
        self.note("texte_isole", "Contenu extérieur à la structure statistique isolé dans le fichier source.",
                  cell, table, "info", raw_hash=hashlib.sha256(str(cell.value).encode()).hexdigest())

    def headings(self, table, sheet):
        """Lire uniquement les colonnes de période réellement présentes dans cette table."""
        header = table.anchor+1
        col, result = table.first_col, []
        while col <= sheet.max_column:
            cell = sheet.cell(header, col)
            if cell.value is None:
                break
            lines = str(cell.value).strip().splitlines()
            year = end_year(lines[0].strip())
            if len(lines) > 1:
                self.isolate(cell, table)
            expected = (result[-1][1]+1 if result else table.first_year)
            require(year == expected and year <= 2050, f"Période manquante ou répétée dans {table.id}, {cell.coordinate}.")
            width = 3 if table.grouped_sex else 1
            for k in range(width):
                sex = canonical("sex", sheet.cell(header+1,col+k).value) if table.grouped_sex else None
                require(not table.grouped_sex or sex == ("garcons","filles","total")[k],
                        f"En-tête de sexe incompatible dans {table.id}.")
                result.append((col+k, year, sex, lines[0].strip()))
            col += width
        require(result and result[-1][1] >= 2025, f"Période de référence incomplète dans {table.id}.")
        for later in range(col+1, sheet.max_column+1):
            token = str(sheet.cell(header,later).value or "").splitlines()
            require(not token or not re.fullmatch(r"\d{4}(?:[-/]\d{2,4})?",token[0].strip()),
                    f"Colonne de période isolée dans {table.id}.")
        return result

    def dimensions(self, table, sheet, row, carry):
        raw = {}
        for idx, axis in enumerate(table.dims):
            value = sheet.cell(row,idx+1).value
            if value is not None:
                carry[axis] = value
                for dependent in table.dims[idx+1:]:
                    carry.pop(dependent,None)
            previous = carry.get(axis)
            if previous is None and idx:
                previous = "TOTAL" if str(raw[table.dims[idx-1]]).lower().startswith("total") else None
            require(previous is not None, f"Dimension manquante en {sheet.title}!{get_column_letter(idx+1)}{row}.")
            raw[axis] = str(previous)
        dims = {axis:canonical(axis,v) for axis,v in raw.items()}
        return raw, dims

    def read_table(self, t):
        sheet = self.book[t.sheet]
        title = sheet.cell(t.anchor,1)
        require(re.match(rf"^Tableau\s+{int(t.id[-2:])}\s*:",str(title.value).replace("\xa0"," ")),
                f"Tableau attendu absent en {t.sheet}!A{t.anchor}.")
        columns = self.headings(t,sheet)
        years = sorted(set(c[1] for c in columns))
        for r in range(t.anchor,t.last_row+1):
            for c in range(1,columns[-1][0]+1):
                self.visited[t.sheet].add((r,c))
        carry, seen = {}, set()
        unit = CATALOGUE[t.indicator]["unit"]
        for row in range(t.first_row,t.last_row+1):
            raw_dims, row_dims = self.dimensions(t,sheet,row,carry)
            for col, year, col_sex, period_header in columns:
                dims = dict.fromkeys(DIMS)
                dims.update(region="national")
                dims.update(row_dims)
                original_dims = dict(raw_dims)
                if col_sex is not None:
                    dims["sex"] = col_sex
                    original_dims["sex"] = sheet.cell(t.anchor+2,col).value
                key = (year, *dims.values())
                require(key not in seen, f"Observation dupliquée dans {t.id} pour {year}, {dims}.")
                seen.add(key)
                cell = sheet.cell(row,col)
                raw = cell.value
                formula = raw if cell.data_type == "f" else None
                cached = self.cached[t.sheet].cell(row,col).value if formula else raw
                value, state, changes = normalize(cached,unit,cell.number_format)
                if t.indicator == "reussite_cep" and value is not None and value > 100:
                    value, state = None, "invalid"
                if formula:
                    self.formulas += 1
                    changes.append("valeur_enregistree_de_formule")
                    if cached is None:
                        self.note("formule_sans_cache","Formule sans valeur enregistrée.",cell,t,year=year,region=dims["region"])
                    # Seules les formules de rapport direct sont contrôlées arithmétiquement.
                    expected = re.fullmatch(r"=(Feuil\d+)!([A-Z]+\d+)/(Feuil\d+)!([A-Z]+\d+)",formula)
                    if expected and expected[1] in self.cached and expected[3] in self.cached:
                        num = self.cached[expected[1]][expected[2]].value
                        den = self.cached[expected[3]][expected[4]].value
                        self.checks["valeurs_enregistrees_formules"] += 1
                        if (type(num) not in (int,float) or type(den) not in (int,float)
                                or den == 0 or value is None or not math.isclose(value, num/den, rel_tol=1e-9)):
                            self.note("cache_incoherent","Valeur enregistrée incompatible avec les cellules référencées.",cell,t,
                                      year=year,region=dims["region"])
                    else:
                        self.note("formule_a_examiner","Formule conservée avec sa valeur enregistrée, à vérifier.",cell,t,
                                  year=year,region=dims["region"])
                if state == "invalid":
                    self.note("valeur_invalide","Valeur hors domaine isolée. Le calcul conserve une valeur indisponible.",cell,t,
                              year=year,region=dims["region"])
                if raw_dims.get("region","").upper() == "HAUT-BASSINS":
                    changes.append("alias_haut_bassins")
                self.observations.append(dict(id=f"{t.id}:{cell.coordinate}",indicator=t.indicator,cycle=t.cycle,
                    year=year, **dims,unit=unit,value=value,state=state,origin="observed",table=t.id,sheet=t.sheet,
                    cell=cell.coordinate,raw=raw if isinstance(raw,(str,int,float,type(None))) else str(raw),
                    transforms=changes,source=self.meta["source"],version=self.meta["version"],
                    raw_dimensions=original_dims,period_header=period_header,cached_value=cached if formula else None))
        self.tables.append(dict(id=t.id,sheet=t.sheet,anchor=title.coordinate,cycle=t.cycle,indicator=t.indicator,
                                dimensions=[*t.dims, *(["sex"] if t.grouped_sex else [])],years=years,
                                start=years[0],end=years[-1], observations=len(seen),
                                range=f"A{t.anchor}:{get_column_letter(columns[-1][0])}{t.last_row}"))

    def read(self):
        require(set(self.book.sheetnames)==EXPECTED_SHEETS, "Les 14 feuilles attendues ne correspondent pas au classeur.")
        for t in TABLES:
            self.read_table(t)
        for s in self.book:
            for row in s.iter_rows():
                for cell in row:
                    if cell.value is not None and (cell.row,cell.column) not in self.visited[s.title]:
                        self.isolate(cell)
        checks, anomalies = reconcile(self.observations)
        self.checks.update(checks)
        self.anomalies.extend(anomalies)
        self.meta.update(counts=dict(sheets=len(self.book.sheetnames),tables=len(self.tables),
                         observations=len(self.observations),anomalies=len(self.anomalies),formulas=self.formulas,
                         **Counter(r["state"] for r in self.observations)),checks=dict(self.checks))
        return dict(metadata=self.meta,observations=self.observations,anomalies=self.anomalies,
                    catalogue=CATALOGUE,tables=self.tables)


def import_workbook(path):
    path = Path(path)
    workbook_checks(path)
    book = load_workbook(path, data_only=False, keep_links=False)
    try:
        cached = load_workbook(path, data_only=True, keep_links=False)
        try:
            return Reader(path,book,cached).read()
        finally:
            cached.close()
    finally:
        book.close()
