from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str
    hashed_password: str
    role: str

class UserPublic(UserBase):
    id: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class ActionLog(BaseModel):
    id: str
    user_id: str
    action: str
    object_type: str
    object_id: str
    timestamp: str
