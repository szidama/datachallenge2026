"""Allocation annuelle entière, uniquement dans le périmètre autorisé et sous hypothèses."""
from math import ceil, floor

from .finance import Budget, money, total_cost
from .forecast import spread_integers


LABELS = {
    "reference":"Moyens de référence", "rehabilitation":"Réhabilitations et réouvertures",
    "extension":"Salles supplémentaires", "recrutement":"Recrutements et affectations",
    "redeploiement":"Redéploiements", "combine":"Intervention combinée",
    "nouvel_etablissement":"Nouveaux établissements",
}
OPTIONS = tuple(k for k in LABELS if k != "nouvel_etablissement")
COUNTS = ("new_rooms", "new_teachers", "transfers", "rehabilitated")


def initial(rooms, teachers, p, verified):
    states = {}
    for k, stock in rooms.items():
        usable = stock if k in verified["salles_utilisables"].get(p["base_year"],{}) else floor(stock*p["room_availability"])
        active = teachers[k] if k in verified["enseignants_disponibles"].get(p["base_year"],{}) else floor(teachers[k]*p["teacher_availability"])
        states[k] = dict(rooms=usable, closed=stock-usable, staff=active, absent=teachers[k]-active, payroll={k:active})
    return states


def age(row,p):
    retired = floor(row["rooms"]*p["room_retirement"])
    retired_closed = floor(row["closed"]*p["room_retirement"])
    loss = floor((row["rooms"]-retired)*p["room_disruption"])
    exits = floor(row["staff"]*p["staff_departure"])
    exits_absent = floor(row["absent"]*p["staff_departure"])
    row["rooms"] -= retired+loss
    row["closed"] += loss-retired_closed
    if exits:
        departures=spread_integers(exits,row["payroll"])
        for origin,count in departures.items():
            row["payroll"][origin]-=count
    row["staff"] -= exits
    row["absent"] -= exits_absent
    return dict(retired_rooms=retired+retired_closed, newly_closed=loss, staff_exits=exits+exits_absent)


def plan_year(states, demands, p, option, year, budget, commitments):
    """Une action ouvre un groupe. Départs autorisés uniquement depuis les postes excédentaires."""
    flows = {k:dict(**age(row,p),**dict.fromkeys(COUNTS,0),outgoing=0) for k,row in states.items()}
    annual = dict.fromkeys(COUNTS,0)
    q = max(1, floor(p["class_size"]*p["match_factor"]))
    elapsed = year-p["base_year"]
    limits = dict(new_rooms=p["annual_rooms"] if elapsed>=p["construction_delay"] else 0,
                  new_teachers=p["annual_teachers"] if elapsed>=p["training_delay"] else 0,
                  rehabilitated=p["annual_rehab"] if elapsed>=p["rehab_delay"] else 0,
                  transfers=p["annual_transfers"])
    allowed = {
        "new_rooms": option in {"combine","extension"},
        "new_teachers": option in {"combine","recrutement"},
        "rehabilitated": option in {"combine","rehabilitation"},
        "transfers": option in {"combine","redeploiement"},
    }
    while any(allowed[k] and annual[k] < limits[k] for k in COUNTS):
        available = {k for k in COUNTS if allowed[k] and annual[k]<limits[k]}
        donor = None
        if "transfers" in available:
            def surplus(k):
                r = states[k]
                return r["staff"]-min(r["rooms"],ceil(demands[k]/q))
            donor = max(states, key=surplus)
            if surplus(donor)<=0:
                donor = None
        best = None
        for k,row in states.items():
            groups = min(row["staff"],row["rooms"])
            gap = demands[k]-q*groups
            if gap <= 0:
                continue
            room_actions = [None]
            if row["rooms"]==groups:
                room_actions = []
                if row["closed"] and "rehabilitated" in available:
                    room_actions.append("rehabilitated")
                if "new_rooms" in available:
                    room_actions.append("new_rooms")
            staff_action = None
            if row["staff"]==groups:
                if donor and donor!=k:
                    staff_action = "transfers"
                elif "new_teachers" in available:
                    staff_action = "new_teachers"
                else:
                    continue
            for room_action in room_actions:
                actions = tuple(a for a in (room_action,staff_action) if a)
                quote=budget.quote(year,k,room_action,staff_action)
                if quote is None:
                    continue
                capex,debits=quote
                # Ordre lexicographique explicable, puis ordre stable du référentiel.
                score=(min(gap,q),gap/demands[k],-len(actions),-(capex or 0),room_action=="rehabilitated")
                if best is None or score>best[0]:
                    best=(score,k,actions,debits)
        if best is None:
            break
        _,k,actions,debits=best
        budget.commit(debits)
        for a in actions:
            annual[a]+=1
            flows[k][a]+=1
            commitments[k][a]+=1
            if a in {"new_rooms","rehabilitated"}:
                states[k]["rooms"]+=1
                if a=="rehabilitated":
                    states[k]["closed"]-=1
            else:
                states[k]["staff"]+=1
                if a=="transfers":
                    states[donor]["staff"]-=1
                    peers=states[donor]["payroll"]
                    origin=max(peers,key=peers.get)
                    peers[origin]-=1
                    flows[donor]["outgoing"]+=1
                else:
                    origin=k
                payroll=states[k]["payroll"]
                payroll[origin]=payroll.get(origin,0)+1
    results=[]
    for k,row in states.items():
        capacity=q*min(row["rooms"],row["staff"])
        demand=demands[k]
        served=min(capacity,demand)
        required=ceil(demand/q)
        prices=budget.schedule[year][k]
        investment=total_cost(money(flows[k]["new_rooms"],prices["room_cost"]),money(flows[k]["rehabilitated"],prices["rehab_cost"]))
        salary=total_cost(money(row["absent"],prices["salary_cost"]),
                          *(money(v,budget.schedule[year][origin]["salary_cost"]) for origin,v in row["payroll"].items()))
        operating=total_cost(salary,money(row["rooms"],prices["maintenance_cost"]))
        cumulative=commitments[k]
        reserved=total_cost(money(cumulative["new_teachers"],prices["salary_cost"]),
                            money(cumulative["new_rooms"]+cumulative["rehabilitated"],prices["maintenance_cost"]))
        results.append(dict(annual_investment=investment,operating=operating,additional_operating_reserved=reserved,region=k,year=year,option=option,demand=demand,served=served,unserved=demand-served,
                            capacity=capacity,coverage=served/demand if demand else None,rooms=row["rooms"],
                            inventoried_rooms=row["rooms"]+row["closed"],unavailable_rooms=row["closed"],
                            teachers=row["staff"],teacher_headcount=row["staff"]+row["absent"],
                            rooms_needed=max(0,required-row["rooms"]),teachers_needed=max(0,required-row["staff"]),
                            pupils_per_room=served/row["rooms"] if row["rooms"] else None,
                            pupils_per_teacher=served/row["staff"] if row["staff"] else None,**flows[k]))
    return results, annual


