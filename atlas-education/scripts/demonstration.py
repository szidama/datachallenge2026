"""Ouvre l’instance locale de démonstration et remet les accès à l’utilisateur du poste."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.storage import current_handoff

STATE = ROOT.parent / ".instance-locale"
ACCESS = STATE / "acces"
PORT = 8050
ADDRESS = f"http://127.0.0.1:{PORT}"


def cli(*args):
    return subprocess.run([sys.executable, "-m", "server", "--state", str(STATE), *map(str, args)], cwd=ROOT, check=True)


def bootstrap():
    os.umask(0o077)
    ACCESS.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not (STATE / "atlas.sqlite").exists():
        cli("init", "--output", ACCESS / "administrateur.json")
        for name, role in (("gestionnaire", "data"), ("analyste", "analyst")):
            cli("account", name, "--role", role, "--scope", "*", "--output", ACCESS / (name + ".json"))
        files = list(ROOT.parent.glob("DONNEES_STATISTQUES*.xlsx"))
        if len(files) == 1:
            extra = ROOT.parent / "synthetic_demo.csv"
            cli("import", files[0], "--as-user", "gestionnaire", *(["--demo", extra] if extra.exists() else []))


def running_mode():
    try:
        with urllib.request.urlopen(ADDRESS + "/admin", timeout=1) as response:
            if response.headers.get("Server", "").startswith("Atlas"):
                return "demo-locale" if b'data-connexion="demo-locale"' in response.read() else "standard"
    except OSError:
        return None


def start():
    mode = running_mode()
    if mode:
        return mode
    handle = open(STATE / "serveur.log", "a", encoding="utf8")
    with handle:
        process = subprocess.Popen([sys.executable, "-m", "server", "--state", str(STATE), "serve", "--port", str(PORT), "--demo-locale"],
                                   cwd=ROOT, stdin=subprocess.DEVNULL, stdout=handle, stderr=handle, start_new_session=True)
    for _ in range(50):
        mode = running_mode()
        if mode:
            return mode
        if process.poll() is not None:
            break
        time.sleep(.1)
    raise RuntimeError(f"Le service n’a pas démarré. Consulter {STATE / 'serveur.log'}.")


def main():
    if not STATE.exists():
        return subprocess.call([sys.executable, str(ROOT.parent / "demarrer.py")])
    bootstrap()
    mode = start()
    print(f"Atlas Éducation · Démonstration sur ce poste\nPortail public  {ADDRESS}/\nEspace privé   {ADDRESS}/admin")
    if not sys.stdin.isatty():
        return
    print("\nEntrée ouvre le portail. Choisissez un rôle pour consulter ses accès de démonstration sur ce terminal.")
    role = input("1 Analyste  ·  2 Gestionnaire  ·  3 Administrateur  ·  Entrée Portail  ").strip()
    name = {"1": "analyste", "2": "gestionnaire", "3": "administrateur"}.get(role)
    if name is None:
        webbrowser.open(ADDRESS)
        return
    credentials = ACCESS / (name + ".json")
    if not credentials.is_file():
        print("Accès remis séparément par votre administrateur.")
        webbrowser.open(ADDRESS + "/admin")
        return
    account = current_handoff(STATE, json.loads(credentials.read_text()))
    webbrowser.open(ADDRESS + "/admin")
    if account is None:
        print("Ce compte de démonstration est indisponible.")
        return
    print("Identifiant", account["username"])
    if account["password"]:
        print("Mot de passe", account["password"])
    else:
        print("Utilisez votre mot de passe actuel.")
    if mode == "demo-locale" or not account["totp_secret"]:
        input("Entrée pour fermer  ")
        return
    from server.storage import totp
    while True:
        print("Code de démonstration", totp(account["totp_secret"]), "· reste", 30-int(time.time())%30, "secondes")
        if input("Entrée pour rafraîchir le code, q pour fermer  ").strip().lower() == "q":
            return


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
