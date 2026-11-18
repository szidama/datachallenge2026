"""Lecture des compléments synthétiques et réconciliation avec les marges observées."""
import csv
from pathlib import Path

from .lecture import canonical, metadata, require
from .referentiel import CATALOGUE, DEMO_INDICATORS, REGIONS


def import_demo(path, observed_payload):
    path = Path(path)
    require(path.stat().st_size < 3_000_000,"CSV de démonstration trop volumineux.")
    meta = metadata(path)
    meta["version"] = meta["sha256"]
    observations = observed_payload["observations"] if isinstance(observed_payload,dict) else observed_payload
    by_scope = {(r["table"],r["region"],r["year"],r["sex"]):r for r in observations
                if r["table"]=="PRI01" or (r["table"]=="PRI02" and r["status"]=="public")}
    result, lookup = [], {}
    with path.open(encoding="utf-8-sig",newline="") as f:
        source = csv.DictReader(f)
        expected = {"region","year","cycle","indicator","sex","status","value","unit","origin","method",
                    "generator_version","seed","official"}
        require(source.fieldnames and set(source.fieldnames)==expected,"Colonnes du complément CSV incompatibles.")
        for i,r in enumerate(source,2):
            ref = f"ligne {i}"
            require(r["indicator"] in DEMO_INDICATORS and r["region"] in REGIONS and r["cycle"]=="primaire"
                    and r["status"]=="PUBLIC" and r["official"].lower()=="false" and r["origin"]=="SYNTHETIC_DEMO",
                    f"Provenance ou dimension incompatible à la {ref}.")
            indicator,unit,_ = DEMO_INDICATORS[r["indicator"]]
            require(unit==r["unit"] and r["method"] and r["generator_version"] and r["seed"],f"Métadonnées manquantes ({ref}).")
            year = int(r["year"])
            require(2016<=year<=2050,f"Période non prise en charge ({ref}).")
            sex = canonical("sex",r["sex"])
            require(indicator=="effectifs_publics_simules" or sex=="total", f"Ventilation inattendue ({ref}).")
            require(r["value"].isascii() and r["value"].isdigit(),f"Effectif positif ou nul exigé ({ref}).")
            value = int(r["value"])
            require(value < 100_000_000,f"Effectif hors échelle ({ref}).")
            key = (r["region"],year,sex,indicator)
            require(key not in lookup,f"Doublon dans le complément CSV ({ref}).")
            lookup[key] = value
            result.append(dict(id=f"DEMO:{i}",indicator=indicator,cycle="primaire",region=r["region"],year=year,sex=sex,
                status="public",area=None,level=None,unit=unit,value=value,state="available",origin="synthetic",
                table="DEMO",sheet="CSV",cell=ref,raw=r["value"],transforms=["texte_numerique"],source=path.name,
                version=meta["version"],raw_dimensions={k:r[k] for k in ("region","sex","status")},period_header=r["year"],
                cached_value=None,method=r["method"],seed=r["seed"],generator_version=r["generator_version"],official=False))
    years = sorted({r["year"] for r in result})
    require(years and years==list(range(2016,years[-1]+1)) and years[-1]>=2025,"Couverture temporelle incomplète.")
    checks=0
    pupil="effectifs_publics_simules"
    for year in years:
        for reg in REGIONS:
            for indicator,unit,label in DEMO_INDICATORS.values():
                required_sexes = ("garcons","filles","total") if indicator==pupil else ("total",)
                for sex in required_sexes:
                    key=reg,year,sex,indicator
                    require(key in lookup,f"Clé de simulation manquante {key}.")
                    if indicator==pupil:
                        margin=by_scope.get(("PRI01",reg,year,sex))
                        require(margin and margin["value"] is not None and lookup[key]<=margin["value"],
                                f"Inscription simulée supérieure au total régional ou total indisponible {key}.")
            require(lookup[reg,year,"total",pupil]==sum(lookup[reg,year,s,pupil] for s in ("garcons","filles")),
                    f"Somme par sexe incohérente en {year}, {reg}.")
        for sex in ("garcons","filles","total"):
            margin=by_scope.get(("PRI02","national",year,sex))
            require(margin and margin["value"] == sum(lookup[r,year,sex,pupil] for r in REGIONS),
                    f"Marge nationale publique incompatible en {year}, {sex}.")
            checks+=1
    table=dict(id="DEMO",cycle="primaire",sheet="CSV",years=years,start=years[0],end=years[-1],
               dimensions=["region","sex","status"],observations=len(result))
    meta.update(origin="synthetic",official=False,counts=dict(observations=len(result),tables=1,regions=len(REGIONS),
                anomalies=0,available=len(result)),checks=dict(marges_nationales_publiques=checks),
                observed_source=observed_payload.get("metadata",{}).get("sha256") if isinstance(observed_payload,dict) else None)
    return dict(metadata=meta,observations=result,anomalies=[],catalogue={k[0]:CATALOGUE[k[0]] for k in DEMO_INDICATORS.values()},
                tables=[table])


def import_synthetic(path, observations):
    return import_demo(path, observations)["observations"]
