import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.middleware.sessions import SessionMiddleware
import typing
from typing import Optional
from models import schemas, user
from views import admin, index, blog, comment
from ext import mako, oauth2_scheme
import config


app = FastAPI()
app.__name__ = 'fast_blog'
mako.init_app(app)


app.mount('/static/', StaticFiles(directory='static'), name='static')
app.add_middleware(SessionMiddleware, secret_key='fast')
app.include_router(
    admin.router,
    prefix='/api'
)
app.include_router(index.router)
app.include_router(blog.router)
app.include_router(comment.router, prefix='/j')

@app.get('/admin')
@mako.template('admin.html')
async def admin(request: Request):
    return {}


@app.middleware('http')
async def process_auth(req: Request, call_next):
    """ modfiy the request body of authentication """
    if str(req.url).endswith('/auth') and req.headers['referer'].endswith('admin'):
        new_header = req.headers.mutablecopy()
        new_header['content-type'] = 'application/x-www-form-urlencoded'
        req.scope['headers'] = new_header.raw
        recv = await req.receive()
        async def custome_recv():
            body_dct = json.loads(recv['body'].decode())
            recv['body'] = f"username={body_dct['username']}&password={body_dct['password']}".encode()
            return recv
        new_req = Request(req.scope, custome_recv)
        response = await call_next(new_req)
    elif req.scope['path'] == '/' or 'page' in req.scope['path']:
        req.state.partials = config.partials
        response = await call_next(req)
    else:
        response = await call_next(req)
    return response


@app.post('/auth')
async def login(req: Request, username: str=Form(...), password: str=Form(...)):
    user_auth: schemas.User = \
            await user.authenticate_user(username, password)
            # await user.authenticate_user(user_data.username, user_data.password) 
    if not user_auth:
        raise HTTPException(status_code=400, 
                            detail='Incorrect User Auth.')
    access_token_expires = timedelta(
        minutes=int(config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    access_token = await user.create_access_token(
                        data={'sub': user_auth.name},
                        expires_delta=access_token_expires)
    return {
        'access_token': access_token,
        'refresh_token': access_token,
        'token_type': 'bearer'
    }

