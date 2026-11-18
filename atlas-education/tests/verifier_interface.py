"""Recette navigateur ponctuelle, sur une instance privée temporaire (Node + Playwright)."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import domain
from server.http import make_server
from server.storage import connect, initialize, new_account


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--demo-locale", action="store_true")
    cli.add_argument("--captures", type=Path, help="Enregistrer les figures du rapport scientifique")
    args = cli.parse_args()
    if args.captures:
        args.captures.mkdir(parents=True, exist_ok=True)
    workbook = next(ROOT.parent.glob("DONNEES_STATISTQUES*.xlsx"))
    with tempfile.TemporaryDirectory(prefix="atlas-recette-") as tmp:
        state = Path(tmp)
        initialize(state)
        db = connect(state)
        with db:
            accounts = {role:new_account(db, "test-"+role, role, ["*"]) for role in
                        ("admin","data","analyst","validator","decider","publisher")}
            raw = workbook.read_bytes()
            dataset = domain.save_dataset(db, accounts["data"], workbook.name, raw,
                     domain.ingest(workbook.name, raw, ROOT.parent/"synthetic_demo.csv"), "Jeu temporaire de recette")
            def step(role, table, record, action):
                domain.transition(db, accounts[role], table, record["id"],
                                  {"action":action,"reason":"Validation technique sur une instance temporaire de recette"})
            step("data","datasets",dataset,"submit")
            step("validator","datasets",dataset,"validate")
            # Les titres ne révèlent pas le scénario. La troisième publication conserve
            # les paramètres historiques implicites (cycle primaire et demande centrale).
            for title, params in (("Étude A", {"scenario":"bas","cycle":"primaire","regional_mix":"annuaire"}),
                                  ("Étude B", {"scenario":"haut","cycle":"primaire","regional_mix":"annuaire"}),
                                  ("Étude C", {"model":"last"})):
                analysis = domain.create_analysis(db,accounts["analyst"],dict(dataset_id=dataset["id"],
                         kind="projection",title=title,parameters=params))
                step("validator","analyses",analysis,"examine")
                step("validator","analyses",analysis,"validate")
                pub=domain.prepare_publication(db,accounts["publisher"],dict(dataset_id=dataset["id"],
                        analysis_id=analysis["id"],title=title,methodology="Recette locale du circuit."))
                for role,action in (("validator","verify"),("decider","approve"),("publisher","publish")):
                    step(role,"publications",pub,action)
            revision=domain.revised_dataset(db,accounts["data"],dataset["id"],dict(
                observation_id="PRE06:F77",value=0.92,reason="Vérifier la note de contrôle du gestionnaire"))
            step("data","datasets",revision,"submit")
            step("validator","datasets",revision,"return")
        db.close()
        local_demo=args.demo_locale
        web=make_server(state,port=0,local_demo=local_demo)
        thread=threading.Thread(target=web.serve_forever,daemon=True)
        thread.start()
        try:
            body={"base":f"http://127.0.0.1:{web.server_port}","workbook":str(workbook),"localDemo":local_demo,
                  "captures": str(args.captures.resolve()) if args.captures else None,
                  "sourceId":dataset["id"],"returnedSourceId":revision["id"],
                  "accounts":{k:{i:v[i] for i in ("username","password","totp_secret")} for k,v in accounts.items()}}
            subprocess.run(["node",str(ROOT/"tests"/"navigateur.cjs")],input=json.dumps(body),text=True,check=True)
        finally:
            web.shutdown()
            web.server_close()


if __name__=="__main__":
    main()
