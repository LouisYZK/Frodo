from fastapi import Form
from pydantic import BaseModel

class UserCreateForm(BaseModel):
    active: bool = Form(...)
    name: str = Form(...)
    email: str = Form(...)
    password: str = Form(...)
    avatar: str = Form(...)