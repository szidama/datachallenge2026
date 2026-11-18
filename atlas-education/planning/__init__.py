"""API de planification, sans état ni dépendance externe."""
from math import floor, isfinite

from .forecast import BASE, END, REGIONS, SCENARIOS, project, series_for
from .quantile import DAMPING
from .finance import PRICES, schedule
from . import provinces
from .resources import OPTIONS, simulate, unavailable

VERSION = "planning-2.1"


def defaults(cycle="primaire"):
    if cycle not in ("primaire","prescolaire"):
        raise ValueError("Cycle éducatif inconnu.")
    primary = cycle=="primaire"
    return dict(cycle=cycle, base_year=BASE, year=2050, programme_start=BASE+1, scenario="central", model="ml_auto", regional_mix="demo" if primary else "none",
                class_size=45 if primary else 30, mix_weight=1.0, scenario_spread=None,
                room_availability=.95 if primary else .90, teacher_availability=.95, match_factor=.95,
                room_retirement=.005,room_disruption=.005,staff_departure=.015,
                annual_rooms=20 if primary else 5, annual_teachers=25 if primary else 6,
                annual_transfers=10 if primary else 2, annual_rehab=5 if primary else 2,
                training_delay=1, construction_delay=2, rehab_delay=1, preschool_staff_ratio=None,
                room_cost=None,rehab_cost=None,salary_cost=None,maintenance_cost=None,
                investment_budget=None,operating_budget=None,price_year=2025)


def parameters(input_params, allow_collected=False):
    if not isinstance(input_params,dict):
        raise ValueError("Les hypothèses doivent former un objet.")
    p=defaults(input_params.get("cycle","primaire"))
    if set(input_params)-set(p):
        raise ValueError("Paramètre de prospective inconnu.")
    p.update(input_params)
    for key,choices in (("scenario",SCENARIOS),("model",("ml_auto",*DAMPING,"auto","last","trend","damped")),
                        ("regional_mix",("none","demo","proportional","annuaire"))):
        if p[key] not in choices:
            raise ValueError("Option inconnue pour "+key)
    if p["regional_mix"] == "annuaire" and (p["cycle"] != "primaire" or p["base_year"] != BASE):
        raise ValueError("Le référentiel provincial couvre le primaire public au millésime 2024–2025.")
    rules={"programme_start":(BASE+1,END,int),"base_year":(BASE,END-1,int),"year":(BASE+1,END,int),"class_size":(1,120,int),"price_year":(2000,END,int),
           **{k:(0,2000,int) for k in ("annual_rooms","annual_teachers","annual_transfers","annual_rehab")},
           **{k:(1,10,int) for k in ("training_delay","construction_delay","rehab_delay")},
           **{k:(0,1,float) for k in ("mix_weight","room_availability","teacher_availability","room_retirement",
                    "staff_departure","room_disruption","scenario_spread")},"match_factor":(.01,1,float),
           "preschool_staff_ratio":(1,150,float),
           **{k:(0,10**15,int) for k in ("room_cost","rehab_cost","salary_cost","maintenance_cost","investment_budget","operating_budget")}}
    if p["model"] in ("ml_auto", *DAMPING):
        if p["scenario_spread"] is not None:
            raise ValueError("La régression quantile apprend les écarts sur la série. Retirez le pourcentage de scénario fixe.")
    elif p["scenario_spread"] is None:
        p["scenario_spread"] = .20
    optional={"scenario_spread","preschool_staff_ratio","room_cost","rehab_cost","salary_cost","maintenance_cost","investment_budget","operating_budget"}
    for k,(low,high,kind) in rules.items():
        v=p[k]
        if v is None and k in optional:
            continue
        if type(v) not in (int,float) or (kind is int and type(v) is not int) or not low<=v<=high or not isfinite(v):
            raise ValueError(f"Valeur invalide pour {k} (attendu de {low} à {high}).")
    if "programme_start" not in input_params:
        p["programme_start"]=p["base_year"]+1
    if p["programme_start"] <= p["base_year"]:
        raise ValueError("La programmation doit suivre le millésime de base.")
    if p["year"] <= p["base_year"]:
        raise ValueError("Le jalon doit suivre le millésime de base.")
    if not allow_collected and p["investment_budget"] is not None and (p["room_cost"] is None or p["rehab_cost"] is None):
        raise ValueError("Une enveloppe d’investissement exige les coûts de construction et de réhabilitation.")
    if not allow_collected and p["operating_budget"] is not None and (p["salary_cost"] is None or p["maintenance_cost"] is None):
        raise ValueError("Une enveloppe de fonctionnement exige les coûts annuels de salaire et de maintenance.")
    return p


