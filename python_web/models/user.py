from datetime import timedelta, datetime
import jwt
from jwt import PyJWTError
from typing import List
from fastapi import Depends, status, HTTPException
from sqlalchemy import Column, String, Text, Boolean, Integer
from sqlalchemy.orm import Session
from models.base import BaseModel
from ext import pwd_context, oauth2_scheme
from models import schemas
import config

def verify_password(plain_pwd, hashed_pwd):
    return pwd_context.verify(plain_pwd, hashed_pwd)

def get_pwd_hash(pwd):
    return pwd_context.hash(pwd)

class User(BaseModel):
    email = Column(String(length=100))
    name = Column(String(length=100), unique=True)
    avatar = Column(String(length=100), default='')
    password = Column(Text())
    active = Column(Boolean(), default=True)


async def create_user(**data):
    if 'name' not in data or 'password' not in data:
        raise ValueError('username or password are required.')
    data['password'] = get_pwd_hash(data.pop('password'))
    rv = await User.acreate(**data)
    data.pop('password')
    data.update(id=rv)
    return schemas.User(**data)
    
async def authenticate_user(
        username: str, password: str) -> schemas.User:
    user = await User.async_first(name=username)
    user = schemas.UserAuth(**user)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

async def create_access_token(*, data: dict, expires_delta: timedelta=None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, 
                             algorithm=config.JWT_ALGORITHM)
    return encoded_jwt


async def modify_user(user: schemas.UserUpdate):
    user.password = get_pwd_hash(user.password)
    rv = await User.asave(**dict(user))

async def search_user_by_name(name: str) -> List[schemas.User]:
    users = await User.async_all()
    res = []
    for item in users:
        u = schemas.User(**item)
        if name in u.name: res.append(u)
    return res


async def get_current_user(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        playload = jwt.decode(token, config.JWT_SECRET, algorithms=config.JWT_ALGORITHM)
        username: str = playload.get('username')
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
    user = await User.async_first(name=token_data.username)
    user = schemas.User(**user)
    if user is None:
        raise credentials_exception
    return user

class GithubUser(BaseModel):
    gid = Column(Integer(), unique=True)
    email = Column(String(100), default='', unique=True)
    username = Column(String(100), unique=True)
    picture = Column(String(100), default='')
    link = Column(String(100), default='')


async def create_github_user(user_info):
    user = await GithubUser.async_first(gid=user_info['id'])
    kwargs = {
        'gid': user_info.get('id'),
        'link': user_info.get('html_url', ''),
        'picture': user_info.get('avatar_url', ''),
        'username': user_info.get('login', ''),
        'email': user_info.get('email') if user_info.get('email') is not None else ''
    }
    if user:
        id = user.get('id')
        await GithubUser.asave(id=id, **kwargs)
    else:
        await GithubUser.acreate(**kwargs)
    # return await GithubUser(**kwargs).to_async_dict(**kwargs)
    return kwargs


if __name__ == "__main__":
    import sys
    print('test')     