import unittest

from planning import defaults, parameters, run_plan
from planning.forecast import REGIONS, backtest, residual_allocation
from planning.quantile import QUANTILES, evaluate, fit, loss, predict, steps


def observed(year, region, indicator, value):
    return dict(region=region,year=year,cycle="primaire",indicator=indicator,value=value,
                table="COLLECTE",sex="total",status="public",origin="observed")


def fixture():
    data, demo = [], []
    for y in range(2016,2026):
        total = 0
        for i,reg in enumerate(REGIONS):
            pupils=150+5*i+3*(y-2016)
            total+=pupils
            data.append(dict(region=reg,year=y,cycle="primaire",value=pupils+150,table="PRI01",sex="total"))
            for indicator,v in [("effectifs_publics_simules",pupils),("enseignants_simules",3+i%5),
                                ("salles_primaires_simulees",7-i%5)]:
                demo.append(dict(region=reg,year=y,cycle="primaire",indicator=indicator,value=v,
                                 table="DEMO",sex="total",status="public",origin="synthetic"))
        data.append(dict(region="national",year=y,cycle="primaire",value=total,table="PRI02",sex="total",status="public"))
    return data,demo


class Planning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs,cls.demo=fixture()

    def test_trajectories_reconcile_and_holdouts_are_chronological(self):
        r=run_plan(self.obs,{},self.demo,mode="projection")
        self.assertEqual([v["year"] for v in r["trajectories"]],list(range(2026,2051)))
        self.assertEqual(r["meta"]["model"],"quantile95")
        self.assertEqual(r["meta"]["learning"]["fitted"]["examples"],17)
        old=run_plan(self.obs,{"model":"auto"},self.demo,mode="projection")
        self.assertEqual(old["meta"]["model"],"trend")
        self.assertEqual(old["trajectories"][-1]["haut"],round(old["trajectories"][-1]["central"]*1.2))
        self.assertEqual(r["regional"],[])
        for row in r["trajectories"]:
            for sc in ("bas","central","haut"):
                self.assertEqual(row[sc],sum(v[sc] for v in r["regional_trajectories"] if v["year"]==row["year"]))
            self.assertLessEqual(0,row["bas"])
            self.assertLessEqual(row["bas"],row["central"])
            self.assertLessEqual(row["central"],row["haut"])
        # Tous les entraînements ont ici exclusivement des zéros. L'apparition du
        # pic au dernier millésime implique les mêmes erreurs pour les trois modèles.
        _, metrics=backtest([(y,0 if y<2025 else 100) for y in range(2016,2026)])
        for metric in metrics:
            n=7-metric["horizon"]
            self.assertEqual(metric["n"],n)
            self.assertAlmostEqual(metric["mae"],100/n,places=2)
            self.assertAlmostEqual(metric["bias"],-100/n,places=2)

    def test_learned_quantiles_minimize_loss_without_looking_ahead(self):
        series=list(zip(range(2016,2026),[100,115,112,125,128,120,143,151,134,139]))
        phi=.8
        fitted=fit(series,phi)
        examples=[(steps(h,phi),series[i+h][1]-v) for i,(_,v) in enumerate(series)
                  for h in (1,2) if i+h<len(series)]
        for key,tau in QUANTILES.items():
            def objective(b):
                return sum(loss(d-x*b,tau) for x,d in examples)
            expected=min(objective(d/x) for x,d in examples)
            self.assertAlmostEqual(objective(fitted["slopes"][key]),expected)
        future=predict(139,25,fitted,phi)
        self.assertLess(future["bas"],future["central"])
        self.assertLess(future["central"],future["haut"])
        # Le pic de 2025 n'entre dans aucun ajustement servant à le prédire.
        spike=[(y,100 if y==2025 else 0) for y in range(2016,2026)]
        selected,scores,_=evaluate(spike,"ml_auto")
        self.assertEqual(selected,"quantile80")
        for s in scores:
            self.assertEqual(s["n"],7-s["horizon"])
            self.assertAlmostEqual(s["mae"],100/s["n"],places=2)
            self.assertAlmostEqual(s["pinball"],50/s["n"],places=2)
        self.assertIsNone(fit([(2016,1),(2019,2),(2022,3),(2025,4)],phi))

    def test_all_demand_scenarios_drive_resource_calculation(self):
        series=[1000,1250,940,1120,1050,1240,1500,1490,1240,1400]
        obs=[dict(r,value=series[r["year"]-2016]) if r["table"]=="PRI02" else r for r in self.obs]
        demands=[]
        for sc in QUANTILES:
            plan=run_plan(obs,{"scenario":sc,"regional_mix":"proportional"},self.demo)
            target=plan["trajectories"][-1][sc]
            rows=[v for v in plan["regional"] if v["option"]=="combine"]
            self.assertTrue(rows)
            self.assertEqual(sum(v["demand"] for v in rows),target)
            demands.append(target)
        self.assertLess(demands[0],demands[1])
        self.assertLess(demands[1],demands[2])

    def test_scope_ignores_external_observations_and_demo(self):
        p={"year":2030}
        a=run_plan(self.obs,p,self.demo,regions=["centre"])
        b=run_plan([r for r in self.obs if r["region"]=="centre"],p,
                   [r for r in self.demo if r["region"]=="centre"],regions=["centre"])
        self.assertEqual(a,b)
        self.assertTrue(all(row["region"]=="centre" for row in a["regional"]))
        self.assertFalse(any(row["kind"]=="ventilation" for row in a["sensitivity"]))
        self.assertEqual(a["historical"][-1]["origin"],"estimate")
        with self.assertRaises(ValueError):
            run_plan(self.obs,{"mix_weight":0.5},self.demo,regions=["centre"])

    def test_missing_inputs_remain_missing(self):
        r=run_plan(self.obs,{},[])
        self.assertTrue(r["trajectories"])
        self.assertFalse(r["regional"])
        for row in r["comparison"]:
            self.assertIsNone(row["unserved"])
            self.assertFalse(row["available"])
        empty=run_plan([],{"cycle":"prescolaire"},[])
        self.assertEqual(empty["trajectories"],[])
        self.assertIsNone(empty["comparison"][0]["demand"])

    def test_conservation_and_action_availability(self):
        p=dict(year=2027,programme_start=2027,class_size=30,room_availability=1,teacher_availability=1,match_factor=1,
               room_disruption=0,room_retirement=0,staff_departure=0,annual_transfers=2,
               annual_rooms=2,annual_teachers=2,annual_rehab=0,construction_delay=2)
        r=run_plan(self.obs,p,self.demo)
        for row in r["regional"]:
            self.assertEqual(row["served"]+row["unserved"],row["demand"])
            self.assertLessEqual(row["served"],30*min(row["teachers"],row["rooms"]))
        baseline=next(x for x in r["comparison"] if x["option"]=="reference")
        redeployed=next(x for x in r["comparison"] if x["option"]=="redeploiement")
        self.assertEqual(baseline["teachers"],redeployed["teachers"])
        self.assertLessEqual(redeployed["transfers"],4)
        by_region={v["region"]:v for v in r["regional"] if v["option"]=="reference"}
        moves=[v for v in r["regional"] if v["option"]=="redeploiement"]
        self.assertEqual(sum(v["transfers"] for v in moves),sum(v["outgoing"] for v in moves))
        for zone in moves:
            self.assertGreaterEqual(zone["served"],by_region[zone["region"]]["served"])
        for v in r["annual_options"]:
            if v["year"]==2026:
                self.assertEqual(v["new_rooms"],0)
        self.assertTrue(all(v["year"] in range(2027,2032) for v in r["programme"]))

    def test_constrained_allocations_and_incremental_costs(self):
        p=dict(room_cost=800,rehab_cost=400,salary_cost=300,maintenance_cost=100,
               investment_budget=1100,operating_budget=1400,year=2030)
        r=run_plan(self.obs,p,self.demo)
        for v in r["annual_options"]:
            self.assertLessEqual(v["annual_investment"],p["investment_budget"])
            self.assertLessEqual(v["additional_operating_reserved"],p["operating_budget"])
            self.assertEqual(v["investment"],v["new_rooms"]*800+v["rehabilitated"]*400)
            self.assertGreaterEqual(v["operating"],0)
            self.assertEqual(v["served"]+v["unserved"],v["demand"])
            self.assertLessEqual(v["annual"]["new_rooms"],20)
            self.assertLessEqual(v["annual"]["new_teachers"],25)

    def test_collected_prices_and_ringfenced_budgets(self):
        def financial(reg,year,code,value,unit,price_year=2025):
            return dict(**observed(year,reg,code,value),unit=unit,price_year=price_year,source="Bordereau validé")
        resources=[]
        for reg in REGIONS:
            resources.extend([financial(reg,2025,"cout_salle",1300,"FCFA/salle"),
                              financial(reg,2025,"cout_rehabilitation",600,"FCFA/salle"),
                              financial(reg,2025,"cout_enseignant",550,"FCFA/poste/an"),
                              financial(reg,2025,"cout_maintenance",50,"FCFA/salle/an")])
            resources.append(financial(reg,2027,"budget_investissement",0,"FCFA"))
            # La contrainte salariale future est réservée dès le recrutement.
            resources.append(financial(reg,2029,"budget_fonctionnement",0,"FCFA"))
        resources.append(financial("centre",2024,"cout_salle",12,"FCFA/salle",2018))
        p=dict(year=2027,construction_delay=1,programme_start=2026,room_cost=600,rehab_cost=10,
               operating_budget=1000000,investment_budget=100000)
        result=run_plan(self.obs+resources,p,self.demo)
        for r in result["annual_options"]:
            if r["year"]<=2029:
                self.assertEqual(r["new_teachers"]+r["new_rooms"]+r["rehabilitated"],0)
            if r["year"]==2027:
                self.assertEqual(r["annual_investment"],0)
            self.assertEqual(r["operating"],r["rooms"]*50+r["teacher_headcount"]*550)
        self.assertTrue(any("année de prix" in t for t in result["prerequisites"]))
        self.assertTrue(result["meta"]["financial_sources"])
        # Une région n'a pas accès aux bordereaux d'un autre périmètre.
        scoped=run_plan(self.obs+resources,p,self.demo,regions=["centre"])
        self.assertEqual({r["region"] for r in scoped["meta"]["financial_sources"]},{"centre"})

    def test_transfer_never_spends_staff_or_construction_quota(self):
        p=dict(year=2026,class_size=30,room_availability=1,teacher_availability=1,match_factor=1,
               annual_rooms=0,annual_teachers=0,annual_rehab=0,annual_transfers=2,staff_departure=0,
               room_disruption=0,room_retirement=0,training_delay=8,construction_delay=8,
               operating_budget=0,investment_budget=0,salary_cost=350,maintenance_cost=100,room_cost=800,rehab_cost=500)
        tariffs=[dict(**observed(2025,k,"cout_enseignant",1000+i*100),unit="FCFA/poste/an",price_year=2025)
                 for i,k in enumerate(REGIONS)]
        result=run_plan(self.obs+tariffs,p,self.demo)
        used=next(c for c in result["comparison"] if c["option"]=="redeploiement")
        self.assertEqual(used["operating"],result["comparison"][0]["operating"])
        self.assertGreater(used["transfers"],0)
        self.assertEqual(used["new_teachers"]+used["new_rooms"]+used["rehabilitated"],0)
        self.assertEqual(used["investment"],0)
        self.assertEqual(used["additional_operating_reserved"],0)
        self.assertEqual(sum(r["outgoing"] for r in result["regional"] if r["option"]=="redeploiement"),used["transfers"])

    def test_actual_resources_take_precedence_and_rebasing(self):
        new=[observed(2026,reg,metric,val) for reg in REGIONS for metric,val in
             (("effectifs_publics_regionaux",100),("salles_utilisables",4),("enseignants_disponibles",4))]
        p=dict(base_year=2026,year=2027,regional_mix="none",room_availability=0,teacher_availability=0,
               room_retirement=0,staff_departure=0,room_disruption=0)
        r=run_plan(self.obs+new,p,self.demo)
        self.assertEqual(r["historical"][-1],{"year":2026,"origin":"observed","value":1300})
        self.assertEqual(r["trajectories"][0]["year"],2027)
        self.assertTrue(r["comparison"][0]["available"])
        self.assertEqual(r["comparison"][0]["teachers"],52)
        self.assertEqual(r["comparison"][0]["rooms"],52)
        self.assertEqual(r["meta"]["data_origins"]["regional_enrolment"],"observed")

    def test_partial_collection_respects_margins(self):
        actual=observed(2025,"centre","effectifs_publics_regionaux",0)
        r=run_plan(self.obs+[actual],{"year":2030},self.demo)
        row=next(v for v in r["regional_trajectories"] if v["region"]=="centre")
        self.assertEqual(row["central"],0)
        self.assertEqual(residual_allocation(9,{"a":8,"b":1},{"a":3,"b":9}),{"a":3,"b":6})
        with self.assertRaises(ValueError):
            run_plan(self.obs+[observed(2025,"centre","effectifs_publics_regionaux",9999)],{},self.demo)

    def test_parameters_rejected_without_computing(self):
        for value in ({"operating_budget":10},{"class_size":True},{"scenario_spread":float("nan")},
                      {"model":"unknown"},{"year":2051},{"unused":0}):
            with self.assertRaises(ValueError):
                parameters(value)
        self.assertNotEqual(defaults("primaire")["class_size"],defaults("prescolaire")["class_size"])


if __name__=="__main__":
    unittest.main()
