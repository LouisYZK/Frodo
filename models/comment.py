import asyncio

import mistune
import markupsafe
from sqlalchemy import Column, String, Integer

from .base import BaseModel
from .user import GithubUser
import config

markdown = mistune.Markdown()


class Comment(BaseModel):
    github_id = Column(Integer())
    post_id = Column(Integer())
    ref_id = Column(Integer())
    kind = config.K_COMMENT

    async def set_content(self, content):
        return await self.set_props_by_key('content', content)
    
    async def asave(self, *args, **kwargs):
        content = kwargs.pop('content', None)
        if content is not None:
            await self.set_content(content)
        return await super().asave(*args, **kwargs)

    @property
    async def html_content(self):
        content = markupsafe.escape(await self.content)
        if not content:
            return ''
        return markdown(content)

    @property
    async def user(self):
        return await GithubUser.async_first(gid=self.github_id)

    @property
    async def n_likes(self):
        return 1


class CommentMixin:
    async def add_comment(self, user_id, content, ref_id=0):
        data = await Comment.acreate(github_id=user_id, post_id=self.id,
                                     ref_id=ref_id)
        obj = Comment(**data)
        await obj.set_content(content)
        return obj

    async def del_comment(self, user_id, comment_id):
        c = await Comment.async_first(id=comment_id)
        if c and c.get('github_id') == user_id and c.get('post_id') == self.id:
            await Comment.adelete(id=comment_id)
            return True
        return False

    @property
    async def comments(self):
        return await Comment.async_filter(post_id=self.id)

    @property
    async def n_comments(self):
        return len(await Comment.async_filter(post_id=self.id))

    