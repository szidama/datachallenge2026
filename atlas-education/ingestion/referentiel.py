"""Périmètres stables, unités et tables du classeur du Data Challenge Burkina."""
from dataclasses import dataclass

REGIONS = dict(zip(
    ("boucle-du-mouhoun", "cascades", "centre", "centre-est", "centre-nord", "centre-ouest",
     "centre-sud", "est", "hauts-bassins", "nord", "plateau-central", "sahel", "sud-ouest"),
    ("Boucle du Mouhoun", "Cascades", "Centre", "Centre-Est", "Centre-Nord", "Centre-Ouest",
     "Centre-Sud", "Est", "Hauts-Bassins", "Nord", "Plateau Central", "Sahel", "Sud-Ouest"),
))
DIMS = ("region", "sex", "status", "area", "level")
LEVELS = {
    "primaire": ("cp1", "cp2", "ce1", "ce2", "cm1", "cm2"),
    "prescolaire": ("petite-section", "moyenne-section", "grande-section"),
}

# Les cellules de total sont des observations publiées à part entière.
@dataclass(frozen=True)
class Table:
    id: str
    sheet: str
    anchor: int
    first_row: int
    last_row: int
    dims: tuple
    indicator: str
    grouped_sex: bool = False
    first_year: int = 2016

    @property
    def cycle(self):
        return "prescolaire" if self.sheet == "PRESCOLAIRE" else "primaire"

    @property
    def first_col(self):
        return len(self.dims) + 1


def pre(i, anchor, start, end, axes, metric, grouped=False, year=2016):
    return Table(f"PRE{i:02}", "PRESCOLAIRE", anchor, start, end, tuple(axes.split()), metric, grouped, year)


def pri(i, start, end, axes, metric, grouped=False):
    return Table(f"PRI{i:02}", f"Feuil{i}", 1, start, end, tuple(axes.split()), metric, grouped)


TABLES = (
    pre(1, 1, 4, 17, "region", "effectifs", True),
    pre(2, 19, 22, 25, "status", "effectifs", True),
    pre(3, 27, 30, 33, "area", "effectifs", True, 2018),
    pre(4, 36, 39, 51, "status level", "effectifs", True),
    pre(5, 54, 57, 70, "region", "tbs", True),
    pre(6, 73, 75, 88, "region", "ips_tbs"),
    pre(7, 91, 93, 145, "region status", "structures"),
    pre(8, 148, 150, 202, "region status", "salles_recensees"),
    pri(1, 3, 44, "region sex", "effectifs"),
    pri(2, 3, 11, "status sex", "effectifs"),
    pri(3, 3, 11, "area sex", "effectifs"),
    pri(4, 3, 47, "status level sex", "effectifs"),
    pri(5, 3, 44, "region sex", "nouveaux_cp1"),
    pri(6, 4, 17, "region", "tba", True),
    pri(7, 4, 17, "region", "tbs", True),
    pri(8, 4, 17, "region", "tap", True),
    pri(9, 3, 44, "region sex", "reussite_cep"),
    pri(10, 3, 16, "region", "ips_tba"),
    pri(11, 3, 16, "region", "ips_tbs"),
    pri(12, 3, 16, "region", "ips_tap"),
    pri(13, 3, 44, "region status", "ecoles"),
)


def fiche(label, unit, numerator, denominator, formula, purpose, limits):
    return dict(label=label, unit=unit, numerator=numerator, denominator=denominator,
                formula=formula, objective=purpose, limits=limits,
                validation="Contrôles techniques à l'import. Validation métier par version.")


