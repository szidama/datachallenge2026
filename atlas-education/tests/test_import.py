import copy
import csv
import os
from pathlib import Path
import tempfile
import unittest

from ingestion import CATALOGUE, REGIONS, import_demo, import_workbook
from ingestion.lecture import end_year, normalize
from ingestion.generateur import bounded_allocation, generate_demo
from ingestion.qualite import reconcile


class ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(os.environ.get("ATLAS_SOURCE_DIR", Path(__file__).resolve().parents[2]))
        cls.path = next(work.glob("DONNEES_STATISTQUES*.xlsx"))
        cls.csv = work / "synthetic_demo.csv"
        cls.data = import_workbook(cls.path)
        cls.rows = {r["id"]:r for r in cls.data["observations"]}

    def test_manifest(self):
        meta = self.data["metadata"]
        self.assertEqual(meta["counts"]["sheets"],14)
        self.assertEqual(meta["counts"]["tables"],21)
        self.assertEqual(len(self.rows),len(self.data["observations"]))
        self.assertEqual(len(self.rows),6636)
        self.assertEqual(len(REGIONS),13)
        self.assertEqual(len(meta["sha256"]),64)
        self.assertEqual(meta["checks"]["valeurs_enregistrees_formules"],420)
        self.assertEqual(self.rows["PRI10:B3"]["raw"],"=Feuil6!C4/Feuil6!B4")
        self.assertEqual(self.rows["PRI10:B3"]["value"],self.rows["PRI10:B3"]["cached_value"])

    def test_idempotent_normalization(self):
        again = import_workbook(self.path)
        self.assertEqual(again["metadata"]["sha256"],self.data["metadata"]["sha256"])
        self.assertEqual(again["observations"],self.data["observations"])
        self.assertEqual(again["anomalies"],self.data["anomalies"])

    def test_missing_and_indeterminate(self):
        absent = self.rows["PRE03:B32"]
        self.assertEqual((absent["area"],absent["year"],absent["state"],absent["value"]),
                         ("indetermine",2018,"missing",None))
        zero = self.rows["PRE07:C99"]
        self.assertEqual((zero["status"],zero["state"],zero["value"]),("communautaire","available",0))
        self.assertEqual(normalize("s.o.","eleves","0")[:2],(None,"not_applicable"))
        self.assertEqual(normalize("3,5","pourcent","0.0")[:2],(3.5,"available"))

    def test_dimensions_and_periods(self):
        years = {t["id"]:t["years"] for t in self.data["tables"]}
        self.assertEqual(years["PRE03"],list(range(2018,2026)))
        self.assertEqual(years["PRI09"],list(range(2016,2026)))
        self.assertEqual(self.rows["PRI13:C27"]["region"],"hauts-bassins")
        self.assertEqual(self.rows["PRI13:C27"]["raw_dimensions"]["region"],"HAUT-BASSINS")
        self.assertEqual(self.rows["PRI04:D45"]["level"],"total")
        self.assertEqual(self.rows["PRI01:C3"]["status"],None)
        self.assertEqual(self.rows["PRE08:C158"]["unit"],"salles")
        self.assertEqual(self.rows["PRI13:C3"]["unit"],"ecoles")
        self.assertEqual(end_year("2024/25"),2025)
        with self.assertRaises(ValueError):
            end_year("2024/26")

    def test_source_ips_and_rates_unchanged(self):
        original = self.rows["PRE06:F77"]
        self.assertEqual(original["raw"],1)
        self.assertEqual(original["value"],1)
        issues = [a for a in self.data["anomalies"] if a["code"]=="ips_incoherent"]
        self.assertEqual(len(issues),1)
        self.assertEqual(issues[0]["references"],["PRESCOLAIRE!O59","PRESCOLAIRE!N59"])
        self.assertAlmostEqual(issues[0]["expected"],0.9114263023285987)
        self.assertGreater(self.rows["PRI07:D6"]["value"],100)
        self.assertEqual(CATALOGUE["ips_tbs"]["unit"],"rapport")

    def test_integrity_detection(self):
        rows = [dict(r) for r in self.data["observations"]]
        next(r for r in rows if r["id"]=="PRI02:C5")["value"] += 1
        _, issues = reconcile(rows)
        self.assertTrue(any(a["code"]=="somme_sex" and a["cell"]=="C5" for a in issues))
        self.assertTrue(any(a["code"]=="marges_inter_tableaux" for a in issues))

    def test_foreign_text_isolated(self):
        isolated = [a for a in self.data["anomalies"] if a["code"]=="texte_isole"]
        self.assertEqual(len(isolated),18)
        self.assertTrue(any(a["sheet"]=="Feuil1" and a["cell"]=="F2" for a in isolated))
        self.assertTrue(all(len(a["raw_hash"])==64 for a in isolated))
        self.assertEqual(self.rows["PRI01:F3"]["period_header"],"2018-2019")

    def test_demo_margins_coverage_and_lineage(self):
        demo = import_demo(self.csv,self.data)
        self.assertEqual(len(demo["observations"]),650)
        self.assertEqual(demo["metadata"]["checks"]["marges_nationales_publiques"],30)
        self.assertEqual(demo["metadata"]["observed_source"],self.data["metadata"]["sha256"])
        self.assertTrue(all(r["origin"]=="synthetic" and r["official"] is False and r["method"]
                            for r in demo["observations"]))
        for r in demo["observations"]:
            self.assertIn(r["region"],REGIONS)
            self.assertEqual(r["cycle"],"primaire")
            self.assertEqual(r["status"],"public")

    def test_generator_reproducibility_and_sensitivity(self):
        with tempfile.TemporaryDirectory() as tmp:
            files=[Path(tmp)/f"simulation-{i}.csv" for i in range(3)]
            for path,mix in zip(files,(0.5,0.5,1)):
                generate_demo(self.data,path,mix)
            self.assertEqual(files[0].read_bytes(),files[1].read_bytes())
            self.assertNotEqual(files[1].read_bytes(),files[2].read_bytes())
            self.assertEqual(import_demo(files[2],self.data)["metadata"]["checks"]["marges_nationales_publiques"],30)
            with self.assertRaises(FileExistsError):
                generate_demo(self.data,files[0])
        self.assertEqual(bounded_allocation(9,{"a":2,"b":8},{"a":100,"b":1}),{"a":2,"b":7})

    def test_duplicate_partial_margins_and_provenance_rejected(self):
        with self.csv.open(newline="") as f:
            source=list(csv.DictReader(f))
        with tempfile.TemporaryDirectory() as tmp:
            for problem in ("duplicate","incomplete","margin","origin"):
                rows = copy.deepcopy(source)
                if problem=="duplicate":
                    rows.append(rows[0])
                if problem=="incomplete":
                    rows.pop()
                if problem=="margin":
                    rows[0]["value"]=str(int(rows[0]["value"])+2)
                    rows[2]["value"]=str(int(rows[2]["value"])+2)
                if problem=="origin":
                    rows[0]["official"]="True"
                path=Path(tmp)/"exemple.csv"
                with path.open("w",newline="") as f:
                    writer=csv.DictWriter(f,fieldnames=source[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                with self.subTest(problem=problem),self.assertRaises(ValueError):
                    import_demo(path,self.data)


if __name__=="__main__":
    unittest.main()
