import asyncio

import mistune
import markupsafe
from sqlalchemy import Column, String, Integer, DateTime, func

from .base import BaseModel
from .user import GithubUser
from .mc import cache, clear_mc
from .react import ReactMixin, ReactItem, ReactStats
import config

markdown = mistune.Markdown()
MC_KEY_COMMENT_LIST = 'comment:%s:comment_list'
MC_KEY_N_COMMENTS = 'comment:%s:n_comments'
MC_KEY_COMMNET_IDS_LIKED_BY_USER = 'react:comment_ids_liked_by:%s:%s'
MC_KEY_LATEST_COMMENTS = 'comment:latest_comments:%s'


class Comment(BaseModel, ReactMixin):
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

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

    async def clear_mc(self):
        keys = [key % self.post_id for key in (
            MC_KEY_N_COMMENTS, MC_KEY_COMMENT_LIST)]
        partial_config = next((p for p in config.partials
                               if p['name'] == 'latest_comments'), None)
        if partial_config:
            count = partial_config.get('count')
            if count:
                keys.append(MC_KEY_LATEST_COMMENTS % count)
        await clear_mc(*keys)

    @property
    async def content(self):
        rv = await self.get_props_by_key('content')
        if rv:
            return rv.decode('utf-8')

    @property
    async def html_content(self):
        content = markupsafe.escape(await self.content)
        if not content:
            return ''
        return markdown(content)

    @property
    async def user(self):
        data = await GithubUser.async_first(gid=self.github_id)
        return await GithubUser(**data).to_async_dict(**data)

    @property
    async def n_likes(self):
        stats = await self.stats
        return stats.love_count

        


class CommentMixin:
    async def add_comment(self, user_id, content, ref_id=0):
        rv = await Comment.acreate(github_id=user_id, post_id=self.id,
                                     ref_id=ref_id)
        obj_data = await Comment.cache(id=rv)
        obj = Comment(**obj_data)
        await obj.set_content(content)
        return await obj.to_async_dict(**obj_data)

    async def del_comment(self, user_id, comment_id):
        c = await Comment.cache(id=comment_id)
        if c and c.get('github_id') == user_id and c.get('post_id') == self.id:
            await Comment.adelete(id=comment_id)
            return True
        return False

    @property
    @cache(MC_KEY_COMMENT_LIST % ('{self.id}'))
    async def comments(self):
        data = await Comment.async_filter(post_id=self.id)
        objs = [await Comment(**d).to_async_dict(**d) for d in data]
        return objs

    @property
    @cache(MC_KEY_N_COMMENTS % '{self.id}')
    async def n_comments(self):
        return len(await Comment.async_filter(post_id=self.id))

    @cache(MC_KEY_COMMNET_IDS_LIKED_BY_USER % (
        '{user_id}', '{self.id}'))
    async def comment_ids_liked_by(self, user_id):
        cids = [c.id for c in await self.comments]
        if not cids:
            return []
        react_items = await ReactItem.async_filter(target_kind=config.K_COMMENT,
                                            user_id=user_id)
        react_ids = [item['target_id'] for item in react_items if item['target_id'] in cids]
        return react_ids
    