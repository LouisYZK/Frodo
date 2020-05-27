import traceback
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi_mako import FastAPIMako
import databases
import aiohttp
from config import DB_URL, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth')
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

mako = FastAPIMako()


db_engine = create_engine(
    DB_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
Base = declarative_base()

# AioDataBase = databases.Database(DB_URL.replace('+pymysql', ''))

class AioDataBase():
    async def __aenter__(self):
        db = databases.Database(DB_URL.replace('+pymysql', ''))
        await db.connect()
        self.db = db
        return db

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            traceback.print_exc()
        await self.db.disconnect()

GITHUB_OAUTH_URL = 'https://github.com/login/oauth/authorize'
GITHUB_ACCESS_URL = 'https://github.com/login/oauth/access_token'
GITHUB_API = 'https://api.github.com/user'

class GithubClient:
    
    def __init__(self, 
                 client_id=CLIENT_ID, 
                 client_secret=CLIENT_SECRET,
                 redirect_uri=REDIRECT_URI):
        self.client_id = client_id
        self.client_secret = client_secret
        
        self.auth_url = \
            f'{GITHUB_OAUTH_URL}?client_id={self.client_id}&redirect_uri={REDIRECT_URI}'

    async def get_access_token(self, code):
        async with aiohttp.ClientSession() as session:
            async with session.post(GITHUB_ACCESS_URL,
                                    headers={'accept': 'application/json'},
                                   params={'client_id': self.client_id, 
                                           'client_secret': self.client_secret,
                                           'code': code}) as resp:
                res = await resp.json()
                return res

    async def user_info(self, token):
        async with aiohttp.ClientSession() as session:
            async with session.get(GITHUB_API,
                                   headers={
                                       'accept': 'application/json',
                                       'Authorization': f'token {token}'
                                   }) as resp:
                return await resp.json()