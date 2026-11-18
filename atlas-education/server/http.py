"""API servie en même origine. Le seul répertoire de fichiers exposé est web/."""
import csv
import hmac
import io
import json
import mimetypes
import os
from http import HTTPStatus
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sqlite3
import threading
from urllib.parse import parse_qsl, unquote, urlsplit

from . import admin, domain as d, profile
from .permissions import GROUPS
from .storage import Error, audit, authenticate, check, connect, contains, current_session, dump, now, permit, require, scope, textfield, token_hash, uid, user

class Download:
    def __init__(self,content,mime,filename):
        self.content=content
        self.mime=mime
        self.filename=filename

def csv_file(rows,name):
    headers=["source","version","table","sheet","cell","region","year","cycle","sex","status","area","level","indicator","unit","value","state","origin","method","generator_version","seed","official","price_year"]
    stream=io.StringIO(newline="")
    writer=csv.DictWriter(stream,fieldnames=headers,extrasaction="ignore");writer.writeheader()
    for r in rows:
        # Texte de source traité comme texte, y compris à l'ouverture dans un tableur.
        writer.writerow({k:("'"+v if isinstance(v,str) and v[:1] in ("=","+","-","@","\t","\r") else v) for k,v in r.items() if k in headers})
    return Download(b"\xef\xbb\xbf"+stream.getvalue().encode(),"text/csv; charset=utf-8",name+".csv")

def public_api(db,parts,query):
    check(parts[:1]==["publications"],404,"Route publique inconnue.")
    columns="""id,title,kind,state,version,scope,created,
               CASE WHEN warning IS NOT NULL THEN 'Source en réexamen. Le maintien de cette version historique a été autorisé.' ELSE NULL END AS warning,
               (SELECT max(created) FROM audit WHERE action='publications.publish' AND resource=publications.id AND result='ok') AS published_at,
               (SELECT max(created) FROM audit WHERE action='publications.retain' AND resource=publications.id AND result='ok') AS retained_at"""
    if len(parts)==1:
        return d.paginate([d.summary(r) for r in db.execute(f"SELECT {columns} FROM publications WHERE state='published' ORDER BY rowid DESC")],query)
    check(len(parts)==2 or (len(parts)==3 and parts[2]=="export"),404,"Ressource publique introuvable.")
    row=db.execute(f"SELECT {columns},payload FROM publications WHERE id=? AND state='published'",(parts[1],)).fetchone()
    check(row,404,"Cette version n’est pas diffusée.")
    result={**d.summary(row),"payload":json.loads(row["payload"])}
    if len(parts)==3:
        if query.get("format")=="csv": return csv_file(result["payload"].get("observations",[]),"publication-"+row["id"])
        return Download(dump(result).encode(),"application/json","publication-"+row["id"]+".json")
    return result

def job_result(db,u,identifier):
    row=db.execute("SELECT * FROM jobs WHERE id=?",(identifier,)).fetchone();check(row,404,"Calcul introuvable.")
    params=json.loads(row["request"])
    need={"projection":"projection.run","optimization":"optimization.run","exploration":"analysis.run"}[params["kind"]]
    require(u,need);permit(u,json.loads(row["scope"]));check(row["author"]==u["id"],403,"Calcul d’un autre utilisateur.")
    return {k:row[k] for k in ("id","state","created","result_id","error")}

def run_job(state,identifier):
    db=connect(state)
    try:
        with db:
            row=db.execute("SELECT * FROM jobs WHERE id=?",(identifier,)).fetchone()
            db.execute("UPDATE jobs SET state='running' WHERE id=?",(identifier,))
        with db:
            db.execute("BEGIN IMMEDIATE")
            actor=user(db,row["author"])
            result=d.create_analysis(db,actor,json.loads(row["request"]))
            db.execute("UPDATE jobs SET state='finished',result_id=? WHERE id=?",(result["id"],identifier))
    except Exception as exc:
        with db:
            message=str(exc) if isinstance(exc,Error) else "Échec du calcul. Vérifiez les paramètres et relancez."
            db.execute("UPDATE jobs SET state='failed',error=? WHERE id=?",(message,identifier))
    finally: db.close()

