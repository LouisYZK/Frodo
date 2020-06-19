import markupsafe
from aioredis.commands import Redis

from .markdown import markdown
from .utils import get_redis


class ContentMixin:
    id: int

    @property
    async def redis(self) -> Redis:
        return await get_redis()

    def get_db_key(self, key: str) -> str:
        return f'{self.__class__.__name__}/{self.id}/props/{key}'

    async def set_props_by_key(self, key: str, value: bytes) -> bool:
        key = self.get_db_key(key)
        return await (await self.redis).set(key, value)  # noqa: W606

    async def get_props_by_key(self, key: str) -> bytes:
        key = self.get_db_key(key)
        return await (await self.redis).get(key) or b''  # noqa: W606

    async def set_content(self, content: bytes) -> bool:
        return await self.set_props_by_key('content', content)

    async def asave(self, *args, **kwargs):
        content = kwargs.pop('content', None)
        if content is not None:
            await self.set_content(content)
        return await super().asave(*args, **kwargs)  # type: ignore

    @property
    async def content(self) -> str:
        rv = await self.get_props_by_key('content')
        if rv:
            return rv.decode('utf-8')
        return ''

    @property
    async def html_content(self):
        content = str(markupsafe.escape(await self.content))
        if not content:
            return ''
        return markdown(content.replace('&gt;', '>'))
