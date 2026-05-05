"""Auth-related request/response schemas."""

from pydantic import BaseModel


class GoogleAuthRequest(BaseModel):
    """Request body for POST /auth/google."""
    id_token: str


class TokenResponse(BaseModel):
    """Response after successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshRequest(BaseModel):
    """Request body for POST /auth/refresh."""
    refresh_token: str


class UserResponse(BaseModel):
    """Public user representation."""
    id: str
    email: str
    display_name: str
    photo_url: str | None = None
    role: str

    model_config = {"from_attributes": True}