def private_api(db,u,method,parts,q,data,server):
    name=parts[0] if parts else ""
    if method=="GET":
        if parts==["profile"]:return profile.read_profile(db,u)
        if name in ("datasets","analyses") and len(parts)==3 and parts[2]=="dependencies":
            target=d.item(db,name,parts[1]);d.readable(u,name,target)
            candidates=["analyses","publications"] if name=="datasets" else ["publications","decisions"]
            related={}
            for table_name in candidates:
                key="dataset_id" if name=="datasets" else "analysis_id"
                items=[]
                for record in db.execute(f"SELECT * FROM {table_name} WHERE {key}=?",(parts[1],)):
                    try:d.readable(u,table_name,record)
                    except Error as exc:
                        if exc.status==403:continue
                        raise
                    items.append(d.summary(record))
                related[table_name]=items
            return related
        if parts==["planning","defaults"]:
            require(u,"projection.run","optimization.run")
            from planning import defaults
            return defaults()
        if name in d.TABLES:
            if len(parts)==1:return d.list_records(db,u,name,q)
            if len(parts)==2:return d.describe(db,u,name,parts[1])
            if len(parts)==3:
                action=parts[2];row=d.item(db,name,parts[1]);d.readable(u,name,row)
                if action=="export": require(u,"report.export")
                if name=="datasets" and action in ("observations","export"):
                    rows=d.visible_observations(json.loads(row["payload"]),u["scope"],q)
                    return csv_file(rows,"observations-"+row["id"]) if action=="export" else d.paginate(rows,q)
                if name=="datasets" and action=="source":
                    require(u,"data.import","data.validate");permit(u,["*"])
                    archived=db.execute("SELECT contents FROM archives WHERE sha=?",(row["sha"],)).fetchone()
                    return Download(archived[0],"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","source-"+row["id"]+".xlsx")
                if action=="export":
                    return Download(dump(d.describe(db,u,name,parts[1])).encode(),"application/json",name+"-"+parts[1]+".json")
        if parts==["jobs"]:
            require(u,"analysis.run","optimization.run","projection.run")
            return {"items":[job_result(db,u,r["id"]) for r in db.execute("SELECT id,scope,request FROM jobs WHERE author=? ORDER BY created DESC LIMIT 100",(u["id"],)) if contains(u["scope"],json.loads(r["scope"])) and {"projection":"projection.run","optimization":"optimization.run","exploration":"analysis.run"}[json.loads(r["request"])["kind"]] in u["permissions"]]}
        if name=="jobs" and len(parts)==2:return job_result(db,u,parts[1])
        if parts==["roles"]:return admin.roles_catalogue(db,u)
        if parts==["grants"]:return d.paginate(admin.grants_list(db,u),q)
        if parts==["users"]:
            require(u,"users.manage")
            rows=[]
            for row in db.execute("SELECT id,scope FROM users ORDER BY username"):
                if contains(u["scope"],json.loads(row["scope"])):
                    target=user(db,row["id"])
                    try:admin.guard_target(u,target);target["manageable"]=True
                    except Error:target["manageable"]=False
                    rows.append(target)
            return {**d.paginate(rows,q),"pending_requests":admin.grants_list(db,u)}
        if parts==["audit"]:
            require(u,"audit.read")
            search=str(q.get("search","")).strip().casefold()
            outcome=q.get("result","")
            check(outcome in ("","ok","refus"),422,"Résultat d’audit inconnu.")
            entries=[]
            for r in db.execute("SELECT a.*,u.username AS actor_name FROM audit a LEFT JOIN users u ON u.id=a.actor ORDER BY seq DESC"):
                area=json.loads(r["scope"])
                if u["scope"]!=["*"] and (not area or not contains(u["scope"],area)):continue
                if outcome and outcome!=r["result"]:continue
                if search and not any(search in str(r[k] or "").casefold() for k in ("action","resource","actor","actor_name","reason")):continue
                event={**dict(r),"scope":area}
                if r["action"] in ("user.create","user.access","role.create","role.permissions") and r["reason"]:
                    event["changes"]=json.loads(r["reason"])
                entries.append(event)
            return {**d.paginate(entries,q),"permission_labels":{key:name for group in GROUPS.values() for key,name in group.items()}}
    if method=="POST":
        if parts==["profile"]:return profile.save_details(db,u,data)
        if parts==["profile","login"]:return profile.change_login(db,u,data)
        if parts in (["imports","preview"],["datasets"]):
            require(u,"data.import");permit(u,["*"])
            name,raw=d.decode_file(data)
            demo=server.demo_path if data.get("include_demo") is True else None
            if demo:check(demo.is_file(),422,"Complément de démonstration introuvable.")
            payload=d.ingest(name,raw,demo)
            if parts[0]=="imports":
                return {k:v for k,v in payload.items() if k not in ("observations","synthetic")}|{"sample":payload["observations"][:20]}
            if demo:d.archive(db,demo.name,demo.read_bytes())
            return d.save_dataset(db,u,name,raw,payload,data.get("title",name))
        if parts==["analyses"]:return d.create_analysis(db,u,data)
        if parts==["jobs"]:
            kind=data.get("kind")
            check(kind in ("projection","optimization","exploration"),422,"Type de calcul inconnu.")
            require(u,{"projection":"projection.run","optimization":"optimization.run","exploration":"analysis.run"}[kind])
            areas=scope(data.get("scope",u["scope"]));permit(u,areas)
            source=d.item(db,"datasets",data.get("dataset_id"));check(contains(json.loads(source["scope"]),areas),403,"Source hors périmètre.")
            check(db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]<8,429,"File de calcul pleine.")
            identifier=uid()
            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,NULL,NULL)",(identifier,u["id"],dump(areas),"queued",now(),dump(data)))
            db.commit()
            threading.Thread(target=run_job,args=(server.state,identifier),daemon=True).start()
            return {"id":identifier,"state":"queued"}
        if parts==["publications"]:return d.prepare_publication(db,u,data)
        if len(parts)==3 and name in ("datasets","analyses","publications") and parts[2]=="actions":return d.transition(db,u,name,parts[1],data)
        if name=="datasets" and len(parts)==3 and parts[2]=="revise":return d.revised_dataset(db,u,parts[1],data)
        if name in ("analyses","publications") and len(parts)==3 and parts[2]=="revise":
            return d.revise_result(db,u,name,parts[1],data)
        if parts==["decisions"]:
            require(u,"decision.record")
            a=d.item(db,"analyses",data.get("analysis_id"));areas=json.loads(a["scope"]);permit(u,areas)
            check(a["state"]=="validated" and not a["warning"],409,"Une analyse validée et actuelle est requise.")
            yr=data.get("year");cl=data.get("classification","indicative")
            check(type(yr) is int and 2025<=yr<=2050 and cl in ("indicative","programmee","engagee"),422,"Programmation invalide.")
            choice=textfield(data.get("option"),"Option",400);reason=textfield(data.get("reason"),"Motivation",4000); identifier=uid()
            db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?)",(identifier,a["id"],u["id"],a["scope"],now(),choice,reason,yr,cl))
            audit(db,u["id"],"decision.record",identifier,areas,reason=reason)
            return d.summary(d.item(db,"decisions",identifier))
        if parts==["users"]:return admin.take_request(db,u,{**data,"action":"create"})
        if parts==["roles"]:return admin.take_request(db,u,{**data,"action":"role"})
        if name=="users" and len(parts)==3 and parts[2]=="actions":return admin.manage_user(db,u,parts[1],data)
        if name=="roles" and len(parts)==3 and parts[2]=="permissions":
            return admin.take_request(db,u,{**data,"action":"role_update","name":parts[1]})
        if name=="grants" and len(parts)==3 and parts[2] in ("approve","reject","cancel"):
            return admin.decide(db,u,parts[1],parts[2],data.get("reason"))
    raise Error(404,"Route inconnue.")

