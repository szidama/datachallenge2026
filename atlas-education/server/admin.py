import json
from .permissions import PERMISSIONS, GROUPS, modules_for
from .storage import Error, audit, check, contains, credentials, dump, new_account, now, permit, require, scope, textfield, uid, user

ROLE_ACTIONS={"role","role_update"}
DIRECT_ACTIONS=ROLE_ACTIONS | {"create","grant"}

def role_permissions(db,name):
    row=db.execute("SELECT permissions FROM roles WHERE name=?",(name,)).fetchone()
    check(row,422,"Rôle inconnu.")
    return sorted(PERMISSIONS) if name=="admin" else sorted(json.loads(row[0]))

def can_delegate(u,permissions):
    return set(permissions)<=set(u["permissions"])

def guard_target(u,target):
    permit(u,target["scope"])
    check(target["id"]!=u["id"],403,"Modification de ses propres accès interdite.")
    check(can_delegate(u,target["permissions"]) and (target["role"]!="admin" or u["role"]=="admin"),
          403,"Ce compte dépasse votre autorité de gestion.")

def check_request(db,u,data):
    action=data["action"]
    require(u,"roles.manage" if action in ROLE_ACTIONS else "users.manage")
    permit(u,data["scope"])
    if action in ROLE_ACTIONS:
        check(u["scope"]==["*"],403,"Configuration nationale requise.")
        check(data["name"]!="admin",403,"Le rôle Administrateur conserve toutes les permissions.")
        check(can_delegate(u,data["permissions"]),403,"Ces permissions dépassent vos habilitations.")
        if action=="role_update":
            check(u["role"]!=data["name"] and can_delegate(u,role_permissions(db,data["name"])),403,"Modification de ce rôle non autorisée.")
    if action in ("grant","recover"):
        target=user(db,data["user_id"]);check(target,404,"Compte inconnu.")
        guard_target(u,target)
    if action in ("grant","create"):
        require(u,"roles.manage")
        check(can_delegate(u,role_permissions(db,data["role"])) and (data["role"]!="admin" or u["role"]=="admin"),
              403,"Vous ne pouvez pas attribuer ce rôle.")

def roles_catalogue(db,u):
    require(u,"roles.manage","users.manage")
    roles=[]
    for r in db.execute("SELECT name FROM roles ORDER BY name"):
        name=r["name"];permissions=role_permissions(db,name)
        roles.append(dict(name=name,permissions=permissions,modules=modules_for(permissions),
            editable="roles.manage" in u["permissions"] and u["scope"]==["*"] and name not in ("admin",u["role"]) and can_delegate(u,permissions),
            assignable=can_delegate(u,permissions) and (name!="admin" or u["role"]=="admin")))
    return {"items":roles,"catalogue":sorted(PERMISSIONS),"groups":GROUPS,"direct_access":u["role"]=="admin"}

