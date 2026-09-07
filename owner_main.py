"""Private MB Future Tech Owner Console (run separately on port 9000)."""
import ipaddress, os
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.config import AGENT_TYPES
from app.database.connection import init_db
from app.infrastructure.audit.service import get_logs, record
from app.owner import repository
from app.owner.security import create_session, require_owner, verify_login
from app.services import ai_service
from app.services.ai_provider_router import provider_health

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
init_db(); repository.init_owner_schema()

@app.middleware("http")
async def private_network_only(request:Request,call_next):
    host=request.client.host if request.client else ""
    allowed=os.getenv("OWNER_ALLOWED_NETWORKS","127.0.0.0/8,::1/128,100.64.0.0/10").split(",")
    try: permitted=any(ipaddress.ip_address(host) in ipaddress.ip_network(net.strip()) for net in allowed if net.strip())
    except ValueError: permitted=False
    if not permitted: return Response("Private Owner Console",status_code=403)
    return await call_next(request)

class Login(BaseModel): email:str; password:str; code:str=""
class ProviderKey(BaseModel): api_key:str
class AgentControl(BaseModel): enabled:bool
class ProviderTest(BaseModel): confirm_billable:bool=False

@app.get("/")
def page(): return FileResponse("owner-console.html")
@app.get("/owner/auth-config")
def auth_config():
    return {"mfa_required":os.getenv("OWNER_MFA_REQUIRED","true").lower() not in {"false","0","no"}}
@app.post("/owner/login")
def login(body:Login,response:Response):
    verify_login(body.email,body.password,body.code); token=create_session()
    response.set_cookie("owner_session",token,httponly=True,samesite="strict",secure=os.getenv("OWNER_COOKIE_SECURE","false").lower()=="true",max_age=1800)
    record("owner.login"); return {"ok":True}
@app.post("/owner/logout")
def logout(response:Response): response.delete_cookie("owner_session"); return {"ok":True}
@app.get("/owner/dashboard")
def dashboard(_:None=Depends(require_owner)):
    return {"overview":repository.overview(),"subscribers":repository.subscribers(),"providers":repository.list_providers(),
            "provider_health":provider_health.snapshot(),"agents":[{"agent_type":a,"enabled":repository.agent_enabled(a)} for a in AGENT_TYPES],"audit":get_logs(None,50)}
@app.post("/owner/providers/{provider}")
def save_provider(provider:str,body:ProviderKey,_:None=Depends(require_owner)):
    if provider not in ai_service.PROVIDERS: raise HTTPException(404,"Unknown provider")
    key=body.api_key.strip()
    if len(key)<12: raise HTTPException(400,"Invalid API key")
    repository.save_provider_key(provider,key); record(f"owner.provider.updated:{provider}"); return {"saved":True,"suffix":key[-4:]}
@app.post("/owner/providers/{provider}/test")
def test_provider(provider:str,body:ProviderTest,_:None=Depends(require_owner)):
    if not body.confirm_billable: raise HTTPException(400,"Billable test confirmation required")
    if provider not in ai_service.PROVIDERS: raise HTTPException(404,"Unknown provider")
    answer=ai_service.generate_reply("Reply with exactly: OK",provider,ai_service.get_server_model(provider))
    record(f"owner.provider.tested:{provider}")
    return {"ok":True,"input_tokens":int(getattr(answer,"input_tokens",0) or 0),"output_tokens":int(getattr(answer,"output_tokens",0) or 0)}
@app.delete("/owner/providers/{provider}")
def delete_provider(provider:str,_:None=Depends(require_owner)):
    repository.delete_provider_key(provider); record(f"owner.provider.deleted:{provider}"); return {"deleted":True}
@app.put("/owner/agents/{agent_type}")
def agent_control(agent_type:str,body:AgentControl,_:None=Depends(require_owner)):
    if agent_type not in AGENT_TYPES: raise HTTPException(404,"Unknown agent")
    repository.set_agent(agent_type,body.enabled); record(f"owner.agent.{agent_type}:{body.enabled}"); return {"agent_type":agent_type,"enabled":body.enabled}
