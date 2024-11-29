from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[datetime]

    class Config:
        json_schema_extra = {
            "example": {
                "sub": "user123",
                "exp": "2024-12-31T23:59:59Z"
            }
        }


class LoginRequest(BaseModel):
    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "password123"
            }
        }


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiaWF0IjoxNjI5MjMyMzY5LCJleHBpcmVkIjp0cnVlfQ.v-HiJMQZOrQhQ1bKgm_tQ5SZ4_zj2HCBRY4qCZg-r6M"  # Example JWT token
            }
        }

