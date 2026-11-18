"""Prospective conditionnelle des inscriptions. Aucune extrapolation démographique implicite."""
from collections import defaultdict
from math import floor
from statistics import mean
from . import quantile

BASE = 2025
END = 2050
REGIONS = ("boucle-du-mouhoun", "cascades", "centre", "centre-est", "centre-nord",
           "centre-ouest", "centre-sud", "est", "hauts-bassins", "nord",
           "plateau-central", "sahel", "sud-ouest")
SCENARIOS = ("bas", "central", "haut")
MODELS = ("last", "trend", "damped")


def spread_integers(total, weights):
    """Plus forts restes ; les ex æquo suivent l'identifiant stable."""
    total_weight = sum(weights.values())
    if not total_weight:
        if total:
            raise ValueError("Ventilation impossible avec des poids nuls.")
        return dict.fromkeys(weights, 0)
    shares = {k: total*v/total_weight for k, v in weights.items()}
    counts = {k: floor(v) for k, v in shares.items()}
    order = sorted(shares, key=lambda k: (counts[k]-shares[k], k))
    for k in order[:total-sum(counts.values())]:
        counts[k] += 1
    return counts


def residual_allocation(total, weights, caps):
    """Distribue le résidu sans dépasser les effectifs régionaux tous statuts connus."""
    if sum(caps.values())<total or total<0:
        raise ValueError("Les effectifs collectés sont incompatibles avec les marges observées.")
    allocated = {}
    remaining = dict(weights)
    while remaining:
        weights_left = remaining if sum(remaining.values()) else {k:caps[k] for k in remaining}
        shares = spread_integers(total,weights_left)
        over = [k for k,v in shares.items() if v>caps[k]]
        if not over:
            allocated.update(shares)
            break
        for k in over:
            allocated[k]=caps[k]
            total-=caps[k]
            remaining.pop(k)
    return allocated


def forecast(series, model, year, damping=.8):
    origin, last = series[-1]
    h = year-origin
    if model == "last" or len(series) < 2:
        return float(last)
    # Régression linéaire sur les années réellement renseignées, ancrée au dernier point.
    xt = mean(t for t, _ in series)
    yt = mean(v for _, v in series)
    slope = sum((t-xt)*(v-yt) for t, v in series)/sum((t-xt)**2 for t, _ in series)
    steps = h if model == "trend" else damping*(1-damping**h)/(1-damping)
    return last + slope*steps


def backtest(series):
    """Origines glissantes, quatre points historiques nécessaires pour tester chaque origine."""
    values = dict(series)
    errors = defaultdict(list)
    for stop in range(4, len(series)):
        train = series[:stop]
        origin = train[-1][0]
        for horizon in (1, 2):
            target = origin+horizon
            if target not in values:
                continue
            for model in MODELS:
                estimate = max(0, round(forecast(train, model, target)))
                errors[model, horizon].append(estimate-values[target])
    scores = []
    all_errors = {}
    for model in MODELS:
        all_errors[model] = []
        for horizon in (1, 2):
            e = errors[model, horizon]
            all_errors[model].extend(e)
            scores.append(dict(model=model, horizon=horizon, n=len(e),
                               mae=round(mean(map(abs, e)), 2) if e else None,
                               bias=round(mean(e), 2) if e else None))
    best = min(MODELS, key=lambda m: mean(map(abs, all_errors[m])) if all_errors[m] else float("inf"))
    return best, scores


