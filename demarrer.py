"""Ouvre Atlas Éducation depuis une copie du dépôt sur Windows, macOS, Linux ou Codespaces."""
import argparse
import errno
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import venv
import webbrowser
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path

DEPOT = Path(__file__).resolve().parent
APP = DEPOT / "atlas-education"
sys.path.insert(0, str(APP))

from scripts.instance_personnelle import PROFILS, preparer_instance
from server.http import make_server
from server.storage import Error, current_handoff, totp


def charger_bibliotheques():
    environnement = DEPOT / ".venv"
    if Path(sys.prefix).resolve() != environnement.resolve():
        executable = environnement / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not executable.is_file():
            print("Installation de l’environnement Python du dépôt…", flush=True)
            venv.EnvBuilder(with_pip=True).create(environnement)
        commande = [str(executable), "-X", "utf8", str(DEPOT / "demarrer.py"), *sys.argv[1:]]
        if os.name == "nt":
            raise SystemExit(subprocess.call(commande))
        os.execv(executable, commande)

    exigences = APP / "requirements.txt"
    versions = [ligne.split()[0].split("==") for ligne in exigences.read_text(encoding="utf-8").splitlines()
                if ligne and not ligne.startswith("#")]
    try:
        if all(metadata.version(nom) == version for nom, version in versions):
            return
    except metadata.PackageNotFoundError:
        pass
    if find_spec("pip") is None:
        subprocess.run([sys.executable, "-m", "ensurepip"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "--isolated", "--disable-pip-version-check", "install",
                    "--no-index", "--no-cache-dir", "--require-hashes", "--find-links", str(APP / "vendor"),
                    "-r", str(exigences)], check=True)


def origine_codespaces(port):
    if os.environ.get("CODESPACES") != "true":
        return None
    nom = os.environ.get("CODESPACE_NAME", "")
    domaine = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "")
    label = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    if not re.fullmatch(label, nom) or not re.fullmatch(rf"{label}(?:\.{label})+", domaine):
        raise RuntimeError("L’adresse privée de GitHub Codespaces est indisponible. Rouvrez le Codespace.")
    return f"https://{nom}-{port}.{domaine}"


def afficher_acces(etat, profil, origine):
    fichier = etat / "acces" / (profil + ".json")
    if not fichier.is_file():
        raise RuntimeError(f"Remise introuvable pour {profil}. Démarrez d’abord Atlas ou utilisez les accès remis par votre administrateur.")
    compte = current_handoff(etat, json.loads(fichier.read_text(encoding="utf-8")))
    if compte is None:
        raise RuntimeError("Ce compte est désactivé ou a été supprimé. Consultez Habilitations et audit.")
    print("Identifiant     ", compte["username"])
    print("Mot de passe    ", compte["password"] or "Utilisez votre mot de passe actuel.")
    if origine:
        maintenant = int(time.time())
        if compte["totp_secret"]:
            print("Code temporaire ", totp(compte["totp_secret"], maintenant // 30),
                  f"(valable encore {30 - maintenant % 30} s)")
        else:
            print("Utilisez le code de votre application d’authentification.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("ouvrir", "acces", "preparer"), default="ouvrir", nargs="?")
    parser.add_argument("profil", choices=list(PROFILS), nargs="?", help="Compte dont afficher les accès")
    parser.add_argument("--port", type=int, default=8051, help="Port HTTP de cette instance (8051 par défaut)")
    parser.add_argument("--sans-navigateur", action="store_true", help="Laisser le navigateur fermé")
    args = parser.parse_args()
    if args.profil and args.action != "acces":
        parser.error("Le choix du profil s’utilise avec la commande acces.")
    if not 1 <= args.port <= 65535:
        parser.error("Le port doit être compris entre 1 et 65 535.")
    if sys.version_info < (3, 10):
        parser.exit(1, "Atlas nécessite Python 3.10 ou plus récent.\n")
    os.umask(0o077)
    origine = origine_codespaces(args.port)
    adresse = origine or f"http://127.0.0.1:{args.port}"
    if args.action == "acces":
        print("Espace de travail", adresse + "/admin")
        afficher_acces(DEPOT / ".instance-atlas", args.profil or "administrateur", origine)
        return

    charger_bibliotheques()
    etat = preparer_instance(DEPOT)
    if args.action == "preparer":
        print("L’instance personnelle est prête.")
        return
    try:
        serveur = make_server(etat, port=args.port, origin=origine, local_demo=origine is None, personal_instance=True)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE or getattr(exc, "winerror", None) == 10048:
            raise RuntimeError(f"Le port {args.port} est occupé. Si Atlas est déjà ouvert, utilisez {adresse}/admin. "
                               "Pour une autre instance, choisissez un port libre avec --port.") from exc
        raise
    with serveur:
        print("Portail public   ", adresse + "/")
        print("Espace de travail", adresse + "/admin")
        commande = "py -3" if os.name == "nt" else "python3"
        print(f"Accès des profils dans un second terminal : {commande} demarrer.py acces [profil]", flush=True)
        if sys.stdout.isatty() and not origine:
            try:
                afficher_acces(etat, "administrateur", origine)
            except (OSError, ValueError, KeyError, RuntimeError) as exc:
                print(exc, file=sys.stderr)
            if not args.sans_navigateur:
                webbrowser.open(adresse + "/admin")
        try:
            serveur.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (Error, OSError, RuntimeError, sqlite3.Error, subprocess.CalledProcessError, ValueError) as exc:
        sys.exit(str(exc))