class Handler(BaseHTTPRequestHandler):
    server_version="Atlas"
    sys_version=""
    def log_message(self,*args):pass
    def send_content(self,status,content,mime="application/json; charset=utf-8",extra=()):
        self.send_response(status)
        self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(content)))
        self.send_header("Cache-Control","no-store, max-age=0")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","same-origin")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        for k,v in extra:self.send_header(k,v)
        self.end_headers()
        if self.command!="HEAD":self.wfile.write(content)
    def run(self):
        path=urlsplit(self.path)
        segments=[unquote(v) for v in path.path.strip("/").split("/") if v]
        query=dict(parse_qsl(path.query,max_num_fields=50))
        db=None;actor="anonymous"
        try:
            if self.server.local_demo:
                port=self.server.server_port
                hosts={"127.0.0.1","localhost"}
                allowed={f"{host}:{port}" for host in hosts}
                if port==80:allowed.update(hosts)
                check(self.client_address[0]=="127.0.0.1" and self.headers.get("Host","").lower() in allowed,403,"Démonstration réservée à ce poste.")
            if segments[:1]!=["api"]:
                check(self.command in ("GET","HEAD"),405,"Méthode refusée.")
                root=self.server.web.resolve()
                if not segments:file=root/"index.html"
                elif segments==["admin"]: file=root/"admin.html"
                elif segments[0]=="assets" and len(segments)>1:file=root.joinpath(*segments)
                else: raise Error(404,"Page inconnue.")
                check(file.resolve().is_relative_to(root) and file.is_file(),404,"Page introuvable.")
                content=file.read_bytes()
                if segments==["admin"] and self.server.local_demo:
                    content=content.replace(b'data-connexion="standard"',b'data-connexion="demo-locale"',1)
                if segments==["admin"] and getattr(self.server,"personal_instance",False):
                    content=content.replace(b"<html ",b'<html data-instance="personnelle" ',1)
                self.send_content(200,content,mimetypes.guess_type(str(file))[0] or "application/octet-stream");return
            parts=segments[1:];method="GET" if self.command=="HEAD" else self.command
            db=connect(self.server.state)
            data={};extra=[]
            if method=="POST":
                # Une origine tierce ne peut ni se connecter, ni effectuer une action authentifiée.
                origin=self.headers.get("Origin")
                if origin:
                    expected=self.server.origin or ("http://"+self.headers.get("Host",""))
                    check(origin==expected,403,"Origine non autorisée.")
                size=int(self.headers.get("Content-Length","0"))
                check(0<=size<=14*1024**2,413,"Requête trop volumineuse.")
                check(self.headers.get_content_type()=="application/json",415,"Un objet JSON est requis.")
                data=json.loads(self.rfile.read(size) or b"{}")
                check(isinstance(data,dict),422,"Un objet JSON est requis.")
                db.execute("BEGIN IMMEDIATE")
            cookie=SimpleCookie()
            try:cookie.load(self.headers.get("Cookie",""))
            except CookieError:pass
            token=cookie["atlas_session"].value if "atlas_session" in cookie else ""
            flags="; Path=/; HttpOnly; SameSite=Strict"+("; Secure" if self.server.secure_cookie else "")
            if parts==["login"] and method=="POST":
                secret,result=authenticate(db,data,self.client_address[0],require_totp=not self.server.local_demo)
                extra.append(("Set-Cookie","atlas_session="+secret+"; Max-Age=28800"+flags))
            elif parts[:1]==["public"] and method=="GET":result=public_api(db,parts[1:],query)
            elif parts[:1]==["private"] or parts==["logout"]:
                u,csrf=current_session(db,token);actor=u["id"]
                if method=="POST":check(hmac.compare_digest(csrf,self.headers.get("X-CSRF-Token","")),403,"Jeton de session invalide.")
                if parts==["logout"] and method=="POST":
                    db.execute("DELETE FROM sessions WHERE token=?",(token_hash(token),));extra.append(("Set-Cookie","atlas_session=; Max-Age=0"+flags));result={"ok":True}
                elif parts==["private","me"] and method=="GET":result={"user":u,"csrf":csrf}
                else:
                    result=private_api(db,u,method,parts[1:],query,data,self.server)
                    if method=="POST" and parts==["private","profile","login"]:
                        extra.append(("Set-Cookie","atlas_session=; Max-Age=0"+flags))
                if method=="GET" or parts==["logout"]:audit(db,actor,method+" "+path.path,parts[2] if len(parts)>2 else "",u["scope"])
            else:raise Error(404,"Route inconnue.")
            db.commit()
            if isinstance(result,Download):self.send_content(200,result.content,result.mime,[("Content-Disposition",'attachment; filename="'+result.filename+'"')])
            else:self.send_content(200,dump(result).encode(),extra=extra)
        except (Error,ValueError,TypeError,UnicodeError) as exc:
            status=exc.status if isinstance(exc,Error) else 422
            message=str(exc) if isinstance(exc,Error) else "Paramètres ou document JSON invalides."
            if db:
                db.rollback()
                if status in (401,403,409):
                    audit(db,actor,self.command+" "+path.path,result="refus",reason=message);db.commit()
            self.send_content(status,dump({"error":message}).encode())
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:
            if db:db.rollback()
            import traceback
            traceback.print_exc()
            self.send_content(500,dump({"error":"Le traitement a échoué. Consultez le journal du service."}).encode())
        finally:
            if db:db.close()
    do_GET=do_POST=do_HEAD=run

def make_server(state,host="127.0.0.1",port=8050,web=None,origin=None,*,local_demo=False,personal_instance=False):
    check(not local_demo or (host=="127.0.0.1" and not origin),422,"La démonstration locale requiert 127.0.0.1 et aucune origine de proxy.")
    server=ThreadingHTTPServer((host,port),Handler)
    server.local_demo=local_demo
    server.personal_instance=personal_instance
    server.state=Path(state);server.web=Path(web or d.ROOT/"web");server.origin=origin
    server.secure_cookie=bool(origin and origin.startswith("https://"))
    server.demo_path=Path(os.environ.get("ATLAS_DEMO_CSV",str(d.ROOT.parent/"synthetic_demo.csv")))
    return server
