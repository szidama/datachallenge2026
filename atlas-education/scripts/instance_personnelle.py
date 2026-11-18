"""Prépare les données et les comptes d’exercice d’une copie du dépôt."""
import json
import os
import tempfile
from contextlib import closing
from pathlib import Path

from server import domain
from server.storage import audit, connect, initialize, new_account


PROFILS = {
    "administrateur": "admin",
    "gestionnaire": "data",
    "analyste": "analyst",
    "atlas.validation": "validator",
    "atlas.autorisation": "decider",
    "atlas.diffusion": "publisher",
}
CLASSEUR = "DONNEES_STATISTQUES_ PRESCOLAIRE ET PRIMAIRE_2016_2025_DCB.xlsx"
MOTIF = "Exercice du circuit de diffusion dans cette instance personnelle."


def preparer_exemples(db, comptes, depot):
    source = depot / CLASSEUR
    complement = depot / "synthetic_demo.csv"
    brut = source.read_bytes()
    contenu = domain.ingest(source.name, brut, complement)
    domain.archive(db, complement.name, complement.read_bytes())
    jeu = domain.save_dataset(db, comptes["data"], source.name, brut, contenu,
                              "Statistiques scolaires 2016–2025 · Exercice")

    def avancer(role, table, dossier, action):
        domain.transition(db, comptes[role], table, dossier["id"], {"action": action, "reason": MOTIF})

    avancer("data", "datasets", jeu, "submit")
    avancer("validator", "datasets", jeu, "validate")
    for scenario, libelle in (("central", "central"), ("haut", "haut"), ("bas", "bas")):
        titre = f"Primaire public 2050 · Scénario {libelle} · Exercice"
        analyse = domain.create_analysis(db, comptes["analyst"], {
            "dataset_id": jeu["id"], "kind": "optimization", "title": titre,
            "parameters": {"cycle": "primaire", "year": 2050, "scenario": scenario, "regional_mix": "annuaire"},
        })
        avancer("validator", "analyses", analyse, "examine")
        avancer("validator", "analyses", analyse, "validate")
        edition = domain.prepare_publication(db, comptes["publisher"], {
            "dataset_id": jeu["id"], "analysis_id": analyse["id"], "title": titre,
            "methodology": "Édition d’exercice. Stocks du primaire public issus de l’annuaire 2024–2025. "
                           "Projection par régression quantile amortie jusqu’en 2049/2050. "
                           "Les résultats comparent la référence et les interventions dans les 13 régions historiques.",
        })
        avancer("validator", "publications", edition, "verify")
        avancer("decider", "publications", edition, "approve")
        avancer("publisher", "publications", edition, "publish")


def preparer_instance(depot):
    etat = depot / ".instance-atlas"
    if etat.exists():
        if not (etat / "atlas.sqlite").is_file():
            raise RuntimeError(f"Instance incomplète dans {etat}. Restaurez sa sauvegarde ou ouvrez une nouvelle copie du dépôt.")
        initialize(etat)
        return etat

    print("Préparation des six comptes et calcul des trois scénarios 2050…", flush=True)
    # La base et les remises deviennent disponibles ensemble, même après une interruption.
    with tempfile.TemporaryDirectory(prefix=".instance-installation-", dir=depot) as temporaire:
        nouveau = Path(temporaire) / "instance"
        initialize(nouveau)
        acces = nouveau / "acces"
        acces.mkdir(mode=0o700)
        with closing(connect(nouveau)) as db, db:
            comptes = {}
            for nom, role in PROFILS.items():
                compte = new_account(db, nom, role, ["*"])
                comptes[role] = compte
                audit(db, "operator", "account.init" if role == "admin" else "account.create",
                      compte["id"], ["*"], reason=MOTIF)
                remise = {k: compte[k] for k in ("id", "role", "username", "password", "totp_secret")}
                fd = os.open(acces / (nom + ".json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as fichier:
                    json.dump(remise, fichier, ensure_ascii=False, indent=2)
            preparer_exemples(db, comptes, depot)
        try:
            nouveau.rename(etat)
        except OSError:
            if not (etat / "atlas.sqlite").is_file():
                raise
    return etat
