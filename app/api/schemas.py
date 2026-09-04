"""Pydantic models for API request/response bodies."""

from pydantic import BaseModel, EmailStr


class Message(BaseModel):
    text: str
    companyProfile: str = ""
    voiceType: str = "female"
    language: str = "filipino"
    session_id: str | None = None
    agent_type: str | None = None
    providers: list[str] | None = None
    mode: str | None = None
    request_id: str | None = None


class FaqCreate(BaseModel):
    question: str
    answer: str


class FaqUpdate(BaseModel):
    question: str
    answer: str


class GenerateFaqRequest(BaseModel):
    companyProfile: str = ""


class CompanyProfileReviewRequest(BaseModel):
    draft_profile: str = ""


class CompanyProfileTestRequest(BaseModel):
    profile: str = ""
    question: str = ""


class CompanyProfileWebsiteImportRequest(BaseModel):
    url: str


class AIResponseStyleRequest(BaseModel):
    style: str = "professional"
    custom_instructions: str = ""


class CompanyProfileRestoreRequest(BaseModel):
    version_id: int


class CompanyProfileVersionUpdateRequest(BaseModel):
    version_name: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RequestLoginCodeRequest(BaseModel):
    email: EmailStr


class VerifyLoginCodeRequest(BaseModel):
    email: EmailStr
    code: str
    company_name: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class CompanyCreateRequest(BaseModel):
    company_name: str


class CompanyUpdateRequest(BaseModel):
    company_name: str | None = None
    company_profile: str | None = None
    company_profile_source: str | None = None


class SelectCompanyRequest(BaseModel):
    company_id: int


class SubscriptionUpdateRequest(BaseModel):
    plan: str


class MockPaymentEventRequest(BaseModel):
    event_id: str
    plan: str = "test"
    status: str = "succeeded"


class LoadTestRequest(BaseModel):
    requests: int = 100
    customers: int = 10
    service_ms: float = 10
    global_limit: int = 20
    customer_limit: int = 2


class LiveProviderTestRequest(BaseModel):
    confirm_billable: bool = False


class AIProviderConnectRequest(BaseModel):
    api_key: str


class AIProviderModelRequest(BaseModel):
    model: str


class FacebookConnectRequest(BaseModel):
    page_access_token: str
    app_secret: str


class AccountUpdateRequest(BaseModel):
    full_name: str


class EmailChangeRequest(BaseModel):
    new_email: EmailStr


class EmailChangeVerifyRequest(BaseModel):
    new_email: EmailStr
    code: str
