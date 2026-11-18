"""Prix constants, budgets de territoire et réservation des engagements récurrents."""
from collections import defaultdict
from math import isfinite

from .forecast import END

METRICS = {
    "cout_salle":("room_cost","FCFA/salle"),
    "cout_rehabilitation":("rehab_cost","FCFA/salle"),
    "cout_enseignant":("salary_cost","FCFA/poste/an"),
    "cout_maintenance":("maintenance_cost","FCFA/salle/an"),
    "budget_investissement":("investment_budget","FCFA"),
    "budget_fonctionnement":("operating_budget","FCFA")
}
PRICES = ("room_cost","rehab_cost","salary_cost","maintenance_cost")


def money(count, price):
    return 0 if count==0 else (None if price is None else count*price)


def total_cost(*terms):
    return None if any(v is None for v in terms) else sum(terms)


def schedule(rows,p,regions):
    """Les tarifs collectés à prix comparables prévalent, sans agréger les coûts unitaires."""
    actual=defaultdict(dict)
    ignored=0
    provenance=[]
    for r in rows:
        if (r.get("table")!="COLLECTE" or r.get("origin")!="observed" or r.get("region") not in regions
            or r.get("cycle")!=p["cycle"] or r.get("indicator") not in METRICS):
            continue
        if str(r.get("price_year"))!=str(p["price_year"]):
            ignored+=1
            continue
        key,unit=METRICS[r["indicator"]]
        value=r.get("value")
        if r.get("unit")!=unit or type(value) not in (float,int) or not isfinite(value) or value<0:
            raise ValueError("Montant ou unité de la collecte financière invalide.")
        timeline=actual[r["region"],key]
        if r["year"] in timeline:
            raise ValueError("Tarifs ou budgets collectés concurrents dans le même périmètre.")
        timeline[r["year"]]=value
        provenance.append({k:r.get(k) for k in ("region","indicator","year","value","unit","price_year","source","version","cell")})
    grid={}
    for y in range(p["base_year"]+1,END+1):
        grid[y]={}
        for reg in regions:
            amounts={}
            for key in PRICES:
                series=actual[reg,key]
                latest=max((t for t in series if t<=y),default=None)
                amounts[key]=series[latest] if latest is not None else p[key]
            for key in ("investment_budget","operating_budget"):
                amounts[key]=actual[reg,key].get(y)
            grid[y][reg]=amounts
    return grid,provenance,ignored


class Budget:
    """Portefeuille d'une option. Les réservations restent sur le territoire d'engagement."""
    def __init__(self,schedule,p):
        self.schedule=schedule
        self.capital={}
        self.recurrent={}
        self.active_years=[]
        for y,regions in schedule.items():
            self.capital[y]={k:v["investment_budget"] for k,v in regions.items() if v["investment_budget"] is not None}
            self.recurrent[y]={k:v["operating_budget"] for k,v in regions.items() if v["operating_budget"] is not None}
            for ledger,key in ((self.capital,"investment_budget"),(self.recurrent,"operating_budget")):
                if p[key] is not None:
                    ledger[y]["*"]=p[key]
            if self.recurrent[y]:
                self.active_years.append(y)

    def quote(self,year,region,room,staff):
        prices=self.schedule[year][region]
        capital=prices["room_cost"] if room=="new_rooms" else prices["rehab_cost"] if room else 0
        debits=[]
        def debit(accounts,amount):
            for key in (region,"*"):
                if key in accounts:
                    if amount is None or amount>accounts[key]:
                        return False
                    debits.append((accounts,key,amount))
            return True
        if not debit(self.capital[year],capital):
            return None
        if room or staff=="new_teachers":
            for y in self.active_years:
                if y<year:
                    continue
                prices=self.schedule[y][region]
                cost=total_cost(prices["maintenance_cost"] if room else 0,prices["salary_cost"] if staff=="new_teachers" else 0)
                if not debit(self.recurrent[y],cost):
                    return None
        return capital,debits

    @staticmethod
    def commit(debits):
        for accounts,key,amount in debits:
            accounts[key]-=amount
