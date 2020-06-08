import math
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pickle import dumps, loads
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

import config
from .base import BaseModel
from .post import Post
from .comment import CommentMixin
from .mc import cache, clear_mc
from .mixin import ContentMixin
from .react import ReactMixin
from .user import User
from .utils import cached_property

PER_PAGE = 10
DEFAULT_WIDTH = 260
MC_KEY_ACTIVITIES = 'core:activities:%s'
MC_KEY_ACTIVITY_COUNT = 'core:activity_count'
MC_KEY_ACTIVITY_FULL_DICT = 'core:activity:full_dict:%s'
MC_KEY_STATUS_ATTACHMENTS = 'core.status:attachments:%s'
FFPROBE_TMPL = 'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 {input}'  # noqa


@dataclass
class Attachment:
    LAYOUTS = (LAYOUT_LINK, LAYOUT_PHOTO, LAYOUT_VIDEO) = range(3)
    layout: int = LAYOUT_LINK
    url: Union[Optional[str], str] = ''


@dataclass
class Link(Attachment):
    title: str = ''
    abstract: str = ''
    images: List[str] = field(default_factory=list)
    layout: int = Attachment.LAYOUT_LINK


@dataclass
class Photo(Attachment):
    title: Optional[str] = ''
    size: Tuple[int, int] = (0, 0)
    layout: int = Attachment.LAYOUT_PHOTO


@dataclass
class Video(Attachment):
    title: Optional[str] = ''
    cover_url: str = ''
    size: Tuple[int, int] = (0, 0)
    layout: int = Attachment.LAYOUT_VIDEO

    
class Status(ContentMixin, BaseModel):
    kind = config.K_STATUS
    user_id = Column(Integer())
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    @classmethod
    async def acreate(cls, **kwargs):
        content = kwargs.pop('content')
        rv = await super().acreate(**kwargs)
        obj = cls(**(await cls.async_first(id=rv)))
        await obj.set_content(content)
        await cls.__flush__(obj)
        return obj

    async def set_attachments(self,
                attachments: List[Union[Link, Photo, Video]]) -> bool:
        if not attachments:
            return False
        lst = []
        for attach in attachments:
            lst.append(asdict(attach))
        await self.set_props_by_key('attachments', dumps(lst))
        return True

    @property
    @cache(MC_KEY_STATUS_ATTACHMENTS % '{self.id}')
    async def attachments(self) -> List[Attachment]:
        rv = await self.get_props_by_key('attachments')
        if not rv: return []
        return loads(rv)

    @property
    async def user(self) -> User:
        rv = await User.cache(id=self.user_id)
        return rv

    async def clear_mc(self):
        keys = [MC_KEY_STATUS_ATTACHMENTS % self.id]
        await clear_mc(*keys)


class Activity(CommentMixin, ReactMixin, BaseModel):
    kind = config.K_ACTIVITY
    user_id = Column(Integer())
    target_id = Column(Integer())
    target_kind = Column(Integer())
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    @classmethod
    @cache(MC_KEY_ACTIVITIES % '{page}')
    async def get_multi_by(cls, page: int = 1) -> List[Dict]:
        items = []
        queryset = await cls.async_all(
            offset=(page - 1) * PER_PAGE,
            limit=PER_PAGE,
            order_by='created_at',
            desc=True)
        for data in queryset:
            try:
                items.append(await cls(**data).to_full_dict())
            except:
                continue
        return items
    
    @cached_property
    async def target(self) -> dict:
        kls = None
        if self.target_kind == config.K_POST:
            kls = Post
            data = await kls.cache(ident=self.target_id)
        elif self.target_kind == config.K_STATUS:
            kls = Status
            data = await kls.cache(id=self.target_id)
        if kls is None:
            return
        target = await kls(**data).to_async_dict(**data)
        if self.target_kind == config.K_POST:
            target.content = ''
            target.html_content = ''
        return target

    @property
    async def action(self):
        action = None
        if self.target_kind == config.K_STATUS:
            target = await self.target
            attachments = target.attachments
            if attachments:
                layout = attachments[0]['layout']
                if layout == Attachment.LAYOUT_LINK:
                    action = '分享网页'
                elif layout == Attachment.LAYOUT_PHOTO:
                    action = f'上传了{len(attachments)}张照片'
                elif layout == Attachment.LAYOUT_VIDEO:
                    action = f'上传了{len(attachments)}个视频'
            elif '```' in target.content:
                action = '分享了代码片段'
        elif self.target_kind == config.K_POST:
            action = '写了新文章'

        if action is None:
            action = '说'
        return action

    @property
    async def attachments(self):
        if self.target_kind == config.K_STATUS:
            target = await self.target
            attachments = target.attachments
        elif self.target_kind == config.K_POST:
            target = await self.target
            attachments = [
                asdict(Link(url=target.url, title=target.title, 
                            abstract=''))
            ]
        else:
            attachments = []
        return attachments

    @property
    async def user(self) -> dict:
        return await User.cache(id=self.user_id)
    
    @classmethod
    # @cache(MC_KEY_ACTIVITY_COUNT)
    async def count(cls) -> int:
        data = await cls.async_all()
        return len(data)
    
    @cache(MC_KEY_ACTIVITY_FULL_DICT % '{self.id}')
    async def to_full_dict(self) -> Dict[str, Any]:
        target = await self.target
        if not target:
            return {}
        user = await self.user
        if self.target_kind == config.K_STATUS:
            target['url'] = ''
        elif self.target_kind == config.K_POST:
            pass
        avatar = user['avatar']
        if avatar:
            domain = config.CDN_DOMAIN if config.CDN_DOMAIN and not config.DEBUG else ''
            avatar = f'{domain}/static/upload/{avatar}'
        attachments = await self.attachments

        return {
            'id': self.id,
            'user': {
                'name': user['name'],
                'avatar': avatar
            },
            'target': target,
            'action': await self.action,
            'created_at': self.created_at,
            'attachments': attachments,
            'can_comment': False,  # contemporary
            'layout': attachments[0]['layout'] if attachments else '',
        }

    async def clear_mc(self):
        total = await self.count()
        page_count = math.ceil(total / PER_PAGE)
        keys = [MC_KEY_ACTIVITIES % p for p in range(1, page_count+1)]
        keys.extend([MC_KEY_ACTIVITY_COUNT, MC_KEY_ACTIVITY_FULL_DICT % self.id])
        await clear_mc(*keys)
    

async def create_new_status(user_id: int, data: Dict) -> Tuple[bool, str]:
    text = data.get('text')
    if not text: 
        return False, 'Text reqiured.'
    
    fids = data.get('fids', [])
    url = data.get('url', '')
    attachments = []
    if fids:
        is_video = fids[0].endswith('mp4')
        layout = Video if is_video else Photo
        for fid in fids:
            attach = layout(url=f'/static/upload/{fid}')
            if config.USE_FFMPEG and is_video:
                pass
        
            attachments.append(attach)

    elif url:
        url_info = data.get('url_info', {})
        attachments = [Link(url=url, title=url_info.get('title', url),
                            abstract=url_info.get('abstract', ''))]

    status = await Status.acreate(user_id=user_id, content=text)
    if not status:
        return False, 'Create status fail.'
    await status.set_attachments(attachments)
    act_id = await Activity.acreate(target_id=status.id, target_kind=config.K_STATUS,
                                 user_id=user_id)
    act = Activity(**(await Activity.async_first(id=act_id)))
    return act, ''


async def create_activity_after_post_created(post_id: int, user_id: int):
    await Activity.acreate(target_id=post_id, target_kind=config.K_POST, user_id=int(user_id))