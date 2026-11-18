import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import struct
import time
from datetime import datetime, timezone

from .permissions import PERMISSIONS, modules_for

ROLES = {
    "admin": sorted(PERMISSIONS),
    "data": ["data.import","data.edit","report.export"],
    "analyst": ["analysis.run","projection.run","optimization.run","report.export"],
    "validator": ["data.validate","analysis.validate","report.export"],
    "decider": ["decision.record","publication.approve","report.export"],
    "publisher": ["publication.publish","publication.withdraw","report.export"]
}
REGIONS = set("boucle-du-mouhoun cascades centre centre-est centre-nord centre-ouest centre-sud est hauts-bassins nord plateau-central sahel sud-ouest".split())
SCHEMA = """
CREATE TABLE IF NOT EXISTS roles (name TEXT PRIMARY KEY, permissions TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,role TEXT NOT NULL REFERENCES roles(name),scope TEXT NOT NULL,status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS account_permissions (
    user_id TEXT NOT NULL REFERENCES users(id), permission TEXT NOT NULL, granted INTEGER NOT NULL CHECK(granted IN (0,1)),
    PRIMARY KEY(user_id,permission)
);
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id), first_name TEXT NOT NULL, last_name TEXT NOT NULL,
    phone TEXT NOT NULL, revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS credentials (user_id TEXT PRIMARY KEY REFERENCES users(id),salt BLOB NOT NULL,verifier BLOB NOT NULL,totp TEXT NOT NULL,last_step INTEGER NOT NULL DEFAULT -1);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS login_failures (key TEXT PRIMARY KEY,count INTEGER NOT NULL,since REAL NOT NULL);
CREATE TABLE IF NOT EXISTS grants (id TEXT PRIMARY KEY,actor TEXT NOT NULL,request TEXT NOT NULL,state TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS archives (sha TEXT PRIMARY KEY,name TEXT NOT NULL,contents BLOB NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS datasets (id TEXT PRIMARY KEY,title TEXT NOT NULL,version INTEGER NOT NULL,author TEXT NOT NULL,scope TEXT NOT NULL,state TEXT NOT NULL,created TEXT NOT NULL,sha TEXT NOT NULL REFERENCES archives(sha),previous TEXT REFERENCES datasets(id),payload TEXT NOT NULL,warning TEXT);
CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY,title TEXT NOT NULL,version INTEGER NOT NULL,author TEXT NOT NULL,scope TEXT NOT NULL,state TEXT NOT NULL,created TEXT NOT NULL,dataset_id TEXT NOT NULL REFERENCES datasets(id),kind TEXT NOT NULL,parameters TEXT NOT NULL,result TEXT NOT NULL,warning TEXT);
CREATE TABLE IF NOT EXISTS publications (id TEXT PRIMARY KEY,title TEXT NOT NULL,version INTEGER NOT NULL,author TEXT NOT NULL,scope TEXT NOT NULL,state TEXT NOT NULL,created TEXT NOT NULL,dataset_id TEXT NOT NULL REFERENCES datasets(id),analysis_id TEXT REFERENCES analyses(id),kind TEXT NOT NULL,payload TEXT NOT NULL,replaces TEXT REFERENCES publications(id),reviewer TEXT,approver TEXT,warning TEXT);
CREATE TABLE IF NOT EXISTS revisions (
    kind TEXT NOT NULL CHECK(kind IN ('analyses','publications')), parent TEXT NOT NULL, child TEXT NOT NULL,
    PRIMARY KEY(kind,parent), UNIQUE(kind,child)
);
CREATE INDEX IF NOT EXISTS ix_dataset_previous ON datasets(previous);
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY,author TEXT NOT NULL,scope TEXT NOT NULL,state TEXT NOT NULL,created TEXT NOT NULL,request TEXT NOT NULL,result_id TEXT REFERENCES analyses(id),error TEXT);
CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY,analysis_id TEXT NOT NULL REFERENCES analyses(id),author TEXT NOT NULL,scope TEXT NOT NULL,created TEXT NOT NULL,choice TEXT NOT NULL,reason TEXT NOT NULL,year INTEGER NOT NULL,classification TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY,id TEXT UNIQUE,actor TEXT NOT NULL,action TEXT NOT NULL,resource TEXT NOT NULL,scope TEXT NOT NULL,created TEXT NOT NULL,result TEXT NOT NULL,reason TEXT);
CREATE TRIGGER IF NOT EXISTS audit_immutable_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit immuable'); END;
CREATE TRIGGER IF NOT EXISTS audit_immutable_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit immuable'); END;
CREATE TRIGGER IF NOT EXISTS archive_immutable BEFORE UPDATE ON archives BEGIN SELECT RAISE(ABORT,'archive immuable'); END;
CREATE INDEX IF NOT EXISTS ix_sources ON datasets(sha);
CREATE INDEX IF NOT EXISTS ix_audit_events ON audit(resource,action,result,created);
CREATE INDEX IF NOT EXISTS ix_pub_state ON publications(state);
PRAGMA user_version=1;
"""

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def uid():
    return secrets.token_hex(12)

def dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",",":"), allow_nan=False)

class Error(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status

def check(condition,status,message):
    if not condition:
        raise Error(status,message)

def textfield(value,label="Valeur",limit=300):
    check(isinstance(value,str) and 0<len(value.strip())<=limit and "\x00" not in value,422,f"{label} invalide.")
    return value.strip()

def scope(value):
    check(isinstance(value,list) and 0<len(value)<=13 and all(isinstance(i,str) for i in value),422,"Périmètre invalide.")
    check(value==["*"] or set(value)<=REGIONS,422,"Région inconnue ou périmètre national ambigu.")
    return sorted(set(value))

def contains(granted,requested):
    return granted==["*"] or (requested!=["*"] and set(requested)<=set(granted))

def connect(state):
    path=Path(state)/"atlas.sqlite"
    db=sqlite3.connect(path,timeout=15)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

def initialize(state):
    directory=Path(state)
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    path=directory/"atlas.sqlite"
    if not path.exists():
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(descriptor)
    db=connect(state)
    check(db.execute("PRAGMA user_version").fetchone()[0] in (0,1),500,"Migration de base requise.")
    with db:
        db.executescript(SCHEMA)
        db.executemany("INSERT OR IGNORE INTO roles VALUES (?,?)",[(k,dump(v)) for k,v in ROLES.items()])
        admin_permissions=dump(ROLES["admin"])
        changed=db.execute("UPDATE roles SET permissions=? WHERE name='admin' AND permissions<>?",
                           (admin_permissions,admin_permissions))
        if changed.rowcount:
            db.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE role='admin')")
            audit(db,"system","role.update","admin",["*"],reason="Accès administrateur à toutes les fonctionnalités du catalogue.")
    db.close()

def audit(db,actor,action,resource="",area=(),result="ok",reason=None):
    db.execute("INSERT INTO audit(id,actor,action,resource,scope,created,result,reason) VALUES (?,?,?,?,?,?,?,?)",
               (uid(),actor,action,resource,dump(list(area)),now(),result,reason))

def user(db,user_id):
    row=db.execute("SELECT u.*,r.permissions FROM users u JOIN roles r ON u.role=r.name WHERE id=?",(user_id,)).fetchone()
    if not row:
        return None
    obj=dict(row)
    for k in ("permissions","scope"):
        obj[k]=json.loads(obj[k])
    overrides={r["permission"]:bool(r["granted"]) for r in db.execute(
        "SELECT permission,granted FROM account_permissions WHERE user_id=? ORDER BY permission",(user_id,))}
    effective=set(obj["permissions"])
    for key,granted in overrides.items():
        if granted:effective.add(key)
        else:effective.discard(key)
    obj["permissions"]=sorted(PERMISSIONS if obj["role"]=="admin" else effective & PERMISSIONS)
    obj["permission_overrides"]=overrides
    obj["access_version"]=hashlib.sha256(dump([obj["role"],obj["scope"],obj["permissions"],overrides]).encode()).hexdigest()
    obj["modules"]=modules_for(obj["permissions"])
    return obj

def require(u,*actions):
    check(u and u["status"]=="active",401,"Authentification requise.")
    check(any(action in u["permissions"] for action in actions),403,"Action non autorisée.")

def permit(u,sc):
    check(contains(u["scope"],sc),403,"Périmètre non autorisé.")

def password_verifier(password,salt):
    return hashlib.scrypt(password.encode(),salt=salt,n=2**15,r=8,p=1,maxmem=64*1024**2)

