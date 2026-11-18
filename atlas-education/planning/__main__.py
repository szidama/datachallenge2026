"""Rejouer hors ligne un scénario privé à partir des sources autorisées localement."""
import argparse
import json
from pathlib import Path

from ingestion import import_demo, import_workbook

from . import run_plan


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("classeur",type=Path)
    cli.add_argument("--demo",type=Path,help="Compléments explicitement simulés (CSV)")
    cli.add_argument("--parametres",type=Path,help="Objet JSON des paramètres du modèle")
    cli.add_argument("--region",action="append",help="Une région par argument ; par défaut agrégation nationale")
    cli.add_argument("--projection",action="store_true",help="Calculer uniquement la demande")
    cli.add_argument("--sortie",type=Path,required=True,help="Nouveau fichier JSON résultat")
    args=cli.parse_args()
    try:
        data=import_workbook(args.classeur)
        demo=import_demo(args.demo,data) if args.demo else []
        p=json.loads(args.parametres.read_text(encoding="utf-8")) if args.parametres else {}
        result=run_plan(data,p,demo,args.region,mode="projection" if args.projection else "combined")
        with args.sortie.open("x",encoding="utf-8") as file:
            json.dump(result,file,ensure_ascii=False,allow_nan=False,separators=(",",":"))
        print(f"{len(result['trajectories'])} trajectoires annuelles écrites dans {args.sortie}.")
    except (ValueError,OSError) as exc:
        cli.exit(1,f"Calcul impossible : {exc}\n")


if __name__=="__main__":
    main()