def series_for(rows, supplement, p, regions, national):
    """Une région n'utilise aucune marge nationale. Les tableaux de cycles restent distincts."""
    base = p["base_year"]
    cycle = p["cycle"]
    prefix = "PRI" if cycle == "primaire" else "PRE"
    national_public, all_status, stock_rooms = {}, defaultdict(dict), {}
    verified = {k:defaultdict(dict) for k in ("effectifs_publics_regionaux","enseignants_disponibles","salles_utilisables")}
    seen = set()
    for r in rows:
        region, table, year, v = r.get("region"), r.get("table"), r.get("year"), r.get("value")
        if r.get("cycle") != cycle or v is None or not isinstance(year, int) or year > base:
            continue
        if (region in regions and table == "COLLECTE" and r.get("origin") == "observed"
                and r.get("status") == "public" and r.get("sex") == "total" and r.get("indicator") in verified):
            bucket = verified[r["indicator"]][year]
            if region in bucket or int(v) != v or v < 0:
                raise ValueError("Complément collecté dupliqué ou invalide.")
            bucket[region] = int(v)
            continue
        if national and region == "national" and table == prefix+"02" and r.get("status") == "public" and r.get("sex") == "total":
            target, key = national_public, year
        elif region in regions and table == prefix+"01" and r.get("sex") == "total":
            target, key = all_status[year], region
        elif region in regions and year == base and table == "PRE08" and r.get("status") == "public":
            target, key = stock_rooms, region
        else:
            continue
        identity = table, region, year
        if identity in seen:
            raise ValueError("Deux valeurs concurrentes pour une série de planification.")
        seen.add(identity)
        if v < 0 or int(v) != v:
            raise ValueError("Stock ou inscription inadmissible.")
        target[key] = int(v)
    demo, teachers = defaultdict(dict), {}
    for r in supplement:
        region, year = r.get("region"), r.get("year")
        if r.get("table") != "DEMO" or r.get("origin") != "synthetic" or r.get("cycle") != cycle or region not in regions:
            continue
        if r.get("status") != "public" or r.get("sex") != "total" or r.get("value") is None:
            continue
        indicator, v = r["indicator"], r["value"]
        if indicator == "effectifs_publics_simules":
            target, key = demo[year], region
        elif year == base and indicator == "salles_primaires_simulees":
            target, key = stock_rooms, region
        elif year == base and indicator == "enseignants_simules":
            target, key = teachers, region
        else:
            continue
        if key in target or v < 0 or int(v) != v:
            raise ValueError("Complément dupliqué ou invalide.")
        target[key] = int(v)
    regional = {}
    mix = p["regional_mix"]
    for year in range(2016, base+1):
        prop = None
        if national and year in national_public and set(all_status[year]) == set(regions):
            prop = spread_integers(national_public[year], all_status[year])
        if mix == "proportional" and prop is not None:
            regional[year] = prop
        elif mix == "demo" and set(demo[year]) == set(regions):
            if p["mix_weight"] != 1:
                if prop is None:
                    raise ValueError("La variation du mélange exige les marges du périmètre national autorisé.")
                w = p["mix_weight"]
                regional[year] = spread_integers(national_public[year], {k: w*demo[year][k]+(1-w)*prop[k] for k in regions})
            else:
                regional[year] = demo[year]
            if national and year in national_public and sum(regional[year].values()) != national_public[year]:
                raise ValueError("Les effectifs simulés ne retrouvent pas la marge publique de la version source.")
    # Un croisement validé remplace la valeur de démonstration. Si une marge nationale
    # existe, seule sa part résiduelle est répartie sur les régions encore simulées.
    for year,known in verified["effectifs_publics_regionaux"].items():
        if any(v>all_status.get(year,{}).get(k,v) for k,v in known.items()):
            raise ValueError("Un effectif public collecté dépasse l’effectif régional tous statuts.")
        remaining=set(regions)-set(known)
        if not remaining:
            if national and year in national_public and sum(known.values()) != national_public[year]:
                raise ValueError("La somme des effectifs collectés contredit la marge publique nationale.")
            regional[year]=dict(known)
            if national:
                national_public.setdefault(year,sum(known.values()))
        elif year in regional:
            if national and year in national_public:
                residual=national_public[year]-sum(known.values())
                if residual < 0:
                    raise ValueError("La collecte régionale dépasse la marge nationale.")
                weights={k:regional[year][k] for k in sorted(remaining)}
                caps={k:all_status.get(year,{}).get(k,residual) for k in remaining}
                regional[year]=dict(known,**residual_allocation(residual,weights,caps))
            else:
                regional[year].update(known)
    if cycle == "prescolaire" and p["preschool_staff_ratio"] and base in regional:
        teachers = {k: round(v/p["preschool_staff_ratio"]) for k,v in regional[base].items()}
    stock_rooms.update(verified["salles_utilisables"].get(base,{}))
    teachers.update(verified["enseignants_disponibles"].get(base,{}))
    totals = national_public if national else {y: sum(vals.values()) for y, vals in regional.items()}
    alternative = None
    if national and base in national_public and set(all_status[base]) == set(regions):
        alternative = spread_integers(national_public[base], all_status[base])
    return sorted(totals.items()), regional, stock_rooms, teachers, alternative, verified


def project(series, regional, p):
    base = p["base_year"]
    best, validation = backtest(series)
    selected = best if p["model"] == "auto" else p["model"]
    ml = None
    if selected in ("ml_auto", *quantile.DAMPING):
        selected, scores, ml = quantile.evaluate(series, selected)
        validation += scores
    values, detail, constrained = [], {}, []
    if not series or series[-1][0] != base or (ml and ml["fitted"] is None):
        return selected, validation, values, detail, constrained, ml
    for year in range(base+1, END+1):
        if ml:
            raw = quantile.predict(series[-1][1], year-base, ml["fitted"], ml["phi"])
        else:
            center = forecast(series, selected, year)
            width = p["scenario_spread"] * (year-base)/(END-base)
            raw = dict(bas=center*(1-width), central=center, haut=center*(1+width))
        if min(raw.values()) < 0:
            constrained.append(year)
        totals = {key: max(0, round(v)) for key, v in raw.items()}
        values.append(dict(year=year, **totals))
        if base in regional:
            weights = regional[base]
            if sum(weights.values()) or not any(totals.values()):
                allocated = {key:spread_integers(total, weights) for key,total in totals.items()}
                # Un arrondi indépendant aux plus forts restes peut inverser deux scénarios proches.
                central = allocated["central"]
                if ml and any(allocated["bas"][k] > central[k] for k in weights):
                    allocated["bas"] = residual_allocation(totals["bas"], weights, central)
                if ml and any(allocated["haut"][k] < central[k] for k in weights):
                    residual = {k:max(0, totals["haut"]*v - central[k]*sum(weights.values()))
                                for k, v in weights.items()}
                    increment = spread_integers(totals["haut"]-totals["central"], residual)
                    allocated["haut"] = {k:central[k]+increment[k] for k in weights}
                detail[year] = allocated
    return selected, validation, values, detail, constrained, ml
