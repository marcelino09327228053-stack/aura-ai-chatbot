"""Authenticated customer endpoints for the human Marketing Agent program."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from io import BytesIO

from app.core.deps import require_auth
from app.infrastructure.audit import service as audit_service
from app.referrals import service

router = APIRouter(prefix="/referral-agent", tags=["referral-agent"])


@router.get("/me")
def my_agent_dashboard(request: Request, ctx=Depends(require_auth)):
    return service.public_dashboard(ctx.user_id, str(request.base_url))


@router.post("/apply", status_code=201)
def apply(ctx=Depends(require_auth)):
    result = service.apply(ctx.user_id)
    audit_service.record("referral_agent.application", ctx.company_id, ctx.user_id)
    return result


@router.post("/application")
async def submit_application(full_name:str=Form(...),email:str=Form(...),mobile_number:str=Form(...),
    address_location:str=Form(...),id_type:str=Form(...),id_reference:str=Form(""),
    payout_method:str=Form(...),account_holder_name:str=Form(...),account_number:str=Form(...),
    bank_name:str=Form(""),identity_document:UploadFile=File(...),ctx=Depends(require_auth)):
    content=await identity_document.read(service.MAX_ID_BYTES+1)
    values={"full_name":full_name,"email":email,"mobile_number":mobile_number,
      "address_location":address_location,"id_type":id_type,"id_reference":id_reference,
      "payout_method":payout_method,"account_holder_name":account_holder_name,
      "account_number":account_number,"bank_name":bank_name}
    result=service.submit_application(ctx.user_id,values,{"filename":identity_document.filename or "",
      "content_type":identity_document.content_type or "","content":content})
    audit_service.record("referral_agent.application_submitted",ctx.company_id,ctx.user_id)
    return {"agent":result}


@router.get("/identity-document")
def own_identity_document(ctx=Depends(require_auth)):
    path,content_type,filename=service.own_document(ctx.user_id)
    return FileResponse(path,media_type=content_type,filename=filename,headers={"Cache-Control":"no-store"})


@router.post("/profile")
async def update_profile(full_name: str = Form(...), mobile_number: str = Form(""),
    address_location: str = Form(""), profile_bio: str = Form(""),
    profile_picture: UploadFile | None = File(None), ctx=Depends(require_auth)):
    upload = None
    if profile_picture and profile_picture.filename:
        content = await profile_picture.read(service.MAX_PROFILE_BYTES + 1)
        upload = {"content_type": profile_picture.content_type or "", "content": content}
    result = service.update_profile(ctx.user_id, {
        "full_name": full_name, "mobile_number": mobile_number,
        "address_location": address_location, "profile_bio": profile_bio,
    }, upload)
    audit_service.record("referral_agent.profile_updated", ctx.company_id, ctx.user_id)
    return {"agent": result}


@router.get("/profile-photo")
def profile_photo(ctx=Depends(require_auth)):
    path, content_type = service.own_profile_photo(ctx.user_id)
    return FileResponse(path, media_type=content_type, headers={"Cache-Control": "private, max-age=300"})


@router.post("/payout-request",status_code=201)
def request_payout(ctx=Depends(require_auth)):
    try:result=service.repository.request_payout(ctx.user_id)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    audit_service.record("referral_agent.payout_requested",ctx.company_id,ctx.user_id)
    return result


@router.get("/qr")
def referral_qr(request:Request,ctx=Depends(require_auth)):
    data=service.public_dashboard(ctx.user_id,str(request.base_url))
    if not data.get("agent") or data["agent"]["status"]!="approved":
        raise HTTPException(403,"An approved agent account is required.")
    import qrcode
    image=qrcode.make(data["referral_link"]);buffer=BytesIO();image.save(buffer,format="PNG");buffer.seek(0)
    return StreamingResponse(buffer,media_type="image/png",headers={"Cache-Control":"no-store"})
