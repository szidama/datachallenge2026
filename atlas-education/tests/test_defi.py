"""Contrôles du cadrage et du référentiel spatial historique du défi."""
import json
import unittest
from pathlib import Path

from ingestion import REGIONS
from planning.forecast import BASE, END

ROOT = Path(__file__).resolve().parents[1]


class DefiTests(unittest.TestCase):
    def test_mandat(self):
        self.assertEqual((BASE, END), (2025, 2050))
        self.assertEqual(len(REGIONS), 13)
        cadrage = (ROOT / "docs/Cadrage-et-recette.md").read_text()
        for number in range(15):
            self.assertIn(f"### M{number:02} ·", cadrage)
        self.assertIn("Dix fiches analytiques", cadrage)

    def test_carte_historique(self):
        shapes = json.loads((ROOT / "web/assets/regions.json").read_text())
        self.assertEqual(set(shapes), set(REGIONS))
        provinces = [p for area in shapes.values() for p in area["provinces"]]
        self.assertEqual(len(provinces), 45)
        self.assertEqual(len(set(provinces)), 45)
        for area in shapes.values():
            self.assertTrue(area["path"].startswith("M") and area["path"].endswith("Z"))
            self.assertTrue(area["capital"])

    def test_jointure_provinciale(self):
        from planning.provinces import SNAPSHOT
        s = json.loads(SNAPSHOT.read_text())
        geo = json.loads((ROOT / "web/assets/regions.json").read_text())
        self.assertEqual({(r["region"],r["province"]) for r in s["rows"]},
                         {(k,v) for k,area in geo.items() for v in area["provinces"]})
        self.assertEqual(len(s["rows"]), 45)
        self.assertTrue(all(r["localities_page"] > 0 for r in s["rows"]))

    def test_controle_annuaire_et_population(self):
        from planning.provinces import SNAPSHOT
        data = json.loads(SNAPSHOT.read_text())
        totals = dict(schools=9526, rooms=45921, groups=45543, teachers=44623, enrolment=2391345, water=7343, latrines=8001)
        self.assertEqual(data["totals"], totals)
        for key, total in totals.items():
            self.assertEqual(sum(r[key] for r in data["rows"]), total)
        for r in data["rows"]:
            self.assertEqual(sorted(map(int,r["population"])),list(range(2020,2036)))
            self.assertTrue(0 <= r["water"] <= r["schools"] and 0 <= r["latrines"] <= r["schools"])
            self.assertTrue(12 <= r["inventory_page"] <= 16 and 279 <= r["wash_page"] <= 281)
        oudalan = next(r for r in data["rows"] if r["province"]=="Oudalan")
        self.assertEqual(oudalan["adjustments"], [dict(year=2031,page=466,printed=17030,male=17066,female=16511)])
        self.assertEqual(oudalan["population"]["2031"], 33577)
        self.assertTrue(all(len(s["sha256"])==64 for s in data["sources"].values()))

    @staticmethod
    def source():
        from ingestion import import_workbook
        return import_workbook(next(ROOT.parent.glob("DONNEES_STATISTQUES*.xlsx")))

    def test_projections_provinciales(self):
        from planning import run_plan
        data = self.source()
        for year in (2030,2035,2050):
            result = run_plan(data,dict(regional_mix="annuaire",year=year),mode="projection")
            info=result["provincial"]
            self.assertEqual(info["weight_year"], min(year,2035))
            self.assertEqual(len(info["rows"]),45)
            for r in info["rows"]:
                self.assertEqual(r["population_target"] is None,year>2035)
                self.assertLessEqual(r["demand"]["bas"],r["demand"]["central"])
                self.assertLessEqual(r["demand"]["central"],r["demand"]["haut"])
            for p in (z for z in result["regional_trajectories"] if z["year"]==year):
                for sc in ("bas","central","haut"):
                    self.assertEqual(sum(r["demand"][sc] for r in info["rows"] if r["region"]==p["region"]),p[sc])
            for t in result["trajectories"]:
                for sc in ("bas","central","haut"):
                    self.assertEqual(t[sc],sum(r[sc] for r in result["regional_trajectories"] if r["year"]==t["year"]))
        scoped=run_plan(data,{"regional_mix":"annuaire"},regions=["nord"],mode="projection")
        self.assertEqual({r["region"] for r in scoped["provincial"]["rows"]},{"nord"})
        self.assertFalse(scoped["trajectories"])
        self.assertFalse(scoped["provincial"]["rows"][0]["demand"])

    def test_stocks_annuaire_et_simulation(self):
        from planning import run_plan
        from math import ceil
        source=self.source()
        for sc in ("bas","central","haut"):
            r=run_plan(source,dict(regional_mix="annuaire",scenario=sc))
            self.assertTrue(r["comparison"][0]["available"])
            self.assertNotIn("synthetic", {x.get("origin") for x in r["source_references"]})
            for p in r["provincial"]["rows"]:
                n=ceil(p["demand"][sc]/r["provincial"]["seats"])
                self.assertEqual(p["rooms_gap"],max(0,n-p["rooms"]))
                self.assertEqual(p["teachers_gap"],max(0,n-p["teachers"]))
            for option in ("reference","combine"):
                summary=next(x for x in r["comparison"] if x["option"]==option)
                regional=[x for x in r["regional"] if x["option"]==option]
                self.assertEqual(len(regional),13)
                for field in ("rooms_needed","teachers_needed","demand","unserved"):
                    self.assertEqual(summary[field],sum(x[field] for x in regional))

    def test_compatibilite_et_conflits(self):
        from planning import run_plan
        from test_planning import observed
        base=self.source()["observations"]
        for params in [dict(cycle="prescolaire"),dict(base_year=2026)]:
            with self.assertRaisesRegex(ValueError,"2024–2025"):
                run_plan(base,{"regional_mix":"annuaire",**params})
        with self.assertRaisesRegex(ValueError,"contredit"):
            run_plan(base+[observed(2025,"centre","effectifs_publics_regionaux",1)],{"regional_mix":"annuaire"})
        historical=run_plan(base,{"regional_mix":"none"},mode="projection")
        self.assertNotIn("provincial",historical)
