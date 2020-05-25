import traceback
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi_mako import FastAPIMako
import databases
from config import DB_URL

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

