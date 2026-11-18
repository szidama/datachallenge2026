from functools import lru_cache
import base64
import binascii
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import zipfile

from .storage import Error, audit, check, contains, dump, now, permit, require, scope, textfield, uid

TABLES={"datasets","analyses","publications","decisions"}
from .permissions import READ
PUBLIC_FIELDS={"id","cycle","region","year","sex","status","area","level","indicator","unit","value","state","origin","table","sheet","cell","version","source","method","generator_version","seed","official","price_year"}
FILTERS={"cycle","region","year","sex","status","area","level","indicator","origin","table","state"}
ROOT=Path(__file__).resolve().parents[1]

@lru_cache(maxsize=1)
def code_fingerprint():
    digest=hashlib.sha256()
    for folder in ("server","ingestion","planning"):
        for path in sorted((ROOT/folder).glob("*.py")):
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes())
    digest.update((ROOT/"planning/data/provinces_2025.json").read_bytes())
    return digest.hexdigest()

def item(db,table,identifier):
    if table not in TABLES: raise Error(404,"Ressource inconnue.")
    row=db.execute(f"SELECT * FROM {table} WHERE id=?",(identifier,)).fetchone()
    check(row,404,"Ressource introuvable.")
    return row

def summary(row):
    excluded={"payload","parameters","result"}
    return {k:(json.loads(row[k]) if k=="scope" else row[k]) for k in row.keys() if k not in excluded}

def overlap(a,b):
    return "*" in a or "*" in b or bool(set(a)&set(b))

def readable(u,table,row):
    require(u,*READ[table])
    areas=json.loads(row["scope"])
    if table=="datasets":
        check(overlap(u["scope"],areas),403,"Données hors périmètre.")
    else:
        permit(u,areas)
    if table=="analyses":
        action={"projection":"projection.run","optimization":"optimization.run","exploration":"analysis.run"}[row["kind"]]
        allowed={action,"analysis.read","analysis.validate"}
        if row["state"]=="validated": allowed.update(("decision.record","publication.approve","publication.publish"))
        require(u,*allowed)

def select_rows(rows,regions,query=None):
    # Never include a national margin when the scope is regional, even for all 13 regions.
    query=dict(query or {})
    chart=query.pop("chart",None)
    if chart=="barres":query.pop("region",None)
    if chart=="composition":query.pop("status",None)
    filtered=[r for r in rows if (regions==["*"] or r.get("region") in regions)
              and all(str(r.get(k,""))==str(v) for k,v in query.items() if k in FILTERS and v!="")]
    if chart=="barres":
        return sorted((r for r in filtered if r.get("region") not in ("national",None) and r.get("value") is not None),
                      key=lambda r:-r["value"])
    if chart=="composition":return [r for r in filtered if r.get("status") is not None]
    return filtered

def paginate(rows,query):
    try:
        start=int(query.get("offset",0)); count=int(query.get("limit",100))
    except (TypeError,ValueError):
        raise Error(422,"Pagination invalide.") from None
    check(0<=start and 1<=count<=2000,422,"La limite doit être comprise entre 1 et 2 000.")
    return {"items":rows[start:start+count],"total":len(rows),"offset":start,"limit":count}

def visible_observations(payload,regions,query=None):
    return select_rows(payload["observations"]+payload.get("synthetic",[]),regions,query)

def describe(db,u,table,identifier):
    row=item(db,table,identifier)
    readable(u,table,row)
    result=summary(row)
    if table=="datasets":
        payload=json.loads(row["payload"])
        national=u["scope"]==["*"]
        result.update(catalogue=payload.get("catalogue",{}),
                      anomalies=select_rows(payload["anomalies"],u["scope"]),
                      metadata=payload["metadata"] if national else {"version":row["version"],"scope":u["scope"]},
                      tables=payload.get("tables",[]) if national else [])
        if not national:
            result["scope"]=[v for v in u["scope"] if contains(json.loads(row["scope"]),[v])]
            if result.get("warning"): result["warning"]="Version à réexaminer."
    if table=="analyses":
        result.update(parameters=json.loads(row["parameters"]),result=json.loads(row["result"]))
    if table=="publications":
        result["payload"]=json.loads(row["payload"])
    if table in RULES:result.update(workflow_info(db,u,table,row))
    return result

