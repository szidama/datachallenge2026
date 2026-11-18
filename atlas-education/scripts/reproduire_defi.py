"""Rejoue le défi 2050 à partir du classeur et du référentiel DGESS–INSD figé."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ingestion import import_workbook
from planning import run_plan, VERSION
from planning.forecast import SCENARIOS, spread_integers

YEARS = (2030,2035,2040,2045,2050)


def write_csv(path, records, labels):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.writer(f, delimiter=";")
        w.writerow(labels.values())
        w.writerows([r.get(key) for key in labels] for r in records)


def ecrire_classeur(destination, tableaux, calcul):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    livre = Workbook()
    livre.remove(livre.active)
    for nom, _fichier, lignes, colonnes in tableaux:
        feuille = livre.create_sheet(nom)
        feuille.append(list(colonnes.values()))
        for ligne in lignes:
            feuille.append([ligne.get(cle) for cle in colonnes])
    methode = livre.create_sheet("Hypothèses")
    methode.append(["Paramètre ou source", "Valeur"])
    methode.append(["Classement territorial", "13 régions historiques et 45 provinces"])
    methode.append(["Besoin régional", "Écart à la capacité disponible après évolution annuelle des stocks"])
    methode.append(["Besoin provincial", "Écart à l’inventaire constant de 2025"])
    methode.append(["Démographie après 2035", "Conservation des derniers poids territoriaux de l’INSD"])
    for cle, valeur in calcul["hypotheses"].items():
        methode.append([cle, valeur])
    methode.append(["Amortissement appris", calcul["learning"]["phi"]])
    for nom, source in calcul["sources"].items():
        methode.append([nom, source["url"]])
    methode.append(["Classeur source", calcul["workbook"]["source"]])
    methode.append(["SHA-256 du classeur", calcul["workbook"]["sha256"]])
    for feuille in livre:
        feuille.freeze_panes = "A2"
        feuille.auto_filter.ref = feuille.dimensions
        for colonne, cellule in enumerate(feuille[1], 1):
            cellule.font = Font(bold=True, color="FFFFFF")
            cellule.fill = PatternFill("solid", fgColor="14583F")
            feuille.column_dimensions[get_column_letter(colonne)].width = max(17, len(cellule.value) + 3)
    methode.column_dimensions["A"].width = 36
    methode.column_dimensions["B"].width = 96
    livre.save(destination)


def replay(workbook, dest, excel=False):
    data=import_workbook(workbook)
    labels=json.loads((ROOT/"web/assets/regions.json").read_text(encoding="utf-8"))
    regions=[]; provinces=[]; national=[]
    sensitivity=[]; frozen_2025={}
    for year in YEARS:
        for sc in SCENARIOS:
            r=run_plan(data,dict(year=year,scenario=sc,regional_mix="annuaire"))
            if year==2050 and sc=="central":
                sensitivity=r["sensitivity"]
                target=next(t["central"] for t in r["trajectories"] if t["year"]==2050)
                frozen_2025=spread_integers(target,{v["province"]:v["enrolment"] for v in r["provincial"]["rows"]})
            for item in r["comparison"]:
                if item["option"] in ("reference","combine"):
                    national.append(dict(year=year,scenario=sc,**{k:item[k] for k in
                        ("option","demand","rooms_needed","teachers_needed","served","unserved","coverage",
                         "new_rooms","new_teachers","transfers","rehabilitated")}))
            for item in r["regional"]:
                if item["option"] in ("reference","combine"):
                    regions.append(dict(year=year,scenario=sc,name=labels[item["region"]]["name"],
                                        **{k:item[k] for k in ("region","option","demand","rooms","teachers","rooms_needed","teachers_needed","unserved")}))
            for row in r["provincial"]["rows"]:
                provinces.append(dict(year=year,scenario=sc,name=labels[row["region"]]["name"],weight_year=r["provincial"]["weight_year"],
                     **{k:row[k] for k in ("region","province","schools","enrolment","rooms","teachers","population_base","population_target","without_water","without_latrines","rooms_gap","teachers_gap")},
                     demand=row["demand"][sc]))
    dest.mkdir(parents=True,exist_ok=True)
    common={"year":"Horizon","scenario":"Scénario","option":"Intervention","demand":"Demande projetée",
            "rooms_needed":"Salles manquantes","teachers_needed":"Enseignants manquants","unserved":"Places à couvrir"}
    tableaux = [
        ("Bilan national", "national.csv", national, {**common,"served":"Places servies","coverage":"Taux de couverture (fraction)",
              "new_rooms":"Salles neuves cumulées","new_teachers":"Recrues cumulées","transfers":"Transferts cumulés","rehabilitated":"Salles remises en service cumulées"}),
        ("Régions", "regions.csv", regions, {"name":"Région",**common,"rooms":"Salles utilisables","teachers":"Enseignants disponibles"}),
        ("Provinces", "provinces.csv", provinces, {"province":"Province","name":"Région","year":"Horizon","scenario":"Scénario",
              "demand":"Demande projetée","rooms_gap":"Salles manquantes à inventaire 2025 constant",
              "teachers_gap":"Enseignants manquants à inventaire 2025 constant","schools":"Écoles 2025","enrolment":"Élèves 2025",
              "rooms":"Salles 2025","teachers":"Enseignants chargés de cours 2025","population_base":"6–11 ans 2025",
              "population_target":"6–11 ans à l’horizon (vide après 2035)","weight_year":"Millésime des poids",
              "without_water":"Écoles sans eau 2025","without_latrines":"Écoles sans latrines fonctionnelles 2025"}),
    ]
    for _nom, fichier, lignes, colonnes in tableaux:
        write_csv(dest / fichier, lignes, colonnes)
    summary=dict(version=VERSION,workbook=data["metadata"],tables=len(data["tables"]),observations=len(data["observations"]),
                 sources=r["provincial"]["sources"],historical=r["historical"],trajectories=r["trajectories"],validation=r["validation"],
                 learning=r["meta"]["learning"],hypotheses={k:v for k,v in r["parameters"].items() if k not in ("scenario","year")},
                 national=national,regions=regions,provinces=provinces,sensitivity_2050_central=sensitivity,
                 central_2050_parts_de_2025=frozen_2025)
    (dest/"resultats.json").write_text(json.dumps(summary,ensure_ascii=False,allow_nan=False,indent=1)+"\n",encoding="utf-8")
    if excel:
        ecrire_classeur(dest / "Atlas-resultats-calcules.xlsx", tableaux, summary)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("classeur",type=Path)
    cli.add_argument("sortie",type=Path,help="Répertoire des tableaux reproductibles")
    cli.add_argument("--excel",action="store_true",help="Exporter aussi les tableaux et les hypothèses dans Excel")
    args=cli.parse_args()
    replay(args.classeur,args.sortie,args.excel)