def credentials(db,user_id):
    password=secrets.token_urlsafe(20)
    salt=secrets.token_bytes(16)
    key=base64.b32encode(secrets.token_bytes(20)).decode()
    verifier=password_verifier(password,salt)
    db.execute("INSERT OR REPLACE INTO credentials VALUES(?,?,?,?,?)",(user_id,salt,verifier,key,-1))
    db.execute("DELETE FROM sessions WHERE user_id=?",(user_id,))
    return {"password":password,"totp_secret":key}

def new_account(db,username,role,regions):
    username=textfield(username,"Identifiant",80)
    regions=scope(regions)
    check(db.execute("SELECT 1 FROM roles WHERE name=?",(role,)).fetchone(),422,"Rôle inconnu.")
    check(not db.execute("SELECT 1 FROM users WHERE username=?",(username,)).fetchone(),409,"Identifiant déjà utilisé.")
    identifier=uid()
    db.execute("INSERT INTO users VALUES(?,?,?,?,?)",(identifier,username,role,dump(regions),"active"))
    return {**user(db,identifier),**credentials(db,identifier)}

def totp(secret,step=None):
    if step is None: step=int(time.time())//30
    digest=hmac.new(base64.b32decode(secret),struct.pack(">Q",step),hashlib.sha1).digest()
    number=struct.unpack(">I",digest[digest[-1]&15:(digest[-1]&15)+4])[0]&0x7fffffff
    return f"{number%1000000:06d}"

def check_attempts(db,key,limit,current):
    fail=db.execute("SELECT count,since FROM login_failures WHERE key=?",(key,)).fetchone()
    check(not fail or fail["since"]<current-300 or fail["count"]<limit,429,"Trop de tentatives. Réessayez dans cinq minutes.")

def record_failed_attempt(db,key,current):
    db.execute("INSERT INTO login_failures VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN since<? THEN 1 ELSE count+1 END,since=CASE WHEN since<? THEN excluded.since ELSE since END",(key,current,current-300,current-300))

def authenticate(db,data,client,*,require_totp=True):
    username=data.get("username")
    password=data.get("password")
    valid_input=isinstance(username,str) and 0<len(username)<=80 and isinstance(password,str) and 0<len(password)<=1024
    username=username[:80] if isinstance(username,str) else ""
    password=password[:1024] if isinstance(password,str) else ""
    otp=str(data.get("otp",""))
    current=time.time()
    keys=["ip:"+client,"account:"+username]
    for key,limit in zip(keys,(30,8)):
        check_attempts(db,key,limit,current)
    row=db.execute("SELECT c.*,u.status FROM credentials c JOIN users u ON u.id=c.user_id WHERE u.username=?",(username,)).fetchone()
    salt=row["salt"] if row else b"atlas:dummy:salt"
    verifier=password_verifier(password,salt)
    match=None
    if require_totp and row and otp.isascii() and len(otp)==6:
        step=int(current)//30
        match=next((n for n in [step-1,step,step+1] if n>row["last_step"] and secrets.compare_digest(totp(row["totp"],n),otp)),None)
    if not valid_input or not row or row["status"]!="active" or not hmac.compare_digest(verifier,row["verifier"]) or (require_totp and match is None):
        for key in keys:
            record_failed_attempt(db,key,current)
        audit(db,"anonymous","login","",result="refus")
        db.commit()
        raise Error(401,"Identifiants ou code temporaire invalides." if require_totp else "Identifiant ou mot de passe incorrect.")
    if match is not None:
        db.execute("UPDATE credentials SET last_step=? WHERE user_id=?",(match,row["user_id"]))
    db.execute("DELETE FROM login_failures WHERE key=?",(keys[1],))
    db.execute("DELETE FROM sessions WHERE expires<=?",(current,))
    token=secrets.token_urlsafe(36)
    csrf=secrets.token_urlsafe(32)
    db.execute("INSERT INTO sessions VALUES(?,?,?,?)",(token_hash(token),row["user_id"],csrf,current+8*3600))
    audit(db,row["user_id"],"login")
    return token, {"user":user(db,row["user_id"]),"csrf":csrf}

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def current_session(db,token):
    row=db.execute("SELECT * FROM sessions WHERE token=? AND expires>?",(token_hash(token),time.time())).fetchone()
    check(row,401,"Connectez-vous à l’espace de pilotage.")
    u=user(db,row["user_id"])
    check(u and u["status"]=="active",401,"Session révoquée.")
    return u,row["csrf"]