def take_request(db,u,obj):
    action=obj["action"]
    require(u,"roles.manage" if action in ROLE_ACTIONS else "users.manage")
    if action in ROLE_ACTIONS:
        name=textfield(obj.get("name"),"Rôle",60)
        perms=obj.get("permissions")
        check(isinstance(perms,list) and perms and all(isinstance(p,str) and p in PERMISSIONS for p in perms),422,"Sélectionnez des permissions du catalogue.")
        req=dict(action=action,name=name,permissions=sorted(set(perms)),scope=["*"])
        check_request(db,u,req)
        if action=="role":
            check(not db.execute("SELECT 1 FROM roles WHERE name=?",(name,)).fetchone(),409,"Ce rôle existe déjà.")
        else:
            req["previous"]=role_permissions(db,name)
            check(req["previous"]!=req["permissions"],422,"Les permissions sont identiques.")
    else:
        check(action in {"create","grant","recover"},422,"Demande d’habilitation inconnue.")
        req={"action":action}
        if action=="create":
            req["username"]=textfield(obj.get("username"),"Identifiant",80)
            check(not db.execute("SELECT 1 FROM users WHERE username=?",(req["username"],)).fetchone(),409,"Identifiant déjà utilisé.")
        else:
            target=user(db,obj.get("user_id"));check(target,404,"Compte inconnu.")
            guard_target(u,target)
            req["user_id"]=target["id"]
            req["previous_role"]=target["role"];req["previous_scope"]=target["scope"]
            req["access_version"]=target["access_version"]
            if "expected_version" in obj:
                check(obj["expected_version"]==target["access_version"],409,"Les accès de ce compte ont changé. Rechargez sa fiche.")
        if action in ("grant","create"):
            defaults=target if action=="grant" else {}
            req["role"]=textfield(obj.get("role",defaults.get("role")),"Rôle",60)
            req["scope"]=scope(obj.get("scope",defaults.get("scope")))
            req["role_permissions"]=role_permissions(db,req["role"])
            if "expected_role_permissions" in obj:
                check(obj["expected_role_permissions"]==req["role_permissions"],409,"Les permissions du rôle ont changé. Rechargez sa fiche.")
            if "permissions" in obj:
                check(u["role"]=="admin",403,"La personnalisation individuelle est réservée à l’administrateur.")
                perms=obj["permissions"]
                check(isinstance(perms,list) and all(isinstance(k,str) and k in PERMISSIONS for k in perms),422,"Permissions individuelles invalides.")
                check(req["role"]!="admin" or set(perms)==PERMISSIONS,422,"Le rôle Administrateur conserve toutes ses permissions.")
                req["permissions"]=sorted(set(perms))
        else:req["scope"]=target["scope"]
        check_request(db,u,req)
    if action in ROLE_ACTIONS and "expected_role_permissions" in obj and action=="role_update":
        check(obj["expected_role_permissions"]==req["previous"],409,"Le rôle a changé. Rechargez sa fiche.")
    if u["role"]=="admin" and action in DIRECT_ACTIONS:
        response=apply_change(db,u,req)
        if action=="grant" and req["access_version"]==response["access_version"]:
            return {**response,"state":"unchanged"}
        # Une ancienne demande pour la même opération ne doit plus pouvoir l’appliquer une seconde fois.
        key="name" if action in ROLE_ACTIONS else "username" if action=="create" else "user_id"
        for row in db.execute("SELECT id,request FROM grants WHERE state='pending'").fetchall():
            old=json.loads(row["request"])
            if old["action"]==action and old[key]==req[key]:
                db.execute("UPDATE grants SET state='superseded' WHERE id=?",(row["id"],))
                audit(db,u["id"],"grant.supersede",row["id"],old["scope"],reason="Remplacée par une opération directe de l’administrateur.")
        return {**response,"state":"applied"}
    for pending in db.execute("SELECT request FROM grants WHERE state='pending'"):
        other=json.loads(pending["request"])
        key="name" if action in ROLE_ACTIONS else "username" if action=='create' else "user_id"
        check(other["action"]!=action or other[key]!=req[key],409,"Une demande est déjà en attente pour cet élément.")
    identifier=uid()
    db.execute("INSERT INTO grants VALUES(?,?,?,?,?)",(identifier,u["id"],dump(req),"pending",now()))
    audit(db,u["id"],"grant.request",identifier,req["scope"],reason=request_description(req))
    return {"id":identifier,"state":"pending","request":req}

def request_description(req):
    name=req.get("username") or req.get("name") or req.get("user_id")
    if req["action"] in ROLE_ACTIONS:
        before=set(req.get("previous",[]));after=set(req["permissions"])
        return f"{name} · Ajouts : {', '.join(sorted(after-before)) or 'aucun'} · Retraits : {', '.join(sorted(before-after)) or 'aucun'}"
    return f"{req['action']} · {name}"+(" · "+req["role"] if "role" in req else "")

def approver(db,u,row,data):
    check_request(db,u,data)
    check(u["id"] not in (row["actor"],data.get("user_id")),403,"Double contrôle indépendant requis.")

def grants_list(db,u):
    require(u,"users.manage","roles.manage")
    out=[]
    for row in db.execute("SELECT * FROM grants WHERE state='pending' ORDER BY created"):
        data=json.loads(row["request"])
        if not contains(u["scope"],data["scope"]):continue
        if ("roles.manage" if data["action"] in ROLE_ACTIONS else "users.manage") not in u["permissions"]:continue
        try:approver(db,u,row,data);allowed=True
        except Error:allowed=False
        out.append({**dict(row),"request":data,"can_decide":allowed,"can_cancel":row["actor"]==u["id"]})
    return out

def access_snapshot(account):
    return {key:account[key] for key in ("username","role","scope","permissions","permission_overrides")}

def change_log(db,actor,action,resource,before,after):
    areas=set((before or {}).get("scope",[])) | set(after.get("scope",[]))
    area=sorted(areas) if areas and "*" not in areas else ["*"]
    audit(db,actor,action,resource,area,reason=dump({"before":before,"after":after}))

