from typing import List, Any
from pydantic import BaseModel


class UserBase(BaseModel):
    name: str

class UserAuth(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(UserAuth):
    email: str = None
    avatar: str = None

class UserDelete(BaseModel):
    id: int

class User(UserBase):
    id: int
    email: str = None
    avatar: str = None
    active: bool = None

class UserUpdate(User):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenData(BaseModel):
    username: str = None


class Post(BaseModel):
    id: int
    title: str
    slug: str
    summary: str = None
    content: str
    can_comment: bool
    author_id: int
    type: int
    status: int

class Tag(BaseModel):
    id: str
    name: str

class TagFrontEnd(Tag):
    url: str    


class CommonResponse(BaseModel):
    items: List[Any]
    total: int

if __name__ == '__main__':
    user = {
        'id': 0,
        'username': 'xsxs',
        'password': 'aaa',
    }
    u = User(**user)
    print(u.username)