CATALOGUE = {
    "effectifs": fiche("Élèves inscrits", "eleves", "Élèves inscrits dans le champ du tableau", None,
                       "Dénombrement publié", "Suivre les inscriptions par dimension disponible.",
                       "Le croisement public par région manque. L’inscription ne mesure pas la population scolarisable."),
    "nouveaux_cp1": fiche("Nouveaux inscrits au CP1", "eleves", "Nouveaux inscrits au CP1", None,
                         "Dénombrement publié", "Suivre les entrées au primaire.", "Tous statuts dans le tableau régional."),
    "tba": fiche("Taux brut d’admission", "pourcent", "Nouveaux inscrits en première année, tous âges",
                 "Population ayant l’âge officiel d’entrée", "100 × numérateur / dénominateur",
                 "Examiner les admissions.", "Le taux peut dépasser 100 %. Les dénominateurs régionaux manquent."),
    "tbs": fiche("Taux brut de scolarisation", "pourcent", "Élèves inscrits dans le cycle, tous âges",
                 "Population ayant l’âge officiel du cycle", "100 × numérateur / dénominateur",
                 "Suivre la participation au cycle.", "Le taux peut dépasser 100 %. Il ne donne pas le taux de non-scolarisation."),
    "tap": fiche("Taux d’achèvement du primaire", "pourcent", "Nouveaux entrants en dernière année",
                 "Population d’âge officiel de dernière année", "Taux publié dans le classeur",
                 "Suivre l’achèvement du primaire.", "Vérifier les conventions de l’annuaire avant de recalculer le taux."),
    "reussite_cep": fiche("Réussite au CEP", "pourcent", "Candidats admis au CEP", "Candidats présents au CEP",
                         "100 × numérateur / dénominateur", "Examiner les résultats de l’examen.",
                         "Les effectifs de candidats et d’admis manquent. Cet examen couvre une partie des apprentissages."),
    "ecoles": fiche("Écoles primaires", "ecoles", "Écoles recensées", None, "Dénombrement par région et statut",
                    "Situer l’offre institutionnelle.", "Le stock de salles utilisables requiert un inventaire complémentaire."),
    "structures": fiche("Structures préscolaires", "structures", "Structures recensées", None,
                        "Dénombrement par région et statut", "Localiser l’offre par région.", "Le communautaire a son propre statut."),
    "salles_recensees": fiche("Salles préscolaires recensées", "salles", "Salles recensées", None,
                             "Dénombrement par région et statut", "Décrire le parc préscolaire.", "L’état fonctionnel manque."),
}
for ratio in ("tba", "tbs", "tap"):
    CATALOGUE[f"ips_{ratio}"] = fiche(
        f"Indice de parité du {ratio.upper()}", "rapport", f"{ratio.upper()} féminin", f"{ratio.upper()} masculin",
        "Taux féminin / taux masculin, si le taux masculin est positif",
        "Mesurer l’écart entre filles et garçons.", "Rapport sans unité. Une valeur de 1 correspond à la parité.")
DEMO_INDICATORS = {
    "inscrits_publics_synthetiques": ("effectifs_publics_simules", "eleves", "Inscriptions publiques régionales simulées"),
    "salles_primaires_synthetiques": ("salles_primaires_simulees", "salles", "Salles publiques primaires simulées"),
    "enseignants_synthetiques": ("enseignants_simules", "personnes", "Enseignants publics primaires simulés"),
}
for key, unit, label in DEMO_INDICATORS.values():
    CATALOGUE[key] = fiche(label, unit, label, None, "Méthode illustrative inscrite dans chaque ligne du CSV",
                           "Tester les scénarios et dimensionner la collecte complémentaire.",
                           "Simulation sans validation institutionnelle. La disponibilité opérationnelle exige un contrôle de terrain.")

for key, card in CATALOGUE.items():
    tables = [t for t in TABLES if t.indicator == key]
    card["sources"] = [f"{t.sheet}!A{t.anchor}" for t in tables] or ["CSV de démonstration"]
    card["tables"] = [t.id for t in tables] or ["DEMO"]
    card["granularity"] = {t.id: list(t.dims) + (["sex"] if t.grouped_sex else []) for t in tables} or {"DEMO": ["region","sex","status"]}
    card["period"] = "Année de fin de l’année scolaire. Périodes importées dans le manifeste de chaque table."
    card["method"] = "Valeurs et unités du classeur, avec conservation de l’original" if tables else "Démonstration synthétique"
    card["version"] = "Empreinte du fichier inscrite dans chaque observation"
