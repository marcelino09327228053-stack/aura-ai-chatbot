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
from app.referrals import repository as referral_repository

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
class PricingSettings(BaseModel):
    monthly_platform_price_minor:int; initial_ai_credit_minor:int
    minimum_ai_topup_minor:int; referral_commission_minor:int
    ai_usage_markup_bps:int=0; currency:str="PHP"
class AgentDecision(BaseModel): status:str; notes:str=""
class AttributionCorrection(BaseModel): agent_id:int; reason:str
class PayoutCreate(BaseModel): agent_id:int; commission_ids:list[int]
class PayoutUpdate(BaseModel): status:str; payment_reference:str=""

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
            "provider_health":provider_health.snapshot(),"agents":[{"agent_type":a,"enabled":repository.agent_enabled(a)} for a in AGENT_TYPES],"audit":get_logs(None,50),
            "pricing":referral_repository.current_pricing(),"referral_agents":referral_repository.list_agents(),
            "attributions":referral_repository.list_attributions(),"commissions":referral_repository.list_commissions(),
            "payouts":referral_repository.list_payouts()}
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

@app.put("/owner/pricing")
def update_pricing(body:PricingSettings,_:None=Depends(require_owner)):
    values=body.model_dump()
    if any(values[k]<0 for k in ("monthly_platform_price_minor","initial_ai_credit_minor","minimum_ai_topup_minor","referral_commission_minor","ai_usage_markup_bps")):
        raise HTTPException(400,"Pricing values cannot be negative")
    if values["ai_usage_markup_bps"]>100000: raise HTTPException(400,"Markup is too large")
    if len(values["currency"].strip())!=3: raise HTTPException(400,"Use a three-letter currency")
    values["currency"]=values["currency"].upper()
    result=referral_repository.create_pricing_rule(values); record("owner.referral.pricing.updated"); return result

@app.put("/owner/referral-agents/{agent_id}")
def decide_agent(agent_id:int,body:AgentDecision,_:None=Depends(require_owner)):
    if body.status not in {"pending","approved","suspended","rejected"}: raise HTTPException(400,"Invalid agent status")
    result=referral_repository.set_agent_status(agent_id,body.status,body.notes)
    if not result: raise HTTPException(404,"Referral agent not found")
    record(f"owner.referral_agent.{body.status}:{agent_id}"); return result

@app.put("/owner/referral-attributions/{company_id}")
def correct_attribution(company_id:int,body:AttributionCorrection,_:None=Depends(require_owner)):
    if len(body.reason.strip())<5: raise HTTPException(400,"A correction reason is required")
    result=referral_repository.correct_attribution(company_id,body.agent_id,body.reason)
    if not result: raise HTTPException(404,"Attribution or approved agent not found")
    record(f"owner.referral.attribution.corrected:{company_id}:{body.agent_id}",company_id); return result

@app.post("/owner/referral-payouts",status_code=201)
def create_payout(body:PayoutCreate,_:None=Depends(require_owner)):
    try: result=referral_repository.create_payout(body.agent_id,body.commission_ids)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    record(f"owner.referral.payout.created:{result['id']}"); return result

@app.put("/owner/referral-payouts/{payout_id}")
def update_payout(payout_id:int,body:PayoutUpdate,_:None=Depends(require_owner)):
    if body.status not in {"pending","approved","paid","cancelled"}: raise HTTPException(400,"Invalid payout status")
    result=referral_repository.update_payout(payout_id,body.status,body.payment_reference)
    if not result: raise HTTPException(404,"Payout not found")
    record(f"owner.referral.payout.{body.status}:{payout_id}"); return result
