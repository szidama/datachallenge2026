import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from . import domain
from .http import make_server
from .storage import Error, audit, check, connect, credentials, initialize, new_account, require, user

def emit_account(result,output=None):
    text=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if output:
        path=Path(output)
        with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"w") as f:f.write(text)
        print("Accès remis dans",path)
    else:print(text,end="")

def backup(db,path):
    path=Path(path)
    check(not path.exists(),409,"Le fichier de sauvegarde existe déjà.")
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"wb"):pass
    out=sqlite3.connect(path)
    try:
        db.backup(out)
        check(out.execute("PRAGMA integrity_check").fetchone()[0]=="ok",500,"Sauvegarde incohérente.")
    finally:out.close()

def restore(path,state):
    path=Path(path)
    check(path.is_file() and not (state/"atlas.sqlite").exists(),409,"Restaurez dans un nouveau répertoire privé vide.")
    src=sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True)
    try:
        check(src.execute("PRAGMA integrity_check").fetchone()[0]=="ok" and src.execute("PRAGMA user_version").fetchone()[0]==1,422,"Sauvegarde invalide.")
        check(not src.execute("PRAGMA foreign_key_check").fetchone(),422,"Clés de données invalides.")
        state.mkdir(mode=0o700,parents=True,exist_ok=True)
        backup(src,state/"atlas.sqlite")
    finally:src.close()
    db=connect(state)
    with db:
        db.execute("DELETE FROM sessions")
        audit(db,"operator","restore")
    db.close()

def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser("atlas",description="Service Atlas Éducation 2050")
    parser.add_argument("--state",type=Path,default=Path(os.getenv("ATLAS_STATE",str(Path.home()/".atlas-education"))))
    commands=parser.add_subparsers(dest="command",required=True)
    init=commands.add_parser("init");init.add_argument("--username",default="administrateur");init.add_argument("--output")
    account=commands.add_parser("account");account.add_argument("username");account.add_argument("--role",required=True);account.add_argument("--scope",required=True);account.add_argument("--output")
    recover=commands.add_parser("recover");recover.add_argument("username");recover.add_argument("--output")
    ingest=commands.add_parser("import");ingest.add_argument("workbook",type=Path);ingest.add_argument("--as-user",required=True);ingest.add_argument("--demo",type=Path);ingest.add_argument("--title",default="Statistiques scolaires 2016–2025")
    serve=commands.add_parser("serve");serve.add_argument("--host",default="127.0.0.1");serve.add_argument("--port",type=int,default=8050);serve.add_argument("--origin",default=os.getenv("ATLAS_ORIGIN"))
    serve.add_argument("--demo-locale",action="store_true",help="Connexion par mot de passe sur le poste de démonstration")
    commands.add_parser("backup").add_argument("file",type=Path)
    commands.add_parser("restore").add_argument("file",type=Path)
    args=parser.parse_args()
    check(not args.state.resolve().is_relative_to((domain.ROOT/"web").resolve()),422,"Stockage privé hors de web/ requis.")
    if args.command=="restore":
        restore(args.file,args.state);print("Restauration vérifiée. Sessions révoquées.");return
    if args.command!="init":check((args.state/"atlas.sqlite").is_file(),409,"Initialisez d’abord l’instance avec init.")
    initialize(args.state);db=connect(args.state)
    if args.command=="serve":
        from urllib.parse import urlsplit
        if args.origin:
            parsed=urlsplit(args.origin)
            check(parsed.scheme in {"http","https"} and parsed.netloc and not parsed.path,422,"Origine publique invalide.")
        check(args.host in {"127.0.0.1","localhost","::1"} or (args.origin and args.origin.startswith("https://")),422,"Indiquez l’origine HTTPS du proxy pour une exposition réseau.")
        with db:
            db.execute("UPDATE jobs SET state='failed',error='Calcul interrompu au redémarrage. Relancez.' WHERE state IN ('running','queued')")
        db.close()
        http=make_server(args.state,args.host,args.port,origin=args.origin,local_demo=args.demo_locale)
        print(f"Atlas Éducation · http://{args.host}:{http.server_port}",flush=True)
        try:http.serve_forever()
        except KeyboardInterrupt:pass
        finally:http.server_close()
        return
    try:
        with db:
            if args.command in ("init","account","recover"):
                if args.output:check(not Path(args.output).exists(),409,"Le fichier de remise existe déjà.")
                if args.command=="init":
                    check(not db.execute("SELECT 1 FROM users").fetchone(),409,"Instance déjà initialisée.")
                    result=new_account(db,args.username,"admin",["*"])
                elif args.command=="account":result=new_account(db,args.username,args.role,args.scope.split(","))
                else:
                    r=db.execute("SELECT id FROM users WHERE username=?",(args.username,)).fetchone()
                    check(r,404,"Compte inconnu.")
                    result={**user(db,r["id"]),**credentials(db,r["id"])}
                audit(db,"operator","account."+args.command,result["id"],result["scope"]);emit_account(result,args.output)
            if args.command=="import":
                row=db.execute("SELECT id FROM users WHERE username=?",(args.as_user,)).fetchone()
                check(row,404,"Gestionnaire inconnu.");actor=user(db,row["id"]);require(actor,"data.import")
                raw=args.workbook.read_bytes();check(len(raw)<=10*1024**2,413,"Classeur trop volumineux.")
                payload=domain.ingest(args.workbook.name,raw,args.demo)
                if args.demo:domain.archive(db,args.demo.name,args.demo.read_bytes())
                result=domain.save_dataset(db,actor,args.workbook.name,raw,payload,args.title)
                print(json.dumps({k:result[k] for k in ("id","state","title")},ensure_ascii=False))
            if args.command=="backup":
                backup(db,args.file);audit(db,"operator","backup");print("Sauvegarde vérifiée.")
    finally:db.close()

if __name__=="__main__":
    try:main()
    except (Error,OSError,ValueError,sqlite3.Error) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
