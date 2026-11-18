"""Examiner le fichier transmis ou écrire un nouveau jeu de démonstration."""
import argparse
import json
from pathlib import Path

from . import import_demo, import_workbook
from .generateur import generate_demo


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    actions=cli.add_subparsers(dest="action",required=True)
    inspect=actions.add_parser("controler",help="Contrôler les feuilles et les compléments")
    inspect.add_argument("classeur",type=Path)
    inspect.add_argument("--complements",type=Path)
    generate=actions.add_parser("generer",help="Générer un nouveau CSV de démonstration")
    generate.add_argument("classeur",type=Path)
    generate.add_argument("destination",type=Path)
    generate.add_argument("--poids-ecoles",type=float,default=0.5)
    generate.add_argument("--graine",default="ATLAS-DEMO-V2")
    args=cli.parse_args()
    try:
        payload=import_workbook(args.classeur)
        if args.action=="generer":
            generate_demo(payload,args.destination,args.poids_ecoles,args.graine)
            print(json.dumps(import_demo(args.destination,payload)["metadata"],ensure_ascii=False,indent=2))
        else:
            print(json.dumps(dict(metadata=payload["metadata"],tables=payload["tables"],anomalies=payload["anomalies"]),
                             ensure_ascii=False,indent=2))
            if args.complements:
                print(json.dumps(import_demo(args.complements,payload)["metadata"],ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:
        cli.exit(2,f"Import interrompu. {exc}\n")


if __name__=="__main__":
    main()
