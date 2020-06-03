import re
import ast
import types
import random
import inspect
from datetime import datetime, timedelta
from aioredis.errors import RedisError
from html.parser import HTMLParser
from sqlalchemy import Column, SmallInteger, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from .base import Base, BaseModel, ModelMeta
from .mc import cache, clear_mc
from .user import User
from .utils import trunc_utf8
from .comment import CommentMixin
from .react import ReactMixin
from .markdown import markdown, toc, toc_md, MLStripper
from . import schemas
import config

MC_KEY_TAGS_BY_POST_ID = 'post:%s:tags'
MC_KEY_RELATED = 'post:related_posts:%s:limit:%s'
MC_KEY_POST_BY_SLUG = 'post:%s:slug'
MC_KEY_ALL_POSTS = 'core:posts:%s:v2'
MC_KEY_FEED = 'core:feed'
MC_KEY_SITEMAP = 'core:sitemap'
MC_KEY_SEARCH = 'core:search.json'
MC_KEY_ARCHIVES = 'core:archives'
MC_KEY_ARCHIVE = 'core:archive:%s'
MC_KEY_TAGS = 'core:tags'
MC_KEY_TAG = 'core:tag:%s'
MC_KEY_SPECIAL_ITEMS = 'special:%s:items'
MC_KEY_SPECIAL_POST_ITEMS = 'special:%s:post_items'
MC_KEY_SPECIAL_BY_PID = 'special:by_pid:%s'
MC_KEY_SPECIAL_BY_SLUG = 'special:%s:slug'
MC_KEY_ALL_SPECIAL_TOPICS = 'special:topics'
RK_PAGEVIEW = 'frodo:pageview:{}:v2'
RK_ALL_POST_IDS = 'frodo:all_post_ids'
RK_VISITED_POST_IDS = 'frodo:visited_post_ids'
BQ_REGEX = re.compile(r'<blockquote>.*?</blockquote>')
PAGEVIEW_FIELD = 'pv'



