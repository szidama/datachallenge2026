"""Contrôles des marges compatibles. Les taux nationaux ne sont jamais moyennés."""
from collections import Counter, defaultdict
from math import isclose

from .referentiel import DIMS, LEVELS, REGIONS, TABLES


def reconcile(observations):
    rows = defaultdict(list)
    for obs in observations:
        rows[obs["table"]].append(obs)
    checks, anomalies = Counter(), []

    def flag(row, code, message, expected, refs):
        anomalies.append(dict(code=code,message=message,severity="warning",sheet=row["sheet"],cell=row["cell"],
                              region=row["region"],year=row["year"],table=row["table"],observed=row["value"],
                              expected=expected,references=[f"{x['sheet']}!{x['cell']}" for x in refs]))

    def compare(reported, parts, code):
        if any(r["value"] is None for r in [reported,*parts]):
            checks["verification_partielle_valeur_absente"] += 1
            return
        checks[code] += 1
        expected = sum(r["value"] for r in parts)
        if not isclose(reported["value"],expected,abs_tol=1e-8):
            flag(reported,code,"Écart entre le total publié et les valeurs comparables.",expected,parts)

    for t in TABLES:
        if t.indicator not in {"effectifs","structures","ecoles","nouveaux_cp1","salles_recensees"}:
            continue
        axes = list(t.dims) + (["sex"] if t.grouped_sex else [])
        for axis in axes:
            components = {"region":list(REGIONS), "sex":["garcons","filles"], "level":LEVELS[t.cycle],
                          "area":["urbain","rural"]+(["indetermine"] if t.cycle=="prescolaire" else []),
                          "status":["public","prive"]+(["communautaire"] if t.cycle=="prescolaire" else [])}[axis]
            total_value = "national" if axis == "region" else "total"
            groups = defaultdict(dict)
            for row in rows[t.id]:
                key = (row["year"], *(row[d] for d in DIMS if d!=axis))
                groups[key][row[axis]] = row
            for group in groups.values():
                if total_value in group and all(k in group for k in components):
                    compare(group[total_value], [group[k] for k in components], "somme_"+axis)

    # Même périmètre, même indicateur entre tableaux distincts. Les marges
    # répétées restent attachées à leurs cellules respectives dans le stockage.
    margins = {}
    for row in observations:
        if row["indicator"]!="effectifs" or row["area"] not in (None,"total") or row["level"] not in (None,"total"):
            continue
        if row["region"]!="national":
            continue
        key = (row["cycle"], row["year"], row["status"] or "total", row["sex"])
        previous = margins.setdefault(key,row)
        if previous is not row:
            compare(row,[previous],"marges_inter_tableaux")

    by_index = {(r["table"],r["region"],r["year"],r["sex"]):r for r in observations if r["indicator"] in {"tbs","tba","tap"}}
    for ips, rate in (("PRE06","PRE05"),("PRI10","PRI06"),("PRI11","PRI07"),("PRI12","PRI08")):
        for r in rows[ips]:
            female, male = [by_index.get((rate,r["region"],r["year"],s)) for s in ("filles","garcons")]
            if not female or not male or female["value"] is None or not male["value"] or r["value"] is None:
                checks["verification_ips_indisponible"] += 1
                continue
            expected = female["value"]/male["value"]
            checks["ips_feminin_masculin"] += 1
            # Les taux affichés peuvent avoir été arrondis indépendamment.
            if abs(r["value"]-expected)>0.005:
                flag(r,"ips_incoherent","Écart supérieur à 0,005 entre l’IPS enregistré et le rapport féminin/masculin.",
                     expected,[female,male])
    return checks, anomalies
