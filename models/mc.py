import re
import inspect
import asyncio
from functools import wraps
from pickle import dumps, loads

import aioredis

from .utils import Empty
from .var import redis_var
import config

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

def gen_key_factory(key_pattern: str, arg_names: list, kwonlydefaults: dict):
    def gen_key(*args, **kwargs):
        kw = kwonlydefaults.copy() if kwonlydefaults is not None else {}
        kw.update(zip(arg_names, args))
        kw.update(kwargs)
        if callable(key_pattern):
            key = key_pattern(*[kw[name] for name in arg_names])
        else:
            key = key_pattern.format(*[kw[n] for n in arg_names], **kw)
        return key and key.replace(' ', '_'), kw
    return gen_key


def cache(key_pattern):
    def deco(f):
        rv = inspect.getfullargspec(f)
        arg_names, kwonlydefaults = rv.args, rv.kwonlydefaults
        gen_key = gen_key_factory(key_pattern, arg_names, kwonlydefaults)
        
        @wraps(f)
        async def _(*a, **kw):
            redis = await get_redis()
            key, args = gen_key(*a, **kw)
            if not key:
                return f(*a, **kw)
            r = await redis.get(key)
            
            if r is None:
                r = await f(*a, **kw)
                if r is not None and not isinstance(r, Empty):
                    r = dumps(r)
                    await redis.set(key, r)
            else:
                print('Get from Cache...')
            try:
                r = loads(r)
                
            except TypeError:
                ...
            return r
        _.original_function = f
        return _
    return deco


async def clear_mc(*keys):
    redis = await get_redis()
    print(f'Clear cached: {keys}')
    assert redis is not None
    await asyncio.gather(*[redis.delete(k) for k in keys],
                        return_exceptions=True)

if __name__ == "__main__":
    async def in_db(id):
        print('in db')
        return f'res {id}'

    KEY = 'TEST %s'

    @cache(KEY % '{id}')
    async def get_post(id):
        rv = await in_db(id)
        return rv