class Post(BaseModel, CommentMixin, ReactMixin):
    STATUSES = (
        STATUS_UNPUBLISHED,
        STATUS_ONLINE
    ) = range(2)

    status = Column(SmallInteger(), default=STATUS_UNPUBLISHED)

    (TYPE_ARTICLE, TYPE_PAGE) = range(2)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    title = Column(String(100), unique=True)
    author_id = Column(Integer())
    slug = Column(String(100))
    summary = Column(String(255))
    can_comment = Column(Boolean(), default=True)
    type = Column(Integer(), default=TYPE_ARTICLE)
    pageview = Column(Integer(), default=0)

    kind = config.K_POST


    @cache(MC_KEY_RELATED % ('{self.id}', '{limit}'))
    async def get_related(self, limit: int=4):
        tag_ids = [tag.id for tag in await self.tags]
        if not tag_ids:
            return []
        post_ids = set([ item['post_id']
            for item in await PostTag.async_in('tag_id', tag_ids)])
        post_ids -= set([self.id])
        if not post_ids: return []
        related_posts = [
            Post(**p)
            for p in await Post.async_in('id', post_ids)
        ]
        return related_posts[:limit] if len(related_posts) >= limit else related_posts

    @classmethod
    async def acreate(cls, **kwargs):
        tags = kwargs.pop('tags', [])
        content = kwargs.pop('content')
        obj_id = await super().acreate(**kwargs)
        kwargs['id'] = obj_id
        if tags:
            try:
                await PostTag.update_multi(obj_id, tags)
            except:
                await Post.adelete(id=obj_id)
                return
        obj = cls(**(await cls.async_first(id=obj_id)))
        await obj.set_content(content)
        return obj
    
    async def update_tags(self, tagnames):
        if tagnames:
            await PostTag.update_multi(self.id, tagnames)
        return True

    @property
    @cache(MC_KEY_TAGS_BY_POST_ID % ('{self.id}'))
    async def tags(self):
        pts = await PostTag.async_filter(post_id=self.id)
        if not pts:
            return []
        ids = [item['tag_id'] for item in pts]
        tags = await Tag.async_in('id', ids)
        tags = [Tag(**t) for t in tags]
        return tags

    @property
    async def author(self):
        print('user_id', self.author_id)
        rv = await User.cache(id=self.author_id)
        return {'name': rv['name'], 'id': self.author_id, 'avatar': rv['avatar']}
    
    @property
    def is_page(self):
        return self.type == self.TYPE_PAGE

    @property
    def preview_url(self):
        return f'/{self.__class__.__name__.lower()}/{self.id}/preview'

    async def set_content(self, content):
        return await self.set_props_by_key('content', content)

    async def asave(self, *args, **kwargs):
        content = kwargs.pop('content', None)
        if content is not None:
            await self.set_content('content', content)
        return await super().asave(*args, **kwargs)

    @property
    async def content(self):
        rv = await self.get_props_by_key('content')
        if rv:
            return rv.decode('utf-8')

    @classmethod
    @cache(MC_KEY_POST_BY_SLUG % '{slug}')
    async def get_by_slug(cls, slug):
        return await cls.async_first(slug=slug) 

    @classmethod
    @cache(MC_KEY_ALL_POSTS % '{with_page}')
    async def get_all(cls, with_page=True):
        if with_page:
            posts = await Post.async_filter(status=Post.STATUS_ONLINE)
        else:
            posts = await Post.async_filter(status=Post.STATUS_ONLINE,
                                            type=Post.TYPE_ARTICLE)
        return sorted(posts, key=lambda p: p['created_at'], reverse=True)

    @property
    def url(self):
        if self.is_page:
            return f'/page/{self.slug}'
        return f'/post/{getattr(self, config.PERMALINK_TYPE) or self.id}/'

    @property
    async def html_content(self):
        content = await self.content
        if not content:
            return ''
        return markdown(content)

    @property
    async def excerpt(self):
        if self.summary:
            return self.summary
        s = MLStripper()
        s.feed(await self.html_content)
        return trunc_utf8(BQ_REGEX.sub('', s.get_data()).replace('\n', ''), 100)

    @property
    async def toc(self):
        content = await self.content
        if not content:
            return ''
        toc.reset_toc()
        toc_md.parse(content)
        return toc.render_toc(level=4)

    @classmethod
    async def cache(cls, ident):
        if str(ident).isdigit():
            return await super().cache(id=ident)
        return await cls.get_by_slug(ident)

    async def clear_mc(self):
        print('Clear POst MC', self.created_at)
        try:
            keys = [
                MC_KEY_FEED, MC_KEY_SITEMAP, MC_KEY_SEARCH, MC_KEY_ARCHIVES,
                MC_KEY_TAGS, MC_KEY_RELATED % (self.id, 4),
                MC_KEY_POST_BY_SLUG % self.slug,
                MC_KEY_ARCHIVE % self.created_at.year
            ]
        except:
            import traceback
            traceback.print_exc()
        for i in [True, False]:
            keys.append(MC_KEY_ALL_POSTS % i)

        for tag in await self.tags:
            keys.append(MC_KEY_TAG % tag.id)
        await clear_mc(*keys)

    async def incr_pageview(self, increment=1):
        redis = await self.redis
        try:
            await redis.sadd(RK_ALL_POST_IDS,self.id)
            await redis.sadd(RK_VISITED_POST_IDS, self.id)
            return await redis.hincrby(RK_PAGEVIEW.format(self.id),
                                       PAGEVIEW_FIELD, 
                                       increment)
        except:
            return self.pageview

    @property
    async def pageview_(self):
        try:
            return int(await (await self.redis).hget(
                RK_PAGEVIEW.format(self.id), PAGEVIEW_FIELD) or 0
            )
        except RedisError:
            return self.pageview


                     

            

class Tag(BaseModel):
    name = Column(String(100), unique=True)

    @classmethod
    def create(cls, **kwargs):
        name = kwargs.pop('name')
        kwargs['name'] = name.lower()
        return super().acreate(**kwargs)

    @classmethod
    async def get_by_name(cls, name):
        return  await cls.async_filter(name=name)


class PostTag(BaseModel):
    post_id = Column(Integer())
    tag_id = Column(Integer())
    updated_at = Column(DateTime,  server_default=func.now(), nullable=False)

    @classmethod
    async def update_multi(cls, post_id, tags: list):
        origin_tags_id = [t['tag_id'] for t in (
            await PostTag.async_filter(post_id=post_id)           
        )]
        origin_tags_name = set([t['name'] for t in await Tag.async_in('id', origin_tags_id)])
        need_add = set(tags) - origin_tags_name
        need_del = origin_tags_name - set(tags)
        need_add_tags_id = []
        need_del_tags_id = set()
        for tag_name in need_add:
            rv = await Tag.get_or_create(name=tag_name)
            if isinstance(rv, int): need_add_tags_id.append(rv)
            else: need_add_tags_id.append(rv['id'])
        for tag_name in need_del:
            rv = await Tag.get_or_create(name=tag_name)
            if isinstance(rv, int): need_del_tags_id.append(rv)
            else: need_del_tags_id.add(rv['id'])

        if need_del_tags_id:
            for id in list(need_del_tags_id):
                await cls.adelete(post_id=post_id, tag_id=id)

        for tag_id in need_add_tags_id:
            await cls.get_or_create(post_id=post_id, tag_id=tag_id)

        await clear_mc(MC_KEY_TAGS_BY_POST_ID % post_id)