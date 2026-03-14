from pydantic import BaseModel
from typing import Optional


class UserRegister(BaseModel):
    email: str
    password: str
    name: str


class UserLogin(BaseModel):
    email: str
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class ForgotPassword(BaseModel):
    email: str


class ResetPasswordToken(BaseModel):
    token: str
    new_password: str


class GoogleAuth(BaseModel):
    credential: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