def list_records(db,u,table,query):
    require(u,*READ[table])
    out=[]
    columns={"datasets":"id,title,version,author,scope,state,created,previous,warning",
             "analyses":"id,title,version,author,scope,state,created,dataset_id,kind,warning",
             "publications":"id,title,version,author,scope,state,created,dataset_id,analysis_id,kind,reviewer,approver,replaces,warning",
             "decisions":"*"}[table]
    for row in db.execute(f"SELECT {columns} FROM {table} ORDER BY created DESC,rowid DESC"):
        areas=json.loads(row["scope"])
        try:
            readable(u,table,row)
        except Error as exc:
            if exc.status==403: continue
            raise
        if (table=="datasets" and overlap(u["scope"],areas)) or contains(u["scope"],areas):
            obj=summary(row)
            if table=="datasets" and not contains(u["scope"],areas):
                obj["scope"]=[v for v in u["scope"] if contains(areas,[v])]
                if obj.get("warning"):obj["warning"]="Version à réexaminer."
            if table in RULES and query.get("workflow")=="1":obj.update(workflow_info(db,u,table,row))
            out.append(obj)
    return paginate(out,query)

def decode_file(data):
    name=textfield(data.get("filename"),"Nom de fichier",180)
    check(name==Path(name).name and name.lower().endswith(".xlsx"),422,"Un classeur .xlsx est requis.")
    content=data.get("content")
    check(isinstance(content,str) and len(content)<=14*1024**2,413,"Classeur trop volumineux.")
    try:
        raw=base64.b64decode(content,validate=True)
    except (ValueError,binascii.Error):
        raise Error(422,"Encodage du classeur invalide.") from None
    check(0<len(raw)<=10*1024**2,413,"Classeur vide ou trop volumineux.")
    return name,raw

def ingest(name,raw,demo=None):
    from ingestion import import_workbook, import_demo
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries=z.infolist()
            check(len(entries)<=2000 and sum(v.file_size for v in entries)<=64*1024**2,422,"Classeur hors limites.")
            check(not any(v.filename.lower().endswith("vbaproject.bin") for v in entries),422,"Classeur à macros refusé.")
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/name;p.write_bytes(raw)
            payload=import_workbook(p)
        if demo is not None:
            d=import_demo(demo,payload)
            payload["synthetic"]=d["observations"]
            payload["demo_metadata"]=d["metadata"]
            if isinstance(payload.get("catalogue"),dict) and isinstance(d.get("catalogue"),dict):
                payload["catalogue"].update(d["catalogue"])
        return payload
    except Error: raise
    except (ValueError,OSError,KeyError,TypeError,zipfile.BadZipFile) as e:
        raise Error(422,"Import refusé : "+str(e)[:400]) from e

def archive(db,name,raw):
    sha=hashlib.sha256(raw).hexdigest()
    db.execute("INSERT OR IGNORE INTO archives VALUES (?,?,?,?)",(sha,name,raw,now()))
    return sha

