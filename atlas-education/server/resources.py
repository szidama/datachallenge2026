"""Contrat d'échange des compléments réels pour un périmètre historique explicite."""
import csv
import hashlib
import io
import math
from .storage import Error, REGIONS, check, textfield

UNITS={"effectifs_publics_regionaux":"eleves","enseignants_disponibles":"personnes","salles_utilisables":"salles",
       "budget_investissement":"FCFA","budget_fonctionnement":"FCFA","cout_salle":"FCFA/salle","cout_enseignant":"FCFA/poste/an",
       "cout_rehabilitation":"FCFA/salle","cout_maintenance":"FCFA/salle/an"}
HEADER="region,year,cycle,indicator,value,unit,source,price_year"

def real_complements(content,areas):
    check(isinstance(content,str) and len(content.encode())<=2_000_000,422,"CSV de collecte trop volumineux.")
    sha=hashlib.sha256(content.encode()).hexdigest()
    reader=csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    check(reader.fieldnames==HEADER.split(","),422,"En-tête CSV attendu : "+HEADER)
    rows=[];seen=set()
    for n,r in enumerate(reader,2):
        region=r["region"];metric=r["indicator"]
        check(region in REGIONS and (areas==["*"] or region in areas),422,f"Région invalide à la ligne {n}.")
        check(r["cycle"] in ("primaire","prescolaire") and metric in UNITS and r["unit"]==UNITS[metric],422,f"Cycle, indicateur ou unité incompatible à la ligne {n}.")
        try: year=int(r["year"]);v=float(r["value"])
        except (ValueError,TypeError): raise Error(422,f"Nombre invalide à la ligne {n}.") from None
        check(2016<=year<=2050 and math.isfinite(v) and v>=0,422,f"Valeur ou année hors limites à la ligne {n}.")
        if r["unit"].startswith("FCFA"):
            check(r["price_year"].isdigit() and 2000<=int(r["price_year"])<=2050,422,f"Année de prix requise à la ligne {n}.")
        else:
            check(v.is_integer(),422,f"Un effectif entier est requis à la ligne {n}.")
            v=int(v)
        key=(region,year,r["cycle"],metric)
        check(key not in seen,422,f"Doublon à la ligne {n}.");seen.add(key)
        rows.append(dict(id=f"{sha[:16]}-{n}",source=textfield(r["source"],"Référence de la source",250),version=sha,
            sheet="collecte",table="COLLECTE",cell=f"E{n}",state="available",origin="observed",region=region,
            cycle=r["cycle"],year=year,indicator=metric,value=v,unit=r["unit"],sex="total",status="public",
            level=None,area=None,raw=r["value"],price_year=r["price_year"] or None,transforms=["conversion numérique, vérification de l’unité"]))
    check(rows,422,"Aucune donnée de collecte.")
    return rows
