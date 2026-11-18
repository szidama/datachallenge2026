"""Reconstruit le référentiel provincial à partir des trois PDF officiels (Poppler requis)."""
import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHOOL = "https://www.education.gov.bf/fileadmin/user_upload/storages/annuaire_statistique_du_primaire_2024-2025_vf.pdf"
POP = "https://www.insd.bf/sites/default/files/2023-02/VOLUME%204%20PROJECTIONS%20DEMOGRAPHIQUES%202020%202035%20RGPH%20%C3%A9dition%202-%2006-02-2023.pdf"
LOCAL = "https://www.insd.bf/sites/default/files/2022-10/Fichier%20des%20localites%20RGPH%202019.pdf"
COUNTS = ("schools", "rooms", "groups", "teachers", "enrolment")


def key(label):
    letters = unicodedata.normalize("NFKD", label.lower())
    plain = re.sub("[^a-z]", "", letters)
    return {"boulkiende": "boulkiemde", "komandjoari": "komondjari", "lesbale": "bales", "kourittenga": "kouritenga", "komondjoari": "komondjari"}.get(plain, plain)


def pages(path):
    return subprocess.check_output(["pdftotext", "-layout", str(path), "-"]).decode().split("\f")


def whole(number):
    return int(number.replace(" ", ""))


def extract(primary, population, localities):
    geography = json.loads((ROOT / "web/assets/regions.json").read_text())
    rows = {key(name): {"province": name, "region": region}
            for region, units in geography.items() for name in units["provinces"]}
    school_pages = pages(primary)
    margins = {}
    for page in range(12, 17):
        for line in school_pages[page-1].splitlines():
            cells = re.split(r"\s{2,}", line.strip())
            if cells[:1] == ["Public"] and page == 16:
                margins.update(zip(COUNTS, map(whole, cells[1:6])))
            if len(cells) >= 7 and cells[1] == "Public" and key(cells[0]) in rows:
                record = rows[key(cells[0])]
                if "enrolment" in record:
                    raise ValueError(f"Province répétée, page {page}")
                record.update(zip(COUNTS, map(whole, cells[2:7])))
                record["inventory_page"] = page
    for page in range(279, 282):
        for line in school_pages[page-1].splitlines():
            cells = re.split(r"\s{2,}", line.strip())
            if len(cells) == 8 and page == 281 and cells[0] == "9 526":
                margins.update(water=whole(cells[1]), latrines=whole(cells[3]))
            if len(cells) == 9 and key(cells[0]) in rows:
                row = rows[key(cells[0])]
                if whole(cells[1]) != row["schools"] or "water" in row:
                    raise ValueError(f"Écoles incohérentes, page {page}")
                row.update(water=whole(cells[2]), latrines=whole(cells[4]), wash_page=page)
    demo_pages = pages(population)
    for cover, title in enumerate(demo_pages, 1):
        match = re.fullmatch(r"PROVINCE (?:DE LA |DE L'|DES |DE |DU )(.+)", title.strip())
        if not match or key(match[1]) not in rows:
            continue
        row = rows[key(match[1])]
        population_by_year = {}
        adjustments = []
        for page in range(cover+2, cover+5):
            years = []
            for line in demo_pages[page-1].splitlines():
                if re.fullmatch(r"[^0-9|]*20[23]\d(?:\s+20[23]\d)*\s*", line):
                    years = list(map(int, re.findall(r"20[23]\d", line)))
                ages = re.match(r"^\s*6\s*[-–]\s*11\s*ans\s+(.*)", line, re.I)
                if not ages:
                    continue
                numbers = [whole(n) for n in re.findall(r"\b\d{1,3} \d{3}\b|\b\d{4,7}\b", ages[1])]
                if len(numbers) != len(years)*3 or not years:
                    raise ValueError(f"Ligne 6–11 ans illisible, page {page}: {ages[1]}")
                for i, year in enumerate(years):
                    males, females, total = numbers[3*i:3*i+3]
                    if year in population_by_year or min(males, females, total) <= 0:
                        raise ValueError(f"Total démographique incohérent, page {page}, {year}")
                    if abs(males+females-total) > 1:
                        adjustments.append(dict(year=year, page=page, printed=total, male=males, female=females))
                        total = males + females
                    population_by_year[year] = total
        if sorted(population_by_year) != list(range(2020, 2036)):
            raise ValueError(f"Série démographique incomplète pour {row['province']}")
        row.update(population=population_by_year, population_pages=[cover+2, cover+4], adjustments=adjustments)
    for page, body in enumerate(pages(localities), 1):
        for line in body.splitlines():
            title = re.fullmatch(r"\s*PROVINCE\s*:\s*([\w’'-]+)\s*", line)
            if title and key(title[1]) in rows:
                rows[key(title[1])]["localities_page"] = page
    for row in rows.values():
        if not all(k in row for k in (*COUNTS, "water", "latrines", "population", "localities_page")):
            raise ValueError(f"Données incomplètes pour {row['province']}")
    if set(margins) != set((*COUNTS, "water", "latrines")) or any(sum(row[k] for row in rows.values()) != v for k, v in margins.items()):
        raise ValueError("Totaux provinciaux différents du total national imprimé")
    sources = {name: {"url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
               for name, url, path in (("annuaire", SCHOOL, primary), ("demographie", POP, population), ("localites", LOCAL, localities))}
    return {"edition": "DGESS 2024–2025 · RGPH 2019, volume 4, édition 2", "sources": sources,
            "totals": margins, "rows": list(rows.values())}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("primaire", type=Path)
    cli.add_argument("demographie", type=Path)
    cli.add_argument("localites", type=Path)
    cli.add_argument("--sortie", type=Path, default=ROOT / "planning/data/provinces_2025.json")
    args = cli.parse_args()
    args.sortie.write_text(json.dumps(extract(args.primaire, args.demographie, args.localites), ensure_ascii=False, indent=2)+"\n")
