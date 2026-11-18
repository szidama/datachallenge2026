"""Parcours d'un destinataire du dépôt sur une instance indépendante."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

DEPOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DEPOT))
from demarrer import origine_codespaces
from scripts.instance_personnelle import CLASSEUR, PROFILS, preparer_instance
from server import domain
from server.http import public_api
from server.permissions import MODULES, PERMISSIONS
from server.storage import authenticate, connect, user


class InstancePersonnelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dossier = tempfile.TemporaryDirectory()
        cls.addClassCleanup(dossier.cleanup)
        cls.depot = Path(dossier.name)
        for nom in (CLASSEUR, "synthetic_demo.csv"):
            shutil.copyfile(DEPOT / nom, cls.depot / nom)
        with redirect_stdout(StringIO()):
            cls.etat = preparer_instance(cls.depot)

    def test_six_profils_utilisables_et_administrateur_national(self):
        with closing(connect(self.etat)) as db, db:
            for nom, role in PROFILS.items():
                with self.subTest(nom=nom):
                    remise = json.loads((self.etat / "acces" / (nom + ".json")).read_text(encoding="utf-8"))
                    _, session = authenticate(db, remise, "localhost", require_totp=False)
                    compte = session["user"]
                    self.assertEqual((compte["role"], compte["scope"]), (role, ["*"]))
                    if role == "admin":
                        self.assertEqual(set(compte["permissions"]), PERMISSIONS)
                        self.assertEqual(set(compte["modules"]), set(MODULES))

    def test_trois_editions_conformes_aux_chiffres_livres_et_aux_signatures(self):
        rapport = json.loads((DEPOT / "outputs/Defi-2050/resultats.json").read_text(encoding="utf-8"))
        scenarios = set()
        with closing(connect(self.etat)) as db:
            editions = public_api(db, ["publications"], {})["items"]
            self.assertEqual(len(editions), 3)
            for edition in editions:
                identifiant = edition["id"]
                contenu = public_api(db, ["publications", identifiant], {})["payload"]
                scenario = contenu["parameters"]["scenario"]
                scenarios.add(scenario)
                lignes = {(r["region"], r["option"]): (r["demand"], r["rooms_needed"], r["teachers_needed"])
                          for r in contenu["result"]["regional"] if r["option"] in ("reference", "combine")}
                attendu = {(r["region"], r["option"]): (r["demand"], r["rooms_needed"], r["teachers_needed"])
                           for r in rapport["regions"] if r["year"] == 2050 and r["scenario"] == scenario}
                self.assertEqual(len(lignes), 26)
                self.assertEqual(lignes, attendu)
                signatures = [(r["action"], r["role"]) for r in db.execute(
                    """SELECT a.action,u.role FROM audit a JOIN users u ON u.id=a.actor WHERE a.resource=?
                       AND a.action IN ('publications.verify','publications.approve','publications.publish')
                       ORDER BY a.seq""", (identifiant,))]
                self.assertEqual(signatures, [("publications.verify", "validator"),
                                              ("publications.approve", "decider"), ("publications.publish", "publisher")])
        self.assertEqual(scenarios, {"bas", "central", "haut"})

    def test_relance_conserve_les_acces_et_une_edition_retiree(self):
        # La copie de cet exercice permet de retirer une édition sans influencer les autres tests.
        with tempfile.TemporaryDirectory() as racine:
            copie = Path(racine) / ".instance-atlas"
            shutil.copytree(self.etat, copie)
            with closing(connect(copie)) as db, db:
                edition = public_api(db, ["publications"], {})["items"][0]
                responsable = db.execute("SELECT id FROM users WHERE role='publisher'").fetchone()["id"]
                domain.transition(db, user(db, responsable), "publications", edition["id"],
                                  {"action": "withdraw", "reason": "Fin de l’exercice de publication."})
            self.assertEqual(preparer_instance(Path(racine)), copie)
            with closing(connect(copie)) as db:
                self.assertEqual(public_api(db, ["publications"], {})["total"], 2)
                self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 6)
            self.assertTrue((copie / "acces/administrateur.json").read_bytes() ==
                            (self.etat / "acces/administrateur.json").read_bytes())

    def test_installation_interrompue_peut_etre_reprise(self):
        with tempfile.TemporaryDirectory() as racine, redirect_stdout(StringIO()):
            dossier = Path(racine)
            with self.assertRaises(FileNotFoundError):
                preparer_instance(dossier)
            self.assertEqual(list(dossier.iterdir()), [])
            for nom in (CLASSEUR, "synthetic_demo.csv"):
                shutil.copyfile(DEPOT / nom, dossier / nom)
            etat = preparer_instance(dossier)
            self.assertTrue((etat / "atlas.sqlite").is_file())
            def mot_de_passe(instance):
                return json.loads((instance / "acces/administrateur.json").read_text(encoding="utf-8"))["password"]
            self.assertFalse(mot_de_passe(etat) == mot_de_passe(self.etat))

    def test_adresse_codespaces_fournie_par_github(self):
        with patch.dict(os.environ, {"CODESPACES": "true", "CODESPACE_NAME": "atlas-personnel-abc",
                                     "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev"}):
            self.assertEqual(origine_codespaces(8051), "https://atlas-personnel-abc-8051.app.github.dev")
            with patch.dict(os.environ, {"CODESPACE_NAME": ""}), self.assertRaises(RuntimeError):
                origine_codespaces(8051)
