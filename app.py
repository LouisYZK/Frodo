import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from enum import Enum
from typing import List, Optional
import databases
from ext import mako, SessionLocal, Base, db_engine, AioDataBase
from models import model, schemas, var
from views import crud, users, admin
import config

app = FastAPI()

app.__name__ = 'fast_blog'

mako.init_app(app)

model.Base.metadata.create_all(bind=db_engine)

aio_database = AioDataBase


class ModelName(str, Enum):
    alexnet = 'alexnet'
    resnet = 'resnet'
    lenet = 'lenet'

class UserAuth(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

def fake_decode_token(token):
    return UserAuth(
        username=token + "fakedecoded",
        email='xsxsxs@com',
        full_name='Josnh',
    )
# async def get_current_user(token: str=Depends(oauth2_scheme)):
#     user = fake_decode_token(token)
#     return user

test_item = {
    'name': "test",
    "price": 11
}

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


async def common_params(skip: int=0, limit: int = 100):
    return {'skip': skip, 'limit': limit}


@app.get('/items/{item_id}')
def read_item(item_id: int, q: str=None):
    return {"item_id": item_id, "q": q}

@app.get('/items/')
def read_q(item_name: str):
    pass

@app.put('/items/{item_id}')
def update_item(item_id: int, item: schemas.Item):
    return {"item_name": item.name, "item_id": item_id}


@app.post('/api/users/', response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session=Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already exists')
    return crud.create_user(db=db, user=user)

@app.get('/api/users/{user_id}', response_model=schemas.User)
def read_user(user_id: int, db: Session=Depends(get_db)):
    db_user = crud.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail='No such user')
    return db_user

# @app.get('/api/users', response_model=List[schemas.User])
# def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     users = crud.get_users(db=db, skip=skip, limit=limit)
#     return users
@app.get('/api/users', response_model=List[schemas.User], name='users')
def read_users(com_p: dict=Depends(common_params), db: Session = Depends(get_db)):
    users = crud.get_users(db=db, skip=com_p['skip'], limit=com_p['limit'])
    return users

@app.post('/api/{user_id}/items/', response_model=schemas.Item)
def create_item_for_user(
    user_id: int, item: schemas.ItemCreate, db: Session=Depends(get_db)
):
    return crud.create_user_item(db=db, item=item, user_id=user_id)

@app.get('/api/items', response_model=List[schemas.Item]) 
def read_items(skip: int=0, limit: int=100, db: Session=Depends(get_db)):
    items = crud.get_items(db=db, skip=skip, limit=limit)
    return items



@app.get('/model/{model_name}')
async def get_model(model_name: ModelName):
    if model_name == ModelName.alexnet:
        return {"model_name": model_name}
    if model_name.value == 'lenet':
        return {"model_name": model_name}


@app.get('/', response_class=HTMLResponse)
@mako.template('index.html')
def index(request: Request):
    setattr(request, 'mako', 'test')
    return {'title': 'Yurs'}

@app.get('/async_index', response_class=HTMLResponse)
@mako.template('index.html')
async def async_index(request: Request):
    setattr(request, 'mako', 'test')
    return {'title': 'Yurs'}


@app.on_event("startup")
async def startup():
    global aio_database
    await aio_database.connect()


@app.on_event("shutdown")
async def shutdown():
    global aio_database
    await aio_database.disconnect()

@app.middleware('http')
async def set_context(req: Request, call_next):
    global aio_database
    if aio_database is None:
        print('aio database is NOne...')
    else:
        var.aio_databases.set(aio_database)
    response = await call_next(req)
    return response

async def custome_middware(req: Request, call_next):
    print('In custome middleware...')
    response = await call_next(req)
    return response

# @app.get('/api/users/me')
# async def read_users_me(current_user: UserAuth=Depends(get_current_user)):
#     return current_user

app.include_router(
    users.router,
    prefix='/api/async_users'
)

print(app.url_path_for('users'))
# app['some_key'] = 'ax'
setattr(app, 'some_key', 'aa')



app.user_middleware.append(custome_middware)
print(app.user_middleware)
app.__name__ = 'fast_blog'
print(app.__name__)
setattr(app, 'config', config)