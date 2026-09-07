"""Independent Owner Console authentication with password and TOTP MFA."""
import base64, hashlib, hmac, os, struct, time
import bcrypt, jwt
from fastapi import HTTPException, Request

def _totp(secret: str, counter: int) -> str:
    key=base64.b32decode(secret.upper()+"="*((8-len(secret)%8)%8))
    digest=hmac.new(key,struct.pack(">Q",counter),hashlib.sha1).digest(); offset=digest[-1]&15
    return str((struct.unpack(">I",digest[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)

def verify_totp(code: str) -> bool:
    secret=os.getenv("OWNER_TOTP_SECRET","").replace(" ","").strip()
    if not secret: return False
    now=int(time.time())//30
    try: return any(hmac.compare_digest(str(code).zfill(6),_totp(secret,now+step)) for step in (-1,0,1))
    except (ValueError,TypeError): return False

def verify_login(email: str, password: str, code: str) -> None:
    configured_email=os.getenv("OWNER_EMAIL","").strip().casefold()
    email_ok=bool(configured_email) and hmac.compare_digest(email.strip().casefold(),configured_email)
    stored=os.getenv("OWNER_PASSWORD_HASH","").encode()
    try: password_ok=bool(stored) and bcrypt.checkpw(password.encode(),stored)
    except (ValueError,TypeError): password_ok=False
    if not email_ok or not password_ok or not verify_totp(code):
        raise HTTPException(status_code=401,detail="Invalid owner credentials or MFA code.")

def create_session() -> str:
    secret=os.getenv("OWNER_CONSOLE_SECRET","")
    if len(secret)<32: raise HTTPException(status_code=503,detail="Owner Console secret is not configured.")
    return jwt.encode({"sub":"owner","exp":int(time.time())+1800},secret,algorithm="HS256")

def require_owner(request: Request) -> None:
    token=request.cookies.get("owner_session","")
    try: payload=jwt.decode(token,os.getenv("OWNER_CONSOLE_SECRET",""),algorithms=["HS256"])
    except jwt.PyJWTError as exc: raise HTTPException(status_code=401,detail="Owner login required.") from exc
    if payload.get("sub")!="owner": raise HTTPException(status_code=401,detail="Owner login required.")
