"""Diagnostic provincial du primaire public sur la géographie des annuaires."""
import json
from math import ceil, floor
from pathlib import Path

from .forecast import SCENARIOS, spread_integers

SNAPSHOT = Path(__file__).parent / "data/provinces_2025.json"


def inventory(real, scope):
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    rows = [r for r in snapshot["rows"] if r["region"] in scope]
    margins = {k: {r: sum(x[k] for x in rows if x["region"] == r) for r in scope}
               for k in ("enrolment", "rooms", "teachers")}
    collected = {r["region"]: r["value"] for r in real if r.get("table") == "COLLECTE"
                 and r.get("origin") == "observed" and r.get("cycle") == "primaire" and r.get("status") == "public"
                 and r.get("sex") == "total" and r.get("year") == 2025 and r.get("indicator") == "effectifs_publics_regionaux"}
    for region, number in margins["enrolment"].items():
        if region in collected:
            if collected[region] != number:
                raise ValueError(f"L’effectif public collecté pour {region} contredit le total provincial de l’annuaire 2024–2025.")
            continue
        real.append(dict(table="COLLECTE", cycle="primaire", status="public", sex="total", origin="observed",
                         region=region, year=2025, indicator="effectifs_publics_regionaux", value=number,
                         id="DGESS-I.1-"+region, source="Annuaire primaire 2024–2025, tableau I.1",
                         version=snapshot["sources"]["annuaire"]["sha256"]))
    return rows, margins, snapshot["sources"]


def allocate(rows, totals, params, sources):
    """Les incréments inter-quantiles entiers garantissent l'emboîtement des trois trajectoires."""
    school_base = "2025"
    regions = list(dict.fromkeys(row["region"] for row in rows))
    detail, selected = {}, {}
    for point in totals:
        year = point["year"]
        weight_year = str(min(year, 2035))
        weights = {r["province"]: r["enrolment"] * r["population"][weight_year] / r["population"][school_base]
                   for r in rows}
        prior = dict.fromkeys(weights, 0)
        previous_total = 0
        detail[year] = {}
        for sc in SCENARIOS:
            increment = spread_integers(point[sc]-previous_total, weights)
            distribution = {k: v + increment[k] for k, v in prior.items()}
            detail[year][sc] = {k: sum(distribution[r["province"]] for r in rows if r["region"] == k) for k in regions}
            if year == params["year"]:
                selected[sc] = distribution
            previous_total, prior = point[sc], distribution
    q = max(1, floor(params["class_size"] * params["match_factor"]))
    horizon = params["year"]
    diagnostic = []
    for row in rows:
        base_population = row["population"][school_base]
        target_population = row["population"].get(str(horizon))
        name = row["province"]
        demand = {sc: selected[sc][name] for sc in SCENARIOS} if selected else {}
        groups = ceil(demand[params["scenario"]]/q) if demand else None
        schools, rooms, teachers, enrolment = (row[k] for k in ("schools","rooms","teachers","enrolment"))
        diagnostic.append(dict(province=name, region=row["region"], enrolment=enrolment, schools=schools,
            rooms=rooms, teachers=teachers, population_base=base_population, population_target=target_population,
            enrolment_per_child=enrolment/base_population, pupils_per_room=enrolment/rooms if rooms else None,
            pupils_per_teacher=enrolment/teachers if teachers else None,
            without_water=schools-row["water"], without_latrines=schools-row["latrines"], demand=demand,
            rooms_gap=max(0, groups-rooms) if groups is not None else None,
            teachers_gap=max(0, groups-teachers) if groups is not None else None,
            inventory_page=row["inventory_page"], wash_page=row["wash_page"], localities_page=row["localities_page"],
            population_pages=row["population_pages"], adjustments=row["adjustments"]))
    return detail, dict(year=horizon, scenario=params["scenario"], weight_year=min(horizon,2035), seats=q,
                        sources=sources, rows=diagnostic)