def _rows(payload):
    return payload.get("observations",[]) if isinstance(payload,dict) else payload


def lineage(real, demo, p, scope, national):
    """Références lisibles des séries et stocks utilisés, limitées au périmètre du calcul."""
    prefix="PRI" if p["cycle"]=="primaire" else "PRE"
    references=[]
    for r in real+demo:
        if r.get("region") not in scope and not (national and r.get("region")=="national"):
            continue
        if r.get("cycle")!=p["cycle"] or r.get("value") is None or r["year"]>p["base_year"]:
            continue
        table=r.get("table")
        if table==prefix+"02":
            use=national and r.get("region")=="national" and r.get("sex")=="total" and r.get("status")=="public"
        elif table==prefix+"01":
            use=national and r.get("sex")=="total" and r.get("region") in scope
        elif table=="PRE08":
            use=r["year"]==p["base_year"] and r.get("status")=="public" and r.get("region") in scope
        elif table=="DEMO":
            use=r.get("sex")=="total" and ((p["regional_mix"]=="demo" and r["indicator"]=="effectifs_publics_simules")
                or (r["year"]==p["base_year"] and r["indicator"] in ("salles_primaires_simulees","enseignants_simules")))
        elif table=="COLLECTE":
            use=r.get("indicator")=="effectifs_publics_regionaux" or (r["year"]==p["base_year"] and
                r.get("indicator") in ("salles_utilisables","enseignants_disponibles"))
        else:
            continue
        if use:
            fields=("id","table","region","year","indicator","origin","source","version","sheet","cell","seed","generator_version")
            references.append({k:r[k] for k in fields if k in r})
    return references


def sensitivity(detail,p,fixed,alternative,base):
    """Stress du plan combiné déjà livré à l'année choisie, sans arbitrer à nouveau."""
    result=[]
    for sc in SCENARIOS:
        demand=detail[p["year"]][sc]
        for size in sorted({max(1,p["class_size"]-5),p["class_size"],p["class_size"]+5}):
            q=max(1,floor(size*p["match_factor"]))
            missing={r["region"]:max(0,demand[r["region"]]-q*min(r["rooms"],r["teachers"])) for r in fixed}
            ranks=sorted((k for k,v in missing.items() if v>0), key=lambda k:(-missing[k],k))[:3]
            count=sum(demand.values())
            result.append(dict(kind="capacite",scenario=sc,class_size=size,unserved=sum(missing.values()),
                               coverage=(1-sum(missing.values())/count) if count else None,priorities=ranks))
    if alternative and base:
        result.append(dict(kind="ventilation",year=p["base_year"],
                           label="Écart du croisement retenu au prorata intégral des inscriptions tous statuts",
                           differences=[dict(region=k,current=v,proportional=alternative[k],difference=v-alternative[k]) for k,v in base.items()]))
    return result


