"""Coordonnées privées et accès du titulaire de la session."""
import hmac
import re
import secrets
import time

from .storage import Error, audit, check, check_attempts, password_verifier, record_failed_attempt, textfield


def read_profile(db, actor):
    row = db.execute("SELECT first_name,last_name,phone,revision FROM profiles WHERE user_id=?", (actor["id"],)).fetchone()
    details = dict(row) if row else {"first_name": "", "last_name": "", "phone": "", "revision": 0}
    return {"username": actor["username"], **details}


def save_details(db, actor, data):
    check(set(data) == {"first_name", "last_name", "phone", "revision"}, 422, "Champs de profil invalides.")
    values = []
    for field, label, limit in (("first_name", "Prénom", 100), ("last_name", "Nom", 100), ("phone", "Téléphone", 40)):
        value = data[field]
        check(isinstance(value, str), 422, f"{label} invalide.")
        value = value.strip()
        check(len(value) <= limit and all(c.isprintable() or c in "\u00a0\u202f" for c in value), 422, f"{label} invalide.")
        values.append(value)
    first_name, last_name, phone = values
    digits = re.sub(r"[\s().-]", "", phone)
    check(not phone or re.fullmatch(r"\+?[0-9]{7,15}", digits), 422, "Saisissez un numéro de 7 à 15 chiffres, avec un indicatif facultatif.")
    stored = read_profile(db, actor)
    check(type(data["revision"]) is int and data["revision"] == stored["revision"], 409,
          "Votre profil a été modifié dans une autre session. Rechargez la page avant de réessayer.")
    if (first_name, last_name, phone) != (stored["first_name"], stored["last_name"], stored["phone"]):
        db.execute("""INSERT INTO profiles(user_id,first_name,last_name,phone,revision) VALUES(?,?,?,?,1)
                      ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name,last_name=excluded.last_name,
                      phone=excluded.phone,revision=profiles.revision+1""", (actor["id"], first_name, last_name, phone))
        audit(db, actor["id"], "profile.update", actor["id"], actor["scope"])
    return read_profile(db, actor)


def change_login(db, actor, data):
    check(set(data) <= {"username", "current_password", "new_password", "confirmation"}, 422, "Champs de connexion invalides.")
    username = textfield(data.get("username", actor["username"]), "Identifiant", 80)
    current = data.get("current_password")
    check(isinstance(current, str) and 0 < len(current) <= 1024, 422, "Saisissez votre mot de passe actuel.")
    password = data.get("new_password", "")
    check(isinstance(password, str) and password == data.get("confirmation", ""), 422,
          "La confirmation du nouveau mot de passe ne correspond pas.")
    check(not password or 12 <= len(password) <= 1024 and password.strip(), 422,
          "Le nouveau mot de passe doit comporter entre 12 et 1 024 caractères.")
    check(username != actor["username"] or password, 422, "Modifiez l’identifiant ou saisissez un nouveau mot de passe.")
    key = "profile:" + actor["id"]
    now = time.time()
    check_attempts(db, key, 8, now)
    row = db.execute("SELECT salt,verifier FROM credentials WHERE user_id=?", (actor["id"],)).fetchone()
    if not row or not hmac.compare_digest(password_verifier(current, row["salt"]), row["verifier"]):
        record_failed_attempt(db, key, now)
        audit(db, actor["id"], "profile.login_change", actor["id"], actor["scope"], result="refus")
        db.commit()  # Conserver le compteur avant de renvoyer l’erreur au navigateur.
        raise Error(403, "Le mot de passe actuel est incorrect.")
    check(not password or password != current, 422, "Choisissez un mot de passe différent du mot de passe actuel.")
    if username != actor["username"]:
        check(not db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone(), 409, "Identifiant déjà utilisé.")
        db.execute("UPDATE users SET username=? WHERE id=?", (username, actor["id"]))
    if password:
        salt = secrets.token_bytes(16)
        db.execute("UPDATE credentials SET salt=?,verifier=? WHERE user_id=?",
                   (salt, password_verifier(password, salt), actor["id"]))
    db.execute("DELETE FROM login_failures WHERE key=?", (key,))
    db.execute("DELETE FROM sessions WHERE user_id=?", (actor["id"],))
    audit(db, actor["id"], "profile.login_change", actor["id"], actor["scope"])
    return {"username": username, "reauthenticate": True}