def aggregate(rows, counts, annual, invested):
    fields=("demand","served","unserved","capacity","rooms","teachers","rooms_needed","teachers_needed",
            "teacher_headcount","inventoried_rooms","retired_rooms","newly_closed","staff_exits")
    stats={k:sum(r[k] for r in rows) for k in fields}
    rates=[r["coverage"] for r in rows if r["coverage"] is not None]
    year_investment=total_cost(*(r["annual_investment"] for r in rows))
    investment=total_cost(invested,year_investment)
    operating=total_cost(*(r["operating"] for r in rows))
    reserved=total_cost(*(r["additional_operating_reserved"] for r in rows))
    return dict(year=rows[0]["year"],option=rows[0]["option"],label=LABELS[rows[0]["option"]],available=True,
                reason=None,**stats,**counts,annual=dict(annual),investment=investment,annual_investment=year_investment,
                operating=operating,additional_operating_reserved=reserved,
                coverage=stats["served"]/stats["demand"] if stats["demand"] else None,
                equity_gap=max(rates)-min(rates) if rates else None,solver_status="faisable")


def simulate(rooms,teachers,detail,p,verified,finances):
    comparison,regional,programme,annual_options=[],[],[],[]
    # Programme glissant des cinq années à partir de l'année consultée, jusqu'à l'horizon.
    first=p["programme_start"]
    end=min(2050,first+4)
    last=max(end,p["year"])
    for option in OPTIONS:
        states=initial(rooms,teachers,p,verified)
        counts=dict.fromkeys(COUNTS,0)
        commitments={k:dict.fromkeys(COUNTS,0) for k in states}
        budget=Budget(finances,p)
        invested=0
        for year in range(p["base_year"]+1,last+1):
            rows,annual=plan_year(states,detail[year][p["scenario"]],p,option,year,budget,commitments)
            counts={k:counts[k]+annual[k] for k in COUNTS}
            summary=aggregate(rows,counts,annual,invested)
            invested=summary["investment"]
            annual_options.append(summary)
            if year==p["year"]:
                comparison.append(summary)
                regional.extend(rows)
            if first<=year<=end:
                programme.append(dict(**summary,decision_status="orientation indicative"))
    return comparison,regional,programme,annual_options


def unavailable(option,year,reason,demand):
    fields=dict.fromkeys(("served","unserved","coverage","new_rooms","new_teachers","transfers","rehabilitated",
                          "investment","operating","equity_gap","rooms_needed","teachers_needed"))
    return dict(option=option,year=year,label=LABELS[option],available=False,reason=reason,demand=demand,
                solver_status="prérequis manquants",**fields)
