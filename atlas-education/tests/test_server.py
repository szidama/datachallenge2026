import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from server import admin,domain as d
from server.http import Handler, make_server, private_api, public_api
from server.storage import PERMISSIONS, Error, authenticate, connect, current_session, dump, initialize, new_account, totp, user
from server.__main__ import backup,restore

class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]
        book=next(root.glob("DONNEES*.xlsx"))
        cls.book=book; cls.raw=book.read_bytes()
        cls.payload=d.ingest(book.name,cls.raw,root/"synthetic_demo.csv")

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.state=Path(self.tmp.name)/"state"
        initialize(self.state);self.db=connect(self.state)
        self.accounts={name:new_account(self.db,name,role,sc) for name,role,sc in (
            ("tech","admin",["*"]),("data","data",["*"]),("ana","analyst",["*"]),
            ("controle","validator",["*"]),("dec","decider",["*"]),("edi","publisher",["*"]),
            ("centre","analyst",["centre"]))}
        self.source=d.save_dataset(self.db,self.accounts["data"],self.book.name,self.raw,self.payload,"Import test")["id"]
        self.db.commit()
        self.server=SimpleNamespace(state=self.state)
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def api(self,who,method,parts,data=None,q=None):
        return private_api(self.db,self.accounts[who],method,parts.split("/"),q or {},data or {},self.server)
    def err(self,code,fn,*args,**kw):
        with self.assertRaises(Error) as ctx:fn(*args,**kw)
        self.assertEqual(ctx.exception.status,code)
    def action(self,who,table,identifier,action):
        return self.api(who,"POST",f"{table}/{identifier}/actions",{"action":action,"reason":"Recette automatisée du circuit"})
    def validated_source(self):
        self.action("data","datasets",self.source,"submit")
        self.action("controle","datasets",self.source,"validate")
    def publication(self):
        self.validated_source()
        a=self.api("ana","POST","analyses",{"kind":"exploration","title":"Scolarisation","scope":["centre"],"dataset_id":self.source,"parameters":{"filters":{"table":"PRI01","sex":"total"}}})
        self.action("controle","analyses",a["id"],"examine");self.action("controle","analyses",a["id"],"validate")
        self.api("dec","POST","decisions",{"analysis_id":a["id"],"year":2030,"option":"Formuler un programme","classification":"indicative","reason":"Recette"})
        p=self.api("edi","POST","publications",{"scope":["centre"],"title":"Publication de test","dataset_id":self.source,"analysis_id":a["id"],"methodology":"Méthode de recette"})
        self.action("controle","publications",p["id"],"verify");self.action("dec","publications",p["id"],"approve");self.action("edi","publications",p["id"],"publish")
        return p["id"],a["id"]
    def test_publication_droit_retrait_et_dependances(self):
        self.assertEqual(public_api(self.db,["publications"],{})["items"],[])
        pid,aid=self.publication()
        public=public_api(self.db,["publications",pid],{})
        self.assertTrue(public["published_at"]);self.assertIsNone(public["retained_at"])
        self.assertTrue(public["payload"]["observations"])
        self.assertEqual({v["region"] for v in public["payload"]["observations"]},{"centre"})
        self.assertNotIn("raw",public["payload"]["observations"][0])
        corrected=self.api("data","POST",f"datasets/{self.source}/revise",{"reason":"Correction documentée","observation_id":"PRE06:F77","value":0.9114})
        self.assertNotEqual(corrected["id"],self.source)
        self.assertFalse(self.api("ana","GET","analyses/"+aid)["warning"])
        self.assertIsNone(public_api(self.db,["publications",pid],{})["warning"])
        self.action("data","datasets",corrected["id"],"submit")
        self.action("controle","datasets",corrected["id"],"validate")
        self.assertTrue(self.api("ana","GET","analyses/"+aid)["warning"])
        self.err(404,public_api,self.db,["publications",pid],{})
        self.action("dec","publications",pid,"retain")
        maintained=public_api(self.db,["publications",pid],{})
        self.assertTrue(maintained["warning"]);self.assertTrue(maintained["retained_at"])
        self.action("edi","publications",pid,"withdraw")
        self.err(404,public_api,self.db,["publications",pid,"export"],{})
    def test_correction_puis_diffusion_du_resultat_et_du_paquet(self):
        self.validated_source()
        original=self.api("ana","POST","analyses",dict(dataset_id=self.source,scope=["centre"],kind="exploration",
            title="Extraction à vérifier",parameters={"filters":{"table":"PRI01","year":2024}}))
        aid=original["id"]
        self.action("controle","analyses",aid,"examine")
        self.action("controle","analyses",aid,"return")
        self.assertIn("Recette",self.api("ana","GET","analyses/"+aid)["return_reason"])
        correction=dict(title="Extraction corrigée",reason="Retenir le millésime 2025",parameters={"filters":{"table":"PRI01","year":2025}})
        self.err(403,self.api,"controle","POST",f"analyses/{aid}/revise",correction)
        self.err(422,self.api,"ana","POST",f"analyses/{aid}/revise",{**correction,"reason":""})
        v2=self.api("ana","POST",f"analyses/{aid}/revise",{**correction,"scope":["*"]})
        self.assertEqual((v2["scope"],v2["version"],v2["state"]),(["centre"],2,"calculated"))
        fixed=self.api("ana","GET","analyses/"+v2["id"])
        self.assertEqual((fixed["previous"],fixed["correction_reason"]),(aid,correction["reason"]))
        self.assertEqual({r["year"] for r in fixed["result"]["observations"]},{2025})
        self.assertEqual(self.api("ana","GET","analyses/"+aid)["parameters"],original["parameters"])
        self.err(409,self.api,"ana","POST",f"analyses/{aid}/revise",correction)
        request=dict(scope=["centre"],dataset_id=self.source,analysis_id=v2["id"],title="Étude",methodology="Millésime en cours")
        self.err(409,self.api,"edi","POST","publications",request)
        for action in ("examine","validate"):self.action("controle","analyses",v2["id"],action)
        p=self.api("edi","POST","publications",request)["id"]
        self.action("controle","publications",p,"return")
        patch={**request,"methodology":"Extraction régionale pour 2025","reason":"Préciser l’année retenue"}
        self.err(422,self.api,"edi","POST",f"publications/{p}/revise",{**patch,"analysis_id":""})
        new=self.api("edi","POST",f"publications/{p}/revise",patch)
        self.assertEqual((new["version"],new["state"],new["replaces"],new["approver"]),(2,"prepared",None,None))
        self.err(409,self.api,"edi","POST",f"publications/{p}/revise",patch)
        for role,action in (("controle","verify"),("dec","approve"),("edi","publish")):
            self.err(404,public_api,self.db,["publications",new["id"]],{})
            self.action(role,"publications",new["id"],action)
        visible=public_api(self.db,["publications",new["id"]],{})
        self.assertEqual(visible["payload"]["methodology"],patch["methodology"])
        self.assertNotIn("correction_reason",visible)
        self.assertEqual([r["id"] for r in public_api(self.db,["publications"],{})["items"]],[new["id"]])
        self.action("controle","analyses",v2["id"],"invalidate")
        self.err(404,public_api,self.db,["publications",new["id"],"export"],{})
        self.assertTrue(self.api("ana","GET","analyses/"+v2["id"])["can_revise"])
        self.assertEqual(self.api("edi","GET","publications/"+new["id"])["state"],"review")

    def test_correction_source_retournee_et_remplacement_du_portail(self):
        pid,aid=self.publication()
        self.action("controle","datasets",self.source,"invalidate")
        self.assertNotIn("return_reason",self.api("centre","GET","datasets/"+self.source))
        self.err(409,self.action,"data","datasets",self.source,"submit")
        body=dict(reason="Corriger la valeur documentée",observation_id="PRE06:F77",value=0.9114)
        prev=self.source
        for attempt in range(2):
            next_id=self.api("data","POST",f"datasets/{prev}/revise",body)["id"]
            self.err(409,self.api,"data","POST",f"datasets/{prev}/revise",body)
            self.action("data","datasets",next_id,"submit")
            self.action("controle","datasets",next_id,"return" if attempt==0 else "validate")
            prev=next_id
        corrected=self.api("ana","POST",f"analyses/{aid}/revise",dict(title="Résultat corrigé",dataset_id=prev,reason="Nouvelle source"))
        self.assertEqual(corrected["version"],2)
        for step in ("examine","validate"):self.action("controle","analyses",corrected["id"],step)
        new=self.api("edi","POST",f"publications/{pid}/revise",dict(title="Étude corrigée",dataset_id=prev,
            analysis_id=corrected["id"],methodology="Inventaire corrigé",reason="Actualisation du résultat"))
        self.assertEqual(new["replaces"],pid)
        for role,act in (("controle","verify"),("dec","approve"),("edi","publish")):
            self.action(role,"publications",new["id"],act)
        self.assertEqual(self.api("edi","GET","publications/"+pid)["state"],"replaced")
        self.assertEqual([p["id"] for p in public_api(self.db,["publications"],{})["items"]],[new["id"]])

    def test_portee_et_exports(self):
        endpoint=f"datasets/{self.source}/observations"
        rows=self.api("centre","GET",endpoint,q={"region":"sahel"})
        self.assertEqual(rows["total"],0)
        rows=self.api("centre","GET",endpoint,q={"limit":2000})
        self.assertEqual({r["region"] for r in rows["items"]},{"centre"})
        self.err(403,self.api,"centre","GET",f"datasets/{self.source}/source")
        self.assertTrue(self.api("tech","GET",f"datasets/{self.source}/export").content)
        self.err(403,self.api,"ana","GET",f"datasets/{self.source}/source")
        r=self.api("ana","POST","analyses",{"kind":"exploration","title":"National","scope":["*"],"dataset_id":self.source,"parameters":{}})
        self.err(403,self.api,"centre","GET","analyses/"+r["id"])
        self.err(403,self.api,"centre","GET","analyses/"+r["id"]+"/export")
        self.err(403,self.api,"centre","POST","analyses",{"kind":"projection","title":"Autre territoire","dataset_id":self.source,"scope":["sahel"],"parameters":{}})
    def test_authentication_and_revocation(self):
        a=self.accounts["centre"]
        data={"username":a["username"],"password":a["password"],"otp":totp(a["totp_secret"])}
        token,login=authenticate(self.db,data,"localtest")
        self.assertEqual(current_session(self.db,token)[0]["id"],a["id"])
        self.err(401,authenticate,self.db,data,"localtest")
        self.api("tech","POST","users/"+a["id"]+"/actions",{"action":"suspend"})
        self.err(401,current_session,self.db,token)
    def test_demo_locale_mot_de_passe_et_suspension(self):
        a=self.accounts["ana"]
        data={"username":a["username"],"password":a["password"]}
        self.err(401,authenticate,self.db,data,"localtest")
        self.err(401,authenticate,self.db,{**data,"password":"incorrect"},"localtest",require_totp=False)
        for _ in range(2):
            token,_=authenticate(self.db,data,"localtest",require_totp=False)
            self.assertEqual(current_session(self.db,token)[0]["id"],a["id"])
        self.api("tech","POST","users/"+a["id"]+"/actions",{"action":"suspend"})
        self.err(401,current_session,self.db,token)
        self.err(401,authenticate,self.db,data,"localtest",require_totp=False)
        self.err(422,make_server,self.state,host="0.0.0.0",local_demo=True)
        self.err(422,make_server,self.state,origin="https://atlas.example",local_demo=True)
    def test_grants_custom_not_self(self):
        new_role=self.api("tech","POST","roles",{"name":"lecture","permissions":["analysis.run"]})
        self.assertEqual(new_role["state"],"applied")
        self.assertEqual(self.api("tech","GET","grants")["items"],[])
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM roles WHERE name='lecture'").fetchone())
        self.err(403,self.api,"tech","POST","users/"+self.accounts["tech"]["id"]+"/actions",{"action":"grant","role":"decider","scope":["*"]})

    def test_effective_role_changes_propagate_and_protect_admin(self):
        actor=self.accounts["ana"]
        token,_=authenticate(self.db,{"username":actor["username"],"password":actor["password"]},"test",require_totp=False)
        update=self.api("tech","POST","roles/analyst/permissions",{"permissions":["analysis.run","audit.read"]})
        self.assertEqual(update["state"],"applied")
        self.assertFalse(self.api("tech","GET","grants")["items"])
        self.err(401,current_session,self.db,token)
        self.accounts["ana"]=user(self.db,actor["id"])
        self.assertIn("comptes",self.accounts["ana"]["modules"])
        self.assertNotIn("prospective",self.accounts["ana"]["modules"])
        self.err(403,self.api,"ana","GET","users")
        self.err(403,self.api,"ana","GET","planning/defaults")
        self.assertIn("role.permissions",{r["action"] for r in self.api("ana","GET","audit",q={"search":"tech"})["items"]})
        self.err(403,self.api,"tech","POST","roles/admin/permissions",{"permissions":["analysis.run"]})
        self.db.execute("UPDATE roles SET permissions='[]' WHERE name='admin'")
        self.assertEqual(set(user(self.db,self.accounts["tech"]["id"])["permissions"]),PERMISSIONS)

    def test_administrateur_direct_permissions_individuelles_et_journal(self):
        create={"username":"agent.regional","role":"analyst","scope":["nord"],"permissions":["data.read","audit.read"]}
        account=self.api("tech","POST","users",create)
        self.assertEqual(account["state"],"applied")
        self.assertEqual(account["permissions"],["audit.read","data.read"])
        self.assertIn("password",account)
        self.err(409,self.api,"tech","POST","users",create)
        token,_=authenticate(self.db,{"username":account["username"],"password":account["password"]},"local",require_totp=False)
        self.accounts["regional"]=current_session(self.db,token)[0]
        self.err(403,self.api,"regional","GET","planning/defaults")
        self.err(403,self.api,"regional","POST","users",{**create,"username":"interdit"})
        path="users/"+account["id"]+"/actions"
        desired={"action":"grant","role":"data","scope":["centre"],"permissions":["data.read","analysis.read"],"expected_version":account["access_version"]}
        saved=self.api("tech","POST",path,desired)
        self.err(401,current_session,self.db,token)
        self.assertEqual(saved["permissions"],["analysis.read","data.read"])
        self.err(409,self.api,"tech","POST",path,desired)
        self.assertNotEqual(saved["permissions"],user(self.db,self.accounts["data"]["id"])["permissions"])
        events=self.api("tech","GET","audit",q={"search":account["username"]})["items"]
        log=[event for event in events if "changes" in event]
        self.assertEqual([v["action"] for v in log],["user.access","user.create"])
        self.assertEqual(log[0]["actor"],self.accounts["tech"]["id"])
        self.assertTrue(all(event["result"]=="ok" for event in log))
        self.assertEqual(log[0]["scope"],["centre","nord"])
        self.assertEqual(log[0]["changes"]["before"]["permissions"],account["permissions"])
        self.assertEqual(log[0]["changes"]["after"]["role"],"data")
        self.assertEqual(log[0]["changes"]["after"]["scope"],["centre"])
        self.assertIsNone(log[1]["changes"]["before"])
        for key in ("password","totp_secret"):
            self.assertNotIn(account[key],dump(events))
        moved=self.api("tech","POST",path,{"action":"grant","scope":["sahel"]})
        self.assertEqual(moved["permissions"],saved["permissions"])
        self.assertEqual(self.api("tech","POST",path,{"action":"grant","scope":["sahel"]})["state"],"unchanged")
        reset=self.api("tech","POST",path,{"action":"grant","role":"analyst"})
        self.assertEqual(reset["permission_overrides"],{})
        self.assertEqual(set(reset["permissions"]),set(self.accounts["ana"]["permissions"]))
        self.assertFalse(self.api("tech","GET","grants")["items"])
        self.err(422,self.api,"tech","POST",path,{"action":"grant","permissions":["inconnu"]})
        self.err(422,self.api,"tech","POST",path,{"action":"grant","role":"admin","permissions":[]})

    def test_ancien_dossier_remplace_et_controles_reserves(self):
        self.db.execute("INSERT INTO roles VALUES('delegation',?)",(dump(["users.manage","roles.manage","analysis.read"]),))
        self.db.execute("INSERT INTO roles VALUES('consultation',?)",(dump(["analysis.read"]),))
        self.accounts["deleg"]=new_account(self.db,"delegation","delegation",["sahel"])
        create={"role":"consultation","scope":["sahel"],"username":"terrain.sahel"}
        req=self.api("deleg","POST","users",create)
        self.assertEqual(req["state"],"pending")
        self.err(403,self.api,"deleg","POST","users",{**create,"username":"autre","permissions":[]})
        result=self.api("tech","POST","users",create)
        self.assertEqual(result["state"],"applied")
        self.err(409,self.api,"tech","POST","grants/"+req["id"]+"/approve")
        self.assertFalse(self.api("tech","GET","grants")["items"])
        local=new_account(self.db,"administrateur.regional","admin",["centre"])
        self.accounts["local"]=local
        self.err(403,self.api,"local","POST","users/"+result["id"]+"/actions",{"action":"grant","role":"admin","scope":["*"]})
        recover=self.api("tech","POST","users/"+result["id"]+"/actions",{"action":"recover"})
        self.assertEqual(recover["state"],"pending")
        self.err(403,self.api,"tech","POST","grants/"+recover["id"]+"/approve")

    def test_consultation_sans_modification_et_portee(self):
        self.db.execute("INSERT INTO roles VALUES('lecteur',?)",(dump(["data.read","analysis.read"]),))
        self.accounts["lecteur"]=new_account(self.db,"lecture-territoriale","lecteur",["centre"])
        result=self.api("centre","POST","analyses",dict(title="Territoire",dataset_id=self.source,kind="exploration",parameters={}))
        self.assertEqual(self.api("lecteur","GET","analyses/"+result["id"])["scope"],["centre"])
        rows=self.api("lecteur","GET",f"datasets/{self.source}/observations")["items"]
        self.assertTrue(rows)
        self.assertEqual({r["region"] for r in rows},{"centre"})
        self.err(403,self.api,"lecteur","GET","analyses/"+result["id"]+"/export")
        self.err(403,self.api,"lecteur","POST","analyses",dict(title="Autre",dataset_id=self.source,kind="exploration"))
        self.err(403,self.api,"lecteur","GET","audit")
        self.assertNotIn("interventions",self.accounts["lecteur"]["modules"])

    def test_refus_annulation_et_prevention_delegation(self):
        self.accounts["other"]=new_account(self.db,"other","admin",["*"])
        body={"name":"lecture","permissions":["analysis.run"]}
        self.db.execute("INSERT INTO roles VALUES('mandataire',?)",(dump(["roles.manage","analysis.run"]),))
        self.accounts["mandat"]=new_account(self.db,"mandataire","mandataire",["*"])
        req=self.api("mandat","POST","roles",body)
        self.err(409,self.api,"mandat","POST","roles",body)
        self.err(403,self.api,"mandat","POST","grants/"+req["id"]+"/reject",{"reason":"Essai"})
        self.api("other","POST","grants/"+req["id"]+"/reject",{"reason":"Attribution à revoir"})
        self.err(409,self.api,"other","POST","grants/"+req["id"]+"/approve")
        second=self.api("mandat","POST","roles",body)
        self.api("mandat","POST","grants/"+second["id"]+"/cancel",{"reason":"Demande remplacée"})
        self.assertEqual(self.api("mandat","GET","grants")["items"],[])
        self.assertFalse(self.db.execute("SELECT 1 FROM roles WHERE name='lecture'").fetchone())
        self.db.execute("INSERT INTO roles VALUES('delegue',?)",(dump(["roles.manage","users.manage"]),))
        self.accounts["testdeleg"]=new_account(self.db,"testdeleg","delegue",["*"])
        self.err(403,self.api,"testdeleg","POST","roles",body)
        self.err(403,self.api,"testdeleg","POST","users/"+self.accounts["tech"]["id"]+"/actions",{"action":"suspend"})
        self.err(403,self.api,"testdeleg","POST","users",{"username":"ex","role":"admin","scope":["*"]})
        self.assertEqual(self.api("centre","GET","analyses")["items"],[])

    def test_non_auto_validation_with_custom_role(self):
        combo=self.accounts["data"]|{"permissions":["data.edit","data.validate"]}
        self.action("data","datasets",self.source,"submit")
        self.err(403,d.transition,self.db,combo,"datasets",self.source,{"action":"validate","reason":"Essai de recette"})
    def test_job_rights_changed(self):
        a=self.accounts["centre"]
        self.db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)",("job",a["id"],dump(["centre"]),"finished","date",dump({"kind":"projection"}),None,None))
        self.assertEqual(self.api("centre","GET","jobs/job")["state"],"finished")
        self.accounts["centre"]=a|{"permissions":["analysis.run"]}
        self.err(403,self.api,"centre","GET","jobs/job")
    def test_version_idempotente_et_restauration(self):
        again=d.save_dataset(self.db,self.accounts["data"],self.book.name,self.raw,self.payload,"Test réimport");self.assertEqual(again["id"],self.source)
        self.db.commit();dest=Path(self.tmp.name)/"backup.sqlite";backup(self.db,dest)
        target=Path(self.tmp.name)/"restauration";restore(dest,target)
        db=connect(target)
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM datasets").fetchone()[0],1)
            self.assertEqual(hashlib.sha256(db.execute("SELECT contents FROM archives WHERE sha=?",(again["sha"],)).fetchone()[0]).hexdigest(),again["sha"])
            self.assertEqual(db.execute("SELECT count(*) FROM sessions").fetchone()[0],0)
        finally:db.close()
    def test_prospective_brouillon_et_territoire(self):
        r=self.api("centre","POST","analyses",{"kind":"projection","title":"Exploration prospective","dataset_id":self.source,"parameters":{"cycle":"primaire"}})
        self.assertEqual(r["scope"],["centre"])
        self.assertGreater(len(r["result"]["trajectories"]),0)
        self.assertFalse(r["result"]["comparison"])
        request={"kind":"optimization","title":"Test","dataset_id":self.source}
        self.err(403,self.api,"data","POST","analyses",request)
        self.assertTrue(self.api("tech","POST","analyses",request)["result"]["comparison"])
    def test_migration_role_administrateur(self):
        self.db.execute("UPDATE roles SET permissions=? WHERE name='admin'",(dump(["users.manage","roles.manage","audit.read"]),))
        self.db.execute("INSERT INTO roles VALUES('lecture',?)",(dump(["analysis.run"]),))
        def login(name):
            a=self.accounts[name]
            return authenticate(self.db,{"username":a["username"],"password":a["password"]},"localtest",require_totp=False)[0]
        ancien=login("tech")
        analyste=login("ana")
        self.db.commit()
        initialize(self.state)
        self.err(401,current_session,self.db,ancien)
        self.assertEqual(current_session(self.db,analyste)[0]["permissions"],self.accounts["ana"]["permissions"])
        nouveau=login("tech")
        self.db.commit()
        initialize(self.state)
        self.assertEqual(set(current_session(self.db,nouveau)[0]["permissions"]),PERMISSIONS)
        self.assertEqual(self.db.execute("SELECT permissions FROM roles WHERE name='lecture'").fetchone()[0],dump(["analysis.run"]))
        self.assertEqual(self.db.execute("SELECT count(*) FROM audit WHERE action='role.update'").fetchone()[0],1)
    def test_administrateur_circuit_independant(self):
        self.assertEqual(set(self.accounts["tech"]["permissions"]),PERMISSIONS)
        self.action("data","datasets",self.source,"submit")
        self.action("tech","datasets",self.source,"validate")
        analysis=self.api("tech","POST","analyses",{"kind":"projection","title":"Projection primaire","dataset_id":self.source})
        aid=analysis["id"]
        self.err(403,self.action,"tech","analyses",aid,"examine")
        self.action("controle","analyses",aid,"examine")
        self.action("controle","analyses",aid,"validate")
        self.api("tech","POST","decisions",{"analysis_id":aid,"year":2050,"option":"Programmer des salles","reason":"Test de décision"})
        publication=self.api("tech","POST","publications",{"dataset_id":self.source,"analysis_id":aid,
                             "title":"Projection nationale","methodology":"Projection de recette"})
        pid=publication["id"]
        self.err(403,self.action,"tech","publications",pid,"verify")
        self.action("controle","publications",pid,"verify")
        self.action("dec","publications",pid,"approve")
        self.action("tech","publications",pid,"publish")
        self.assertEqual(public_api(self.db,["publications",pid],{})["state"],"published")
        self.action("tech","publications",pid,"withdraw")
        self.err(404,public_api,self.db,["publications",pid],{})
    def test_ajout_collecte_et_validation(self):
        from server.resources import HEADER
        next_data=self.api("data","POST",f"datasets/{self.source}/revise",{"csv":HEADER+"\ncentre,2025,primaire,salles_utilisables,8,salles,Inventaire exemple,\n","reason":"Collecte vérifiée en recette"})
        self.assertEqual(self.api("centre","GET","datasets/"+next_data["id"]+"/observations",q={"table":"COLLECTE"})["total"],1)
        self.err(409,self.api,"ana","POST","analyses",{"kind":"projection","title":"Calcul","dataset_id":next_data["id"],"parameters":{}})
    def test_http_cookie_csrf_and_public_routes(self):
        class MemorySocket:
            def __init__(self,data):self.request=io.BytesIO(data);self.response=bytearray()
            def makefile(self,*args):return self.request
            def sendall(self,chunk):self.response.extend(chunk)
        server=SimpleNamespace(state=self.state,web=Path(self.tmp.name),origin=None,secure_cookie=False,local_demo=False,server_port=8050)
        def wire(path,body=None,headers=None):
            raw=json.dumps(body).encode() if body is not None else b""
            header={"Host":"localhost","Content-Type":"application/json","Content-Length":len(raw),**(headers or {})}
            req=(("POST" if body is not None else "GET")+" "+path+" HTTP/1.0\r\n"+"\r\n".join(f"{k}: {v}" for k,v in header.items())+"\r\n\r\n").encode()+raw
            sock=MemorySocket(req);Handler(sock,("127.0.0.1",1200),server)
            head,_,data=bytes(sock.response).partition(b"\r\n\r\n")
            return head.decode(),json.loads(data)
        self.assertIn("401",wire("/api/private/me")[0].splitlines()[0])
        a=self.accounts["ana"]
        head,session=wire("/api/login",{"username":"ana","password":a["password"],"otp":totp(a["totp_secret"])})
        cookie=next(line for line in head.splitlines() if line.lower().startswith("set-cookie:")).split(": ",1)[1].split(";")[0]
        headers={"Cookie":cookie}
        self.assertEqual(wire("/api/private/me",headers=headers)[1]["user"]["id"],a["id"])
        self.assertIn("401",wire("/api/private/profile")[0].splitlines()[0])
        self.assertEqual(wire("/api/private/profile",headers=headers)[1]["username"],"ana")
        self.assertIn("403",wire("/api/private/profile",{},headers)[0].splitlines()[0])
        self.assertIn("403",wire("/api/private/profile/login",{},headers)[0].splitlines()[0])
        self.assertIn("403",wire("/api/logout",{},headers)[0].splitlines()[0])
        headers["X-CSRF-Token"]=session["csrf"];self.assertTrue(wire("/api/logout",{},headers)[1]["ok"])
        self.assertIn("401",wire("/api/private/me",headers=headers)[0].splitlines()[0])
        login={"username":"ana","password":a["password"]}
        self.assertIn("401",wire("/api/login",{**login,"local_demo":True})[0].splitlines()[0])
        server.local_demo=True
        self.assertIn("403",wire("/api/login",login,{"Host":"externe.example:8050"})[0].splitlines()[0])
        self.assertIn("403",wire("/api/login",login,{"Host":"localhost:8050","Origin":"https://externe.example"})[0].splitlines()[0])
        head,result=wire("/api/login",login,{"Host":"localhost:8050"})
        self.assertIn("200",head.splitlines()[0])
        self.assertEqual(result["user"]["username"],"ana")
        server.local_demo=False
        pid,aid=self.publication();self.db.commit()
        self.assertEqual(wire("/api/public/publications")[1]["items"][0]["id"],pid)
        head,obj=wire("/api/public/publications/"+pid)
        self.assertIn("200",head.splitlines()[0]);self.assertEqual(obj["payload"]["result"]["execution"]["id"],aid)
        self.assertEqual(wire("/api/public/publications/"+pid+"/export")[1],obj)
        self.action("edi","publications",pid,"withdraw");self.db.commit()
        self.assertIn("404",wire("/api/public/publications/"+pid+"/export")[0].splitlines()[0])

    def test_profile_personal_details(self):
        form={"first_name":" Aïcha ","last_name":"Nom de recette","phone":"+226 70 00 00 00","revision":0}
        self.assertEqual(self.api("centre","GET","profile")["phone"],"")
        self.err(422,self.api,"centre","POST","profile",{**form,"user_id":self.accounts["tech"]["id"]})
        self.err(422,self.api,"centre","POST","profile",{**form,"phone":"Téléphone incorrect"})
        saved=self.api("centre","POST","profile",form)
        self.assertEqual((saved["revision"],saved["first_name"],saved["phone"]),(1,"Aïcha",form["phone"]))
        self.err(409,self.api,"centre","POST","profile",form)
        self.assertEqual(self.api("ana","GET","profile")["phone"],"")
        self.assertNotIn(form["phone"],dump(self.api("tech","GET","users")))
        self.assertNotIn(form["phone"],dump(self.api("tech","GET","audit")))
        self.assertEqual(self.api("centre","POST","profile",{**form,"revision":1,"phone":""})["phone"],"")

    def test_profile_credentials(self):
        from scripts.demonstration import current_handoff
        a=self.accounts["centre"]
        old={"username":"centre","password":a["password"]}
        old_session,_=authenticate(self.db,old,"test",require_totp=False)
        other_session,_=authenticate(self.db,old,"test",require_totp=False)
        params={"username":"profil.renomme","current_password":a["password"]}
        change=lambda data:self.api("centre","POST","profile/login",data)
        self.err(422,change,{**params,"role":"admin"})
        self.err(403,change,{**params,"current_password":"incorrect"})
        self.err(409,change,{**params,"username":"ana"})
        self.err(422,change,{**params,"new_password":"trop court","confirmation":"trop court"})
        current_session(self.db,old_session)
        change(params)
        self.db.commit()
        for token in (old_session,other_session):self.err(401,current_session,self.db,token)
        self.err(401,authenticate,self.db,old,"test",require_totp=False)
        renamed={**old,"username":params["username"]}
        token,session=authenticate(self.db,renamed,"test",require_totp=False)
        self.assertEqual(current_handoff(self.state,a)["username"],params["username"])
        self.assertEqual(current_handoff(self.state,a)["password"],old["password"])
        self.accounts["centre"]=session["user"]
        password="Mot de passe de recette modifié"
        self.err(422,change,{**params,"new_password":password,"confirmation":"autre"})
        change({"current_password":old["password"],"new_password":password,"confirmation":password})
        self.db.commit()
        self.err(401,current_session,self.db,token)
        self.err(401,authenticate,self.db,renamed,"test",require_totp=False)
        self.assertIsNone(current_handoff(self.state,a)["password"])
        fresh={"username":params["username"],"password":password}
        self.err(401,authenticate,self.db,fresh,"test")
        _,session=authenticate(self.db,{**fresh,"otp":totp(a["totp_secret"])},"test")
        self.assertEqual((session["user"]["id"],session["user"]["role"],session["user"]["scope"]),(a["id"],a["role"],a["scope"]))
        self.assertNotIn(password,dump(self.api("tech","GET","audit")))
    def test_chart_filters_and_synthetic_origin(self):
        common={"table":"PRI01","sex":"total","region":"national","year":2025}
        rs=self.api("ana","GET",f"datasets/{self.source}/observations",q={**common,"chart":"barres"})
        self.assertEqual(rs["total"],13)
        result=self.api("ana","POST","analyses",{"kind":"exploration","title":"Régions","dataset_id":self.source,"parameters":{"filters":common,"chart":"barres","year":2025}})["result"]
        self.assertEqual([v["id"] for v in rs["items"]],[v["id"] for v in result["observations"]])
        result=self.api("ana","POST","analyses",{"kind":"exploration","title":"Simulation","dataset_id":self.source,"parameters":{"filters":{"table":"DEMO","year":2025},"chart":"table"}})["result"]
        self.assertEqual(result["origin"],"synthetic");self.assertEqual(result["count"],65)
        self.assertFalse(result["observations"][0]["official"])
        rows=self.api("ana","GET",f"datasets/{self.source}/observations",q={"table":"PRI02","sex":"total","status":"public","year":2025,"chart":"composition"})
        self.assertEqual({v["status"] for v in rows["items"]},{"public","prive","total"})

if __name__=="__main__":unittest.main()
