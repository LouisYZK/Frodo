import asyncio
import aioredis
from fastapi import Depends
from typing import List, Union
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, and_
from sqlalchemy.orm import Session
from sqlalchemy.engine.result import RowProxy
from sqlalchemy.ext.declarative import as_declarative, declared_attr, DeclarativeMeta
import inspect
from typing import Any
import config
from ext import SessionLocal, AioDataBase
from .var import aio_databases, redis_var
from .mc import cache, clear_mc

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        try:
            redis = redis_var.get()
        except LookupError:
            # Hack for debug mode
            loop = asyncio.get_event_loop()
            redis = await aioredis.create_redis_pool(
                config.REDIS_URL, minsize=5, maxsize=20, loop=loop)
        _redis = redis
    return _redis

IGNORE_ATTRS = ['redis', 'stats']
MC_KEY_ITEM_BY_ID = '%s:%s'


class PropertyHolder(type):
    """
    We want to make our class with som useful properties 
    and filter the private properties.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        new_cls.property_fields = []

        for attr in list(attrs) + sum([list(vars(base))
                                       for base in bases], []):
            if attr.startswith('_') or attr in IGNORE_ATTRS:
                continue
            if isinstance(getattr(new_cls, attr), property):
                new_cls.property_fields.append(attr)
        return new_cls

@as_declarative()
class Base():
    __name__: str
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @property
    def url(self):
        return f'/{self.__class__.__name__.lower()}/{self.id}/'

    @property
    def canonical_url(self):
        pass


class ModelMeta(Base.__class__, PropertyHolder):
    ...


class BaseModel(Base, metaclass=ModelMeta):
    """
        Sqlalchemy is unable to support asynchronous, we
        have to use `databases` to excute sql in async, which
        is inrevelent to `Base` model. However we can implement
        both sync and async version.
    """

    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime)
        
    @classmethod
    def to_dict(cls, 
                results: Union[RowProxy, List[RowProxy]]) -> Union[List[dict], dict]:
        if not isinstance(results, list):
            return {col: val for col, val in zip(results.keys(), results)}
        list_dct = []
        for row in results:
            dct = {col: val for col, val in zip(row.keys(), row)}
            list_dct.append(dct)
        return list_dct
    
    async def to_async_dict(self, **data):
        """some coroutine properties like `post.html_content`
        we have to use it like `await post.html_content`
        however if we use it in Mako template, we have 
        to process it into the obj can use point access.
        """
        rv = { key: value for key, value in data.items() }
        for field in self.property_fields:
            coro = getattr(self, field)
            if inspect.iscoroutine(coro):
                rv[field] = await coro
            else:
                rv[field] = coro
        rv['url'] = self.url
        return config.AttrDict(rv)

    @classmethod
    async def async_get(cls, *args, **kwargs):
        pass
    
    @classmethod
    async def async_first(cls, *args, **kwargs):
        table = cls.__table__
        filters = []
        limit = kwargs.pop('limit', '')
        offset = kwargs.pop('offset', '')
        for key, val in kwargs.items():
            filters.append(getattr(table.c, key) == val)
        async with AioDataBase() as db:
            if len(filters) > 1: 
                query = table.select().where(and_(*filters))
            else:
                query = table.select().where(*filters)
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(limit)
            try:
                res = await db.fetch_one(query)
            except:
                raise 
        if not res: return {}
        return cls.to_dict(res)

    @classmethod
    async def async_filter(cls, *args, **kwargs):
        table = cls.__table__
        filters = []
        for key, val in kwargs.items():
            filters.append(getattr(table.c, key) == val)
        async with AioDataBase() as db:
            if len(filters) > 1:
                query = table.select().where(and_(*filters))
            else:
                query = table.select().where(*filters)
            try:
                res = await db.fetch_all(query)
            except:
                raise 
        return cls.to_dict(res)

    @classmethod
    async def async_in(cls, col, values=[]):
        """select * from base where col in values;
        """    
        table = cls.__table__
        col_schema = getattr(table.c, col)
        in_func = getattr(col_schema, 'in_')
        query = table.select().where(in_func(values))
        async with AioDataBase() as db:
            res = await db.fetch_all(query)
        return cls.to_dict(res)
                

    @classmethod
    async def async_all(cls, *args, **kwargs):
        table = cls.__table__
        limit = kwargs.pop('limit', '')
        offset = kwargs.pop('offset', '')
        async with AioDataBase() as db:
            query = table.select()
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            res = await db.fetch_all(query)
        return cls.to_dict(res)
        

    @classmethod
    async def acreate(cls, **kwargs):
        table = cls.__table__
        query = table.insert()
        async with AioDataBase() as db:
            rv = await db.execute(query=query, values=kwargs)
        obj = cls(**(await cls.async_first(id=rv)))
        await cls.__flush__(obj)
        return rv

    @classmethod
    async def adelete(cls, **kwargs):
        table = cls.__table__
        filters = []
        obj = cls(**(await cls.async_first(**kwargs)))
        for key, val in kwargs.items():
            filters.append(getattr(table.c, key) == val)
        async with AioDataBase() as db:
            if len(filters) > 1:
                query = table.delete().where(and_(*filters))
            else:
                query = table.delete().where(*filters)
            rv = await db.execute(query=query)
        await cls.__flush__(obj)
        return rv

    @classmethod
    async def asave(cls, *args, **kwargs):
        '''  update  '''
        table = cls.__table__
        id = kwargs.pop('id')
        async with AioDataBase() as db:
            query = table.update().\
                          where(table.c.id==id).\
                          values(**kwargs)
            rv = await db.execute(query=query)
        obj = cls(**(await cls.async_first(id=id)))
        await cls.__flush__(obj)
        return rv

    @classmethod
    async def get_or_create(cls, **kwargs):
        table = cls.__table__
        if 'id' not in kwargs:
            rv = await cls.async_first(**kwargs)
        else:
            rv = await cls.cache(**kwargs)
        if not rv:
            rv = await cls.acreate(**kwargs)
            return rv
        else:
            return rv

    @classmethod
    async def sync_first(cls, *args, **kwargs):
        pass

    @classmethod
    async def sync_filter(cls, *args, **kwargs):
        pass

    @classmethod
    async def sync_all(cls, *args, **kwargs):
        pass

    def sync_create(self, db: Session):
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    def sync_delete(self):
        pass

    def sync_save(self, *args, **kwargs):
        pass

    def get_db_key(self, key):
        return f'{self.__class__.__name__}/{self.id}/props/{key}'
    
    @property
    async def redis(self):
        return await get_redis()

    async def set_props_by_key(self, key, value):
        key = self.get_db_key(key)
        return await (await self.redis).set(key, value)

    async def get_props_by_key(self, key):
        key = self.get_db_key(key)
        return await (await self.redis).get(key) or b''

    @classmethod
    @cache(MC_KEY_ITEM_BY_ID % ('{cls.__name__}', '{id}'))
    async def cache(cls, **kwargs):
        data = await cls.async_first(**kwargs)
        return data

    @classmethod
    async def __flush__(cls, target):
        await asyncio.gather(
            clear_mc(MC_KEY_ITEM_BY_ID % (target.__class__.__name__, target.id)),
            target.clear_mc(), return_exceptions=True
        )
    
    async def clear_mc(self):
        """In case that som obj dont have clear_mc
        """
        ...

    @classmethod
    async def get_multi(cls, ids):
        return [await cls.cache(id=id) for id in ids]

    

if __name__ == '__main__':
    pass
    # b = Base()
    # print(b.url)
    # print(dir(b.metadata))
    # print(b.metadata.tables)
    # print(Base.__class__)
