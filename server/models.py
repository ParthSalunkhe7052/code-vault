"""
Pydantic models for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# Authentication Models
# =============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# =============================================================================
# License Models
# =============================================================================

class LicenseValidationRequest(BaseModel):
    license_key: str = Field(..., min_length=5, max_length=50)
    hwid: str = Field(..., min_length=8, max_length=64)
    machine_name: Optional[str] = Field(None, max_length=255)
    nonce: str = Field(..., min_length=16, max_length=64)
    timestamp: int
    client_version: Optional[str] = None

class LicenseValidationResponse(BaseModel):
    status: str
    message: str = ""
    expires_at: Optional[int] = None
    features: List[str] = []
    client_nonce: str
    server_nonce: str
    timestamp: int
    signature: str

class LicenseCreateRequest(BaseModel):
    project_id: str
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    expires_at: Optional[datetime] = None
    max_machines: int = Field(default=1, ge=1, le=100)
    features: List[str] = []
    notes: Optional[str] = None


# =============================================================================
# Project Models
# =============================================================================

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    language: str = Field(default="python", pattern="^(python|nodejs)$")
    compiler_options: dict = {}

class ProjectConfigRequest(BaseModel):
    entry_file: Optional[str] = None
    output_name: Optional[str] = None
    include_modules: List[str] = []
    exclude_modules: List[str] = []
    nuitka_options: dict = {}
    compiler_options: dict = {}


# =============================================================================
# Compilation Models
# =============================================================================

class CompileJobRequest(BaseModel):
    entry_file: Optional[str] = None
    output_name: Optional[str] = None
    options: Optional[dict] = None
    license_key: Optional[str] = None

class CompileJobResponse(BaseModel):
    id: str
    project_id: str
    status: str
    progress: int
    output_filename: Optional[str]
    error_message: Optional[str]
    logs: List[str] = []
    started_at: Optional[Any]
    completed_at: Optional[Any]
    created_at: Any


# =============================================================================
# Webhook Models
# =============================================================================

class WebhookCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=10, max_length=500)
    events: List[str] = Field(default=["license.validated", "license.created"])
    secret: Optional[str] = None

class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=500)
    events: Optional[List[str]] = None
    secret: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


# =============================================================================
# Other Models
# =============================================================================

class HWIDResetRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
