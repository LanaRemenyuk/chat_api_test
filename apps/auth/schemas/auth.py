from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[datetime]

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str