def save_dataset(db,u,name,raw,payload,title):
    require(u,"data.import");permit(u,["*"])
    sha=archive(db,name,raw)
    demo_sha=payload.get("demo_metadata",{}).get("sha256")
    for row in db.execute("SELECT id,payload FROM datasets WHERE sha=? AND previous IS NULL",(sha,)):
        obj=json.loads(row["payload"])
        if obj.get("demo_metadata",{}).get("sha256")==demo_sha:
            return describe(db,u,"datasets",row["id"])
    did=uid()
    db.execute("INSERT INTO datasets VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (did,textfield(title,"Titre"),1,u["id"],dump(["*"]),"draft",now(),sha,None,dump(payload),None))
    audit(db,u["id"],"data.import",did,["*"])
    return describe(db,u,"datasets",did)

def create_analysis(db,u,data):
    kind=data.get("kind","exploration")
    perms={"exploration":"analysis.run","projection":"projection.run","optimization":"optimization.run"}
    check(kind in perms,422,"Type d’analyse inconnu.");require(u,perms[kind])
    source=item(db,"datasets",data.get("dataset_id"))
    areas=scope(data.get("scope",u["scope"]));permit(u,areas)
    check(contains(json.loads(source["scope"]),areas),403,"Source hors périmètre.")
    check(not source["warning"] and source["state"]!="returned",409,"Cette source nécessite une correction.")
    params=data.get("parameters",{})
    check(isinstance(params,dict) and len(dump(params))<=12000,422,"Paramètres invalides.")
    payload=json.loads(source["payload"])
    obs=select_rows(payload["observations"],areas)
    if kind!="exploration" and any(r.get("table")=="COLLECTE" for r in obs):
        check(source["state"]=="validated",409,"Validez les compléments de collecte avant le calcul.")
    if kind=="exploration":
        filters=params.get("filters",{})
        check(isinstance(filters,dict) and set(filters)<=FILTERS,422,"Filtres inconnus.")
        demonstration=filters.get("table")=="DEMO" or filters.get("origin")=="synthetic" or filters.get("indicator") in {r["indicator"] for r in payload.get("synthetic",[])}
        if demonstration:obs=obs+select_rows(payload.get("synthetic",[]),areas)
        chart=params.get("chart","table")
        chart_query={**filters,"chart":chart}
        if chart in ("barres","composition") and params.get("year"):
            chart_query["year"]=params["year"]
        rows=select_rows(obs,areas,chart_query)
        result={"observations":[{k:v for k,v in r.items() if k in PUBLIC_FIELDS} for r in rows],"filters":filters,"count":len(rows),"chart":params.get("chart","table"),"year":params.get("year"),"origin":"synthetic" if rows and all(r.get("origin")=="synthetic" for r in rows) else "observed"}
    else:
        from planning import run_plan
        try:
            result=run_plan(obs,params,select_rows(payload.get("synthetic",[]),areas),None if areas==["*"] else areas,
                            mode="projection" if kind=="projection" else "combined")
        except (ValueError,TypeError,KeyError) as e:
            raise Error(422,"Paramétrage du calcul : "+str(e)[:250]) from e
    identifier=uid()
    result["execution"]={"id":identifier,"source_version":source["id"],"sha256":source["sha"],"actor":u["id"],"date":now(),"code":code_fingerprint(),"status":"calculated"}
    db.execute("INSERT INTO analyses VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(identifier,textfield(data.get("title"),"Titre"),1,u["id"],dump(areas),"calculated",now(),source["id"],kind,dump(params),dump(result),None))
    audit(db,u["id"],perms[kind],identifier,areas)
    return describe(db,u,"analyses",identifier)

def dependency(db,table,identifier):
    row=db.execute(f"SELECT id,author,state,warning" + (",dataset_id,kind" if table=="analyses" else "") +
                   f" FROM {table} WHERE id=?",(identifier,)).fetchone()
    check(row,404,"Version source introuvable.")
    return row

def dependencies(db,pub):
    source=dependency(db,"datasets",pub["dataset_id"])
    check(source["state"]=="validated" and not source["warning"],409,"Source non validée ou à réexaminer.")
    authors={source["author"]}
    if pub["analysis_id"]:
        analysis=dependency(db,"analyses",pub["analysis_id"])
        check(analysis["dataset_id"]==source["id"] and analysis["state"]=="validated" and not analysis["warning"],409,"Analyse non éligible.")
        authors.add(analysis["author"])
    return authors

def prepare_publication(db,u,data):
    require(u,"publication.publish")
    areas=scope(data.get("scope",u["scope"]));permit(u,areas)
    did=data.get("dataset_id"); aid=data.get("analysis_id") or None
    dependencies(db,{"dataset_id":did,"analysis_id":aid})
    source=item(db,"datasets",did);check(contains(json.loads(source["scope"]),areas),403,"Périmètre non autorisé.")
    p=json.loads(source["payload"])
    fields=lambda r:{k:v for k,v in r.items() if k in PUBLIC_FIELDS}
    selected=select_rows(p["observations"],areas)
    payload={"observations":[fields(r) for r in selected],"catalogue":p.get("catalogue",{}),
             "source":{"id":did,"sha256":source["sha"],"version":source["version"],"name":p["metadata"].get("source")},
             "methodology":textfield(data.get("methodology"),"Méthodologie",8000),"parameters":{}}
    kind="diagnostic"
    if aid:
        a=item(db,"analyses",aid); permit(u,json.loads(a["scope"]))
        check(json.loads(a["scope"])==areas,422,"La diffusion doit reprendre le périmètre exact de l’analyse.")
        result=json.loads(a["result"])
        if "execution" in result: result["execution"].pop("actor",None)
        payload.update(result=result, parameters=json.loads(a["parameters"]));kind=a["kind"]
    replaces=data.get("replaces") or None
    version=1
    if replaces:
        old=item(db,"publications",replaces);permit(u,json.loads(old["scope"]))
        check(old["state"] in ("published","review") and json.loads(old["scope"])==areas,409,"Version à remplacer incompatible.")
        version=old["version"]+1
    identifier=uid()
    db.execute("INSERT INTO publications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(identifier,textfield(data.get("title"),"Titre"),version,u["id"],dump(areas),"prepared",now(),did,aid,kind,dump(payload),replaces,None,None,None))
    audit(db,u["id"],"publication.prepare",identifier,areas)
    return summary(item(db,"publications",identifier))

def invalidate(db,old,reason):
    warning="À réexaminer · "+reason
    db.execute("UPDATE datasets SET warning=? WHERE id=?",(warning,old))
    db.execute("UPDATE analyses SET warning=? WHERE dataset_id=?",(warning,old))
    flag_publications(db,"dataset_id",old,warning)

def flag_publications(db,key,identifier,warning):
    db.execute(f"UPDATE publications SET warning=?,state=CASE WHEN state='published' THEN 'review' ELSE state END WHERE {key}=?",(warning,identifier))

RULES={
    "datasets":{"invalidate":("data.validate",("validated",),"returned"),"submit":("data.edit",("draft",),"submitted"),"validate":("data.validate",("submitted",),"validated"),"return":("data.validate",("submitted",),"returned")},
    "analyses":{"invalidate":("analysis.validate",("validated",),"returned"),"examine":("analysis.validate",("calculated",),"examined"),"validate":("analysis.validate",("examined",),"validated"),"return":("analysis.validate",("calculated","examined"),"returned")},
    "publications":{"verify":("analysis.validate",("prepared",),"verified"),"approve":("publication.approve",("verified",),"authorized"),"publish":("publication.publish",("authorized",),"published"),"withdraw":("publication.withdraw",("published","review"),"withdrawn"),"return":("publication.approve",("verified","prepared"),"returned"),"retain":("publication.approve",("review",),"published")}
}

def check_transition(db,u,table,row,action):
    permit(u,json.loads(row["scope"]))
    check(action in RULES[table],422,"Transition inconnue.")
    permission,allowed,target=RULES[table][action]
    if table=="publications" and action=="return" and row["state"]=="prepared":
        require(u,permission,"analysis.validate")
    else:
        require(u,permission)
    check(row["state"] in allowed,409,"Transition incompatible avec l’état actuel.")
    if action in ("invalidate","validate","return","examine","verify","approve","retain"):
        check(u["id"]!=row["author"],403,"Une autre personne doit contrôler cette production.")
    if action=="submit":
        check(row["author"]==u["id"],403,"Action réservée à l’auteur.")
    if action in ("invalidate","submit","examine","validate","publish","approve","verify"):
        check(not row["warning"],409,"Réexamen requis.")
    if table=="datasets" and action in ("submit","validate"):
        check(not successor(db,table,row["id"]),409,"Une correction existe déjà. Utilisez la version corrigée.")
        ancestors_for_validation(db,row)
    if table=="analyses" and action=="validate":
        dependencies(db,{"dataset_id":row["dataset_id"],"analysis_id":None})
    if table=="publications":
        if action in ("verify","approve","publish"):
            authors=dependencies(db,row)
            if action in ("approve","verify"):
                check(u["id"] not in authors,403,"Contrôle indépendant requis pour les versions sources.")
        if action=="retain":
            authors={dependency(db,"datasets",row["dataset_id"])["author"],row["reviewer"]}
            if row["analysis_id"]:authors.add(dependency(db,"analyses",row["analysis_id"])["author"])
            check(u["id"] not in authors,403,"Décision indépendante requise.")
        if action=="approve":
            check(u["id"]!=row["reviewer"],403,"Autorisation distincte de la vérification.")
        if action=="publish":
            check(u["id"] not in (row["approver"],row["reviewer"]),403,"Publication distincte de l’autorisation.")
            if row["replaces"]:
                old=dependency(db,"publications",row["replaces"])
                check(old["state"] in {"published","review"},409,"La version antérieure a déjà été remplacée ou retirée.")
    return target

def ancestors_for_validation(db,row):
    ancestors=[]
    parent=row["previous"]
    while parent:
        record=db.execute("SELECT state,warning,previous FROM datasets WHERE id=?",(parent,)).fetchone()
        check(not record["warning"],409,"Une autre révision a déjà remplacé la version parente.")
        ancestors.append(parent)
        if record["state"]=="validated" or db.execute(
            "SELECT 1 FROM audit WHERE resource=? AND action='datasets.validate' AND result='ok' LIMIT 1",(parent,)
        ).fetchone():break
        parent=record["previous"]
    return ancestors

def transition(db,u,table,identifier,data):
    row=item(db,table,identifier)
    action=data.get("action")
    target=check_transition(db,u,table,row,action)
    areas=json.loads(row["scope"])
    reason=textfield(data.get("reason"),"Motif",1600)
    if action=="invalidate":
        warning="À réexaminer · "+reason
        if table=="datasets":
            db.execute("UPDATE analyses SET warning=? WHERE dataset_id=?",(warning,identifier))
        flag_publications(db,"dataset_id" if table=="datasets" else "analysis_id",identifier,warning)
    if table=="datasets" and action=="validate":
        for parent in ancestors_for_validation(db,row):
            invalidate(db,parent,reason)
    if table=="publications":
        if action=="verify":
            db.execute("UPDATE publications SET reviewer=? WHERE id=?",(u["id"],identifier))
        if action=="approve":
            db.execute("UPDATE publications SET approver=? WHERE id=?",(u["id"],identifier))
        if action=="publish" and row["replaces"]:
            db.execute("UPDATE publications SET state='replaced' WHERE id=?",(row["replaces"],))
    db.execute(f"UPDATE {table} SET state=? WHERE id=?",(target,identifier))
    audit(db,u["id"],table+"."+action,identifier,areas,reason=reason)
    return summary(item(db,table,identifier))

def successor(db,table,identifier):
    if table=="datasets":
        row=db.execute("SELECT id FROM datasets WHERE previous=? ORDER BY version DESC LIMIT 1",(identifier,)).fetchone()
    else:
        row=db.execute("SELECT child FROM revisions WHERE kind=? AND parent=?",(table,identifier)).fetchone()
    return row[0] if row else None

def revision_allowed(u,table,row):
    if table=="datasets":return "data.edit" in u["permissions"] and not row["warning"]
    if row["state"]!="returned" and not row["warning"]:return False
    if table=="analyses":
        perm={"exploration":"analysis.run","projection":"projection.run","optimization":"optimization.run"}[row["kind"]]
        return perm in u["permissions"]
    return "publication.publish" in u["permissions"] and row["state"] not in ("replaced","withdrawn")

def workflow_info(db,u,table,row):
    info={"actions":[],"can_revise":False}
    if not contains(u["scope"],json.loads(row["scope"])):return info
    for action,(_,states,_) in RULES[table].items():
        if row["state"] not in states:continue
        try:check_transition(db,u,table,row,action)
        except Error:continue
        info["actions"].append(action)
    child=successor(db,table,row["id"])
    info["successor"]=child
    info["can_revise"]=not child and revision_allowed(u,table,row)
    if table!="datasets":
        parent=db.execute("SELECT parent FROM revisions WHERE kind=? AND child=?",(table,row["id"])).fetchone()
        info["previous"]=parent[0] if parent else None
    if row["state"]=="returned":
        note=db.execute("SELECT reason FROM audit WHERE resource=? AND action IN (?,?) AND result='ok' ORDER BY seq DESC LIMIT 1",
                        (row["id"],table+".return",table+".invalidate")).fetchone()
        if note:info["return_reason"]=note[0]
    previous=row["previous"] if table=="datasets" else info.get("previous")
    if previous:
        action="data.revise" if table=="datasets" else table+".revise"
        note=db.execute("SELECT reason FROM audit WHERE resource=? AND action=? AND result='ok' ORDER BY seq DESC LIMIT 1",
                        (row["id"],action)).fetchone()
        if note:info["correction_reason"]=note[0]
    return info

def revise_result(db,u,table,identifier,data):
    row=item(db,table,identifier)
    readable(u,table,row)
    areas=json.loads(row["scope"])
    if table=="analyses":
        require(u,{"exploration":"analysis.run","projection":"projection.run","optimization":"optimization.run"}[row["kind"]])
    else:require(u,"publication.publish")
    check(revision_allowed(u,table,row),409,"Cette version n’est pas à corriger.")
    check(not successor(db,table,identifier),409,"Une correction existe déjà pour cette version.")
    reason=textfield(data.get("reason"),"Motif de correction",1600)
    request={**data,"scope":areas,"dataset_id":data.get("dataset_id",row["dataset_id"])}
    if table=="analyses":
        request.update(kind=row["kind"],parameters=data.get("parameters",json.loads(row["parameters"])))
        child=create_analysis(db,u,request)
    else:
        request["analysis_id"]=data.get("analysis_id",row["analysis_id"])
        if row["analysis_id"]:
            check(request["analysis_id"],422,"Sélectionnez le résultat validé à diffuser.")
            analysis=dependency(db,"analyses",request["analysis_id"])
            check(analysis["kind"]==row["kind"],422,"Conservez le type de résultat à diffuser.")
        request["replaces"]=identifier if row["state"] in ("review","published") else row["replaces"]
        child=prepare_publication(db,u,request)
    db.execute(f"UPDATE {table} SET version=? WHERE id=?",(max(row["version"]+1,child["version"]),child["id"]))
    db.execute("INSERT INTO revisions VALUES(?,?,?)",(table,identifier,child["id"]))
    audit(db,u["id"],table+".revise",child["id"],areas,reason=reason)
    return summary(item(db,table,child["id"]))

def revised_dataset(db,u,identifier,data):
    from .resources import real_complements
    require(u,"data.edit")
    row=item(db,"datasets",identifier); areas=json.loads(row["scope"]);permit(u,areas)
    check(not row["warning"] and not successor(db,"datasets",identifier),409,"Utilisez la dernière version pour apporter une correction.")
    reason=textfield(data.get("reason"),"Motif de correction",1600)
    payload=json.loads(row["payload"])
    if "csv" in data:
        additions=real_complements(data["csv"],areas)
        existing={(r["region"],r["year"],r["cycle"],r["indicator"],r.get("sex"),r.get("status")) for r in payload["observations"]}
        check(not any((r["region"],r["year"],r["cycle"],r["indicator"],r.get("sex"),r.get("status")) in existing for r in additions),409,"Complément déjà présent ; corrigez la valeur par identifiant.")
        payload["observations"].extend(additions)
        archive(db,"complements.csv",data["csv"].encode())
    else:
        observation_id=textfield(data.get("observation_id"),"Observation")
        obs=next((v for v in payload["observations"] if v["id"]==observation_id),None)
        check(obs is not None,404,"Observation inconnue.")
        value=data.get("value")
        check(type(value) in (int,float) and math.isfinite(value) and value>=0,422,"Valeur corrigée invalide.")
        if obs.get("unit") in ("élèves","personnes","salles","écoles","structures","eleves","ecoles"): check(float(value).is_integer(),422,"Effectif entier requis.")
        obs.update(value=value,state="available",correction={"reason":reason,"actor":u["id"],"at":now(),"previous_value":obs["value"]})
    from collections import Counter
    from ingestion.qualite import reconcile
    counts,anomalies=reconcile(payload["observations"])
    arithmetic={"ips_incoherent","marges_inter_tableaux","somme_region","somme_statut","somme_status","somme_area","somme_sex","somme_level"}
    payload["anomalies"]=[v for v in payload["anomalies"] if v["code"] not in arithmetic]+anomalies
    counts_meta=payload["metadata"]["counts"]
    states=Counter(r["state"] for r in payload["observations"])
    counts_meta.update({k:states.get(k,0) for k in ("available","missing","invalid","not_applicable")})
    counts_meta.update(observations=len(payload["observations"]),anomalies=len(payload["anomalies"]))
    payload["metadata"]["checks"].update(counts)
    if "csv" not in data and obs["table"] in ("PRI01","PRI02","PRI13") and payload.get("synthetic"):
        # Les compléments sont calibrés à la source d'origine. Une correction de marge
        # demande un nouveau contrôle du CSV avant de les réutiliser dans cette version.
        payload["synthetic"]=[]
        payload["anomalies"].append(dict(code="demo_recalibrer",message="Compléments synthétiques retirés de cette version après correction d’une marge de calibration.",severity="warning",region=None,year=obs["year"],table=obs["table"],sheet=obs["sheet"],cell=obs["cell"]))
        counts_meta["anomalies"]=len(payload["anomalies"])
    identifier2=uid()
    version=db.execute("SELECT coalesce(max(version),0)+1 FROM datasets WHERE sha=?",(row["sha"],)).fetchone()[0]
    db.execute("INSERT INTO datasets VALUES(?,?,?,?,?,?,?,?,?,?,?)",(identifier2,row["title"],version,u["id"],row["scope"],"draft",now(),row["sha"],identifier,dump(payload),None))
    audit(db,u["id"],"data.revise",identifier2,areas,reason=reason)
    return describe(db,u,"datasets",identifier2)