def run_plan(observations, params, synthetic=(), regions=None, mode="combined"):
    """regions=None est réservé à une habilitation nationale explicite ; le serveur gère les droits."""
    if mode not in ("projection","combined"):
        raise ValueError("Mode de calcul inconnu.")
    p=parameters(params,allow_collected=True)
    base=p["base_year"]
    national=regions is None
    if not national and (not isinstance(regions,(tuple,list,set,frozenset)) or not regions or not set(regions)<=set(REGIONS)):
        raise ValueError("Périmètre régional vide ou inconnu.")
    scope=tuple(k for k in REGIONS if national or k in regions)
    rows=list(_rows(observations))
    extra=list(_rows(synthetic))
    # L'import peut regrouper les deux origines dans la version validée.
    demo=[r for r in rows+extra if r.get("table")=="DEMO"]
    real=[r for r in rows if r.get("table")!="DEMO"]+[r for r in extra if r.get("table")=="COLLECTE"]
    provincial = None
    if p["regional_mix"] == "annuaire":
        province_rows, margins, official_sources = provinces.inventory(real, scope)
        demo = []
    series,regional,rooms,teachers,alternate,verified=series_for(real,demo,p,scope,national)
    selected,metrics,totals,detail,constrained,ml=project(series,regional,p)
    if p["regional_mix"] == "annuaire":
        rooms = {**margins["rooms"], **rooms}
        teachers = {**margins["teachers"], **teachers}
        detail, provincial = provinces.allocate(province_rows, totals, p, official_sources)
    known_public=verified["effectifs_publics_regionaux"]
    def regional_origin(year):
        return "observed" if set(scope)==set(known_public.get(year,{})) else "estimate"
    info=dict(code_version=VERSION,base_year=base,unit="élèves",cycle=p["cycle"],regions=list(scope),
              scope="national" if national else "régional",model=selected,status="simulation exploratoire",
              reference="périmètre des 13 régions historiques du classeur",damping=.8,
              assumption_source="Hypothèses de démonstration modifiables",currency="XOF",
              price_year=p["price_year"],discounting="aucune actualisation",data_origins={
                  "enrolment": "observed" if national else regional_origin(base),
                  "regional_enrolment":regional_origin(base) if base in regional else "missing",
                  "regional_public_observed":sorted(known_public.get(base,{})),
                  "usable_rooms_observed":sorted(verified["salles_utilisables"].get(base,{})),
                  "available_teachers_observed":sorted(verified["enseignants_disponibles"].get(base,{}))},
              method="Projection des inscriptions publiques ; scénarios d’évolution relative de la demande adressée au public.",
              scenario_definition="Écart linéaire de 0 au dernier millésime à ±scenario_spread en 2050 ; fourchette conditionnelle sans probabilité.",
              demand_basis="Les inscriptions servent de point de départ. La population scolarisable par âge reste à collecter.",
              floor_applied_years=constrained,solver="Heuristique entière annuelle à gains marginaux ; faisabilité sous les hypothèses saisies.",
              optimality_gap=None,time_limit_seconds=None,
              pooling="Groupes théoriques par région ; min(salles utilisables, enseignants disponibles) × max(1, plancher(taille × facteur de correspondance)).",
              financial_basis="Investissement cumulé jusqu’au jalon ; fonctionnement total de l’année. Budgets additionnels contrôlés à la livraison, fonctionnement réservé chaque année pour les moyens créés ou restaurés.",
              limits="Mutualisation régionale théorique. Implantations scolaires, qualifications individuelles, accessibilité et effets causaux restent à documenter.")
    if ml:
        info.update(learning=ml, damping=ml["phi"],
                    method="Régression quantile des variations d’inscriptions sur l’horizon amorti. Une pente est apprise par scénario.",
                    scenario_definition="Basse, centrale et haute utilisent les quantiles 20 %, 50 % et 80 % des variations conditionnelles. Leur prolongement à 2050 est exploratoire.")
    if isinstance(observations,dict):
        metadata=observations.get("metadata",{})
        info["source_version"]=metadata.get("sha256") or metadata.get("version")
    prerequisites=["Géolocalisation des établissements et réseau de déplacement requis pour l’accessibilité.",
                   "Population par âge et hypothèses de parcours requises pour une projection démographique."]
    if provincial:
        info["demand_basis"] = "Série scolaire du périmètre et poids provinciaux des inscriptions de 2025 ajustés par les 6–11 ans de l’INSD jusqu’en 2035. Les poids relatifs de 2035 sont conservés jusqu’en 2050."
        info["data_origins"]["inventory"] = "DGESS 2024–2025, primaire public, tableau I.1"
        prerequisites[1] = "Les projections INSD des 6–11 ans s’arrêtent en 2035. Les poids territoriaux ultérieurs sont une hypothèse."
    if not series or series[-1][0] != base:
        prerequisites.append(f"Série d’inscriptions publiques clôturée en {base-1}/{base} requise dans le périmètre autorisé.")
    if ml and ml["fitted"] is None:
        prerequisites.append("Apprentissage insuffisant. Il faut au moins trois années de départ distinctes suivies d’une observation un ou deux ans après.")
    if ml and ml["fitted"] and all(v is None for v in ml["selection_scores"].values()):
        prerequisites.append("Aucune origine testable. L’amortissement automatique par défaut est de 0,80. La performance historique reste inconnue.")
    if len(detail) != END-base:
        detail = {}
    if not detail:
        prerequisites.append("Croisement public/région requis. En habilitation nationale, une ventilation proportionnelle peut être essayée explicitement.")
    missing=[]
    if set(rooms)!=set(scope):
        missing.append("salles initiales")
    if set(teachers)!=set(scope):
        missing.append("enseignants disponibles")
    if missing:
        prerequisites.append("Stocks régionaux requis : "+", ".join(missing)+".")
    finances, financial_sources, ignored_prices = schedule(real,p,scope)
    info["financial_sources"]=financial_sources
    info["financial_basis"] += " Les tarifs collectés comparables priment sur les hypothèses. Les enveloppes territoriales s’ajoutent comme contraintes locales pour leur seul exercice."
    if ignored_prices:
        prerequisites.append(f"{ignored_prices} montant(s) collecté(s) écarté(s) car l’année de prix diffère de celle du scénario.")
    if any(values[k] is None for values in finances[p["year"]].values() for k in PRICES):
        prerequisites.append("Coûts unitaires à renseigner pour les dépenses correspondantes.")
    history=[dict(year=y,value=v,origin="observed" if national else regional_origin(y)) for y,v in series]
    regional_series=[dict(region=k,year=y,**{sc:values[sc][k] for sc in SCENARIOS}) for y,values in detail.items() for k in scope]
    result=dict(meta=info,parameters=p,historical=history,validation=metrics,trajectories=totals,
                regional_trajectories=regional_series,comparison=[],regional=[],programme=[],sensitivity=[],
                annual_options=[],prerequisites=prerequisites,source_references=lineage(real,demo,p,scope,national))
    if provincial:
        result["provincial"] = provincial
    if mode=="projection":
        return result
    demand=next((v[p["scenario"]] for v in totals if v["year"]==p["year"]),None)
    if missing or not detail:
        reason="Stocks ou effectifs publics régionaux complémentaires requis."
        result["comparison"]=[unavailable(k,p["year"],reason,demand) for k in OPTIONS]
    else:
        comparison,by_region,programme,annual=simulate(rooms,teachers,detail,p,verified,finances)
        result.update(comparison=comparison,regional=by_region,programme=programme,annual_options=annual)
        fixed=[r for r in by_region if r["option"]=="combine"]
        result["sensitivity"]=sensitivity(detail,p,fixed,alternate,regional.get(base))
        ref=comparison[0]["served"]
        for r in comparison:
            r["gain_vs_reference"]=r["served"]-ref
    result["comparison"].append(unavailable("nouvel_etablissement",p["year"],
            "Terrains, implantations candidates, coûts de site et demandes localisées requis.",demand))
    return result
