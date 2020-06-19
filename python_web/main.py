import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import typing
from typing import Optional
from models import Base, schemas, user
from models.activity import create_activity_after_post_created
from views import admin, index, blog, comment, activity
from ext import mako, oauth2_scheme, db_engine
import config



app = FastAPI()
app.__name__ = 'fast_blog'
mako.init_app(app)

target_metadata = Base.metadata
target_metadata.create_all(db_engine)

app.mount('/static/', 'static', name='static')
app.add_middleware(SessionMiddleware, secret_key='fast')
app.include_router(
    admin.router,
    prefix='/api'
)
app.include_router(index.router)
app.include_router(blog.router)
app.include_router(comment.router, prefix='/j')
app.include_router(activity.router, prefix='/j')

@app.get('/admin')
@mako.template('admin.html')
async def admin(request: Request):
    return {}


@app.middleware('http')
async def process_auth(req: Request, call_next):
    """ modfiy the request body of authentication """
    req.scope["root_path"] = config.HOST_PATH
    h_copy = req.headers.mutablecopy()
    h_copy["host"] = ''
    req.scope["headers"] = h_copy.raw  
    if req.scope['path'] == '/' or 'page' in req.scope['path']:
        req.state.partials = config.partials
        response = await call_next(req)
    else:
        
        response = await call_next(req)
    return response

@app.post("/api/activity")
async def add_post_activity(request: Request):
    """ Server for Golang admin to Create Activity
    """
    body = await request.json()
    post_id = body["post_id"]
    user_id = body["user_id"]
    await create_activity_after_post_created(post_id, user_id)
    return {"status": "ok"}


# @app.post('/auth')
# async def login(req: Request, username: str=Form(...), password: str=Form(...)):
#     user_auth: schemas.User = \
#             await user.authenticate_user(username, password)
#             # await user.authenticate_user(user_data.username, user_data.password) 
#     if not user_auth:
#         raise HTTPException(status_code=400, 
#                             detail='Incorrect User Auth.')
#     access_token_expires = timedelta(
#         minutes=int(config.ACCESS_TOKEN_EXPIRE_MINUTES)
#     )
#     access_token = await user.create_access_token(
#                         data={'sub': user_auth.name},
#                         expires_delta=access_token_expires)
#     return {
#         'access_token': access_token,
#         'refresh_token': access_token,
#         'token_type': 'bearer'
#     }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(config.WEB_PORT))