def apply_change(db,u,data):
    action=data["action"]
    if "role_permissions" in data:
        check(data["role_permissions"]==role_permissions(db,data["role"]),409,"Le rôle a changé. Renouvelez la demande.")
    if action in ROLE_ACTIONS:
        name=data["name"];before=None
        if action=="role":
            check(not db.execute("SELECT 1 FROM roles WHERE name=?",(name,)).fetchone(),409,"Ce rôle existe déjà.")
            db.execute("INSERT INTO roles VALUES(?,?)",(name,dump(data["permissions"])))
        else:
            check(role_permissions(db,name)==data["previous"],409,"Les permissions ont changé. Renouvelez la demande.")
            before={"role":name,"permissions":data["previous"]}
            holders=[(r["id"],access_snapshot(user(db,r["id"]))) for r in db.execute("SELECT id FROM users WHERE role=?",(name,))]
            db.execute("UPDATE roles SET permissions=? WHERE name=?",(dump(data["permissions"]),name))
            db.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE role=?)",(name,))
            for identifier,old in holders:
                new=access_snapshot(user(db,identifier))
                if old!=new:change_log(db,u["id"],"user.access",identifier,old,new)
        change_log(db,u["id"],"role.create" if action=="role" else "role.permissions",name,before,{"role":name,"permissions":data["permissions"]})
        return {"name":name}
    before=None
    if action=="create":
        created=new_account(db,data["username"],data["role"],data["scope"])
        identifier=created["id"]
    else:
        identifier=data["user_id"];target=user(db,identifier)
        if "access_version" in data:
            check(target["access_version"]==data["access_version"],409,"Les habilitations ont changé. Renouvelez la demande.")
        elif "previous_role" in data:
            check((target["role"],target["scope"])==(data["previous_role"],data["previous_scope"]),409,"Les habilitations ont changé. Renouvelez la demande.")
        if action=="recover":return credentials(db,identifier)
        before=access_snapshot(target)
        keep_admin(db,target,data["role"],data["scope"])
        db.execute("UPDATE users SET role=?,scope=? WHERE id=?",(data["role"],dump(data["scope"]),identifier))
    if "permissions" in data or (before and before["role"]!=data["role"]):
        base=set(role_permissions(db,data["role"]))
        desired=set(data.get("permissions",base))
        db.execute("DELETE FROM account_permissions WHERE user_id=?",(identifier,))
        db.executemany("INSERT INTO account_permissions VALUES(?,?,?)",[(identifier,k,k in desired) for k in sorted(base ^ desired)])
    updated=user(db,identifier);after=access_snapshot(updated)
    if before!=after:
        db.execute("DELETE FROM sessions WHERE user_id=?",(identifier,))
        change_log(db,u["id"],"user.create" if action=="create" else "user.access",identifier,before,after)
    if action=="create":return {**updated,"password":created["password"],"totp_secret":created["totp_secret"]}
    return updated

def decide(db,u,identifier,decision,reason=None):
    row=db.execute("SELECT * FROM grants WHERE id=?",(identifier,)).fetchone()
    check(row,404,"Demande introuvable.")
    data=json.loads(row["request"])
    require(u,"roles.manage" if data["action"] in ROLE_ACTIONS else "users.manage")
    permit(u,data["scope"])
    check(row["state"]=="pending",409,"Demande déjà traitée.")
    if decision=="cancel":
        check(row["actor"]==u["id"],403,"Seul le demandeur peut annuler.")
    else:approver(db,u,row,data)
    response={}
    if decision=="approve":
        check_request(db,user(db,row["actor"]),data)
        response=apply_change(db,u,data)
        note=request_description(data)
    else:note=textfield(reason,"Motif",1600)
    state={"approve":"approved","reject":"rejected","cancel":"cancelled"}[decision]
    db.execute("UPDATE grants SET state=? WHERE id=?",(state,identifier))
    audit(db,u["id"],"grant."+decision,identifier,data["scope"],reason=note)
    return {"id":identifier,"state":state,**response}

def keep_admin(db,target,role=None,areas=None):
    if target["role"]=="admin" and target["scope"]==["*"] and target["status"]=="active" and (role!="admin" or areas!=["*"]):
        check(db.execute("SELECT 1 FROM users WHERE role='admin' AND status='active' AND scope=? AND id<>?",(dump(["*"]),target["id"])).fetchone(),
              409,"Un administrateur national actif est requis.")

def manage_user(db,u,identifier,data):
    require(u,"users.manage")
    target=user(db,identifier);check(target,404,"Compte introuvable.")
    guard_target(u,target)
    action=data.get("action")
    if action in ("grant","recover"):return take_request(db,u,{**data,"user_id":identifier})
    check(action in ("activate","suspend","disable","revoke"),422,"Action de compte inconnue.")
    if action in ("suspend","disable"):keep_admin(db,target)
    if action!="revoke":
        db.execute("UPDATE users SET status=? WHERE id=?",(dict(activate="active",suspend="suspended",disable="disabled")[action],identifier))
    db.execute("DELETE FROM sessions WHERE user_id=?",(identifier,))
    audit(db,u["id"],"user."+action,identifier,target["scope"])
    return user(db,identifier)
