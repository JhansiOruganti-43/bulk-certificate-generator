from pydantic import BaseModel, EmailStr
from typing import Optional

class StudentCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class StudentRead(BaseModel):
    id: str
    full_name: str
    email: EmailStr

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
