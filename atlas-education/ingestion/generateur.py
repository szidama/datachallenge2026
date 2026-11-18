"""Générateur illustratif alternatif. Les paramètres n'ont aucune valeur normative."""
import csv
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from .lecture import require
from .referentiel import REGIONS

FIELDS = ("region","year","cycle","indicator","sex","status","value","unit","origin","method","generator_version","seed","official")


def bounded_allocation(target, capacities, weights):
    """Plus forts restes avec plafond régional et renormalisation des poids résiduels."""
    require(0 <= target <= sum(capacities.values()), "Marge nationale hors capacité.")
    result = {region:0 for region in capacities}
    active = [r for r in capacities if capacities[r]>0]
    while target:
        weight = sum(weights[r] for r in active)
        require(weight>0, "Aucun poids positif pour allouer le résidu.")
        quotas = {r:Fraction(target)*weights[r]/weight for r in active}
        saturated = [r for r in active if quotas[r]>=capacities[r]]
        if saturated:
            for r in saturated:
                result[r] = capacities[r]
                target -= capacities[r]
                active.remove(r)
            continue
        for r in active:
            result[r] = int(quotas[r])
        remainder = target-sum(result[r] for r in active)
        top = sorted(active,key=lambda r:(-(quotas[r]-result[r]),r))
        for r in top[:remainder]:
            result[r] += 1
        break
    return result


def generate_demo(observed_payload, destination, mix=0.5, seed="ATLAS-DEMO-V2"):
    """Génère un CSV indépendant. mix=0 pondère seulement par effectif ; mix=1 inclut le poids des écoles publiques."""
    destination = Path(destination)
    require(0 <= mix <= 1 and isinstance(seed,str) and 0<len(seed)<=80, "Poids hors de [0,1] ou graine invalide.")
    factor = Fraction(Decimal(str(mix)))
    rows = {(o["table"],o["year"],o["region"],o["status"],o["sex"]):o["value"]
            for o in observed_payload["observations"] if o["table"] in ("PRI01","PRI02","PRI13")}
    years = sorted({k[1] for k in rows if k[0]=="PRI02"})
    output = []
    for year in years:
        assigned = {}
        for sex in ("garcons","filles"):
            capacities = {r:rows["PRI01",year,r,None,sex] for r in REGIONS}
            weights = {}
            for r in REGIONS:
                schools = rows["PRI13",year,r,"total",None]
                public = rows["PRI13",year,r,"public",None]
                require(isinstance(capacities[r],int) and isinstance(schools,int) and schools>0 and
                        isinstance(public,int) and public<=schools,"Marges d'établissements ou d'inscriptions insuffisantes.")
                weights[r] = capacities[r]*(1-factor+factor*Fraction(public,schools))
            target = rows["PRI02",year,"national","public",sex]
            require(isinstance(target,int),"Effectif national manquant.")
            assigned[sex] = bounded_allocation(target,capacities,weights)

        def add(region, indicator, sex, value, unit, method):
            output.append(dict(region=region,year=year,cycle="primaire",indicator=indicator,sex=sex,status="PUBLIC",
                          value=value,unit=unit,origin="SYNTHETIC_DEMO",method=method,generator_version="atlas-v2.0",
                          seed=seed,official="False"))

        for r in REGIONS:
            total = assigned["garcons"][r]+assigned["filles"][r]
            for sex in ("garcons","filles"):
                add(r,"inscrits_publics_synthetiques",sex.upper(),assigned[sex][r],"eleves",
                    f"Répartition plafonnée au plus fort reste ; pondération des écoles publiques {mix:g}")
            add(r,"inscrits_publics_synthetiques","TOTAL",total,"eleves","Somme des inscriptions synthétiques par sexe")
            for indicator,unit,low,high in (("salles_primaires_synthetiques","salles",44,53),
                                           ("enseignants_synthetiques","personnes",40,53)):
                digest = sha256(f"{seed}/{r}/{year}/{indicator}".encode()).digest()
                ratio = low+int.from_bytes(digest[:4],"big")%(high-low+1)
                # Plafond entier, aucun stock prétendu disponible en classe.
                add(r,indicator,"TOTAL",(total+ratio-1)//ratio,unit,
                    f"Plafond des inscriptions synthétiques divisées par le ratio illustratif {ratio}")
    with destination.open("x",encoding="utf-8",newline="") as f:
        writer = csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
