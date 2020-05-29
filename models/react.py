from sqlalchemy import Column, Integer, String

from .base import BaseModel
# from .signals import comment_reacted
import config



class ReactItem(BaseModel):
    target_id = Column(Integer())
    target_kind = Column(Integer())
    user_id = Column(Integer())
    reaction_type = Column(Integer())

    REACTION_KINDS = (
        K_UPVOTE,
        K_FUNNY,
        K_LOVE,
        K_SURPRISED,
        K_SAD
    ) = range(5)
    REACTION_MAP = {
        'upvote': K_UPVOTE,
        'funny': K_FUNNY,
        'love': K_LOVE,
        'surprised': K_SURPRISED,
        'sad': K_SAD
    }

    @classmethod
    async def acreate(cls, **kwargs):
        obj_id = await super().acreate(**kwargs)
        obj = cls(**(await cls.async_first(id=obj_id)))
        react_name = next((name for name, type in cls.REACTION_MAP.items()
                           if type == obj.reaction_type), None)

        # update stats
        stat_data = await ReactStats.get_by_target(obj.target_id, obj.target_kind)
        field = f'{react_name}_count'
        stat_data.update({field :stat_data.get(field) + 1})
        await ReactStats.asave(**stat_data)
        return obj

    @classmethod
    async def get_reaction_item(cls, user_id, target_id, target_kind) -> dict:
        rv = await cls.async_first(user_id=user_id, target_id=target_id,
                              target_kind=target_kind)
        return rv

    @classmethod
    async def adelete(cls, **kwargs):
        rv = await super().adelete(**kwargs)
        stat_data = await ReactStats.get_by_target(
                        kwargs.get('target_id'), kwargs.get('target_kind'))
        react_name = next((name for name, type in cls.REACTION_MAP.items()
                           if type == kwargs.get('reaction_type')), None)
        field = f'{react_name}_count'
        stat_data.update({field :stat_data.get(field) - 1})
        await ReactStats.asave(**stat_data)
        return rv


class ReactStats(BaseModel):
    target_id = Column(Integer())
    target_kind = Column(Integer())
    upvote_count = Column(Integer(), server_default='0')
    funny_count = Column(Integer(), server_default='0')
    love_count = Column(Integer(), server_default='0')
    surprised_count = Column(Integer(), server_default='0')
    sad_count = Column(Integer(), server_default='0')

    @classmethod
    async def get_by_target(cls, target_id, target_kind):
        rv = await cls.async_first(target_id=target_id,
                                   target_kind=target_kind)
        if not rv:
            obj_id = await cls.acreate(target_id=target_id,
                                   target_kind=target_kind,
                                   upvote_count=0)
            rv = await cls.async_first(id=obj_id)
        return rv


class ReactMixin:
    async def add_reaction(self, user_id, reaction_type):
        item: dict = await ReactItem.get_reaction_item(user_id, self.id, self.kind)
        if item and reaction_type == item.get('reaction_type', ''):
            return True
        if not item:
            item: ReactItem = await ReactItem.acreate(
                target_id=self.id, target_kind=self.kind,
                user_id=user_id, reaction_type=reaction_type)
        else:
            item.update(reaction_type=reaction_type)
            await ReactItem.asave(**item)
            stat_data = await ReactStats.get_by_target(item.target_id, item.target_kind)
            field = reaction_type
            stat_data.update({field :stat_data.get(field) + 1})
            await ReactStats.asave(**stat_data)

        return bool(item)

    async def cancel_reaction(self, user_id):
        item = await ReactItem.get_reaction_item(user_id, self.id, self.kind)
        if item:
            await ReactItem.adelete(**item)
        return True

    @property
    async def stats(self):
        stats_data = await ReactStats.get_by_target(self.id, self.kind)
        return ReactStats(**stats_data)

    async def get_reaction_type(self, user_id):
        item = await ReactItem.get_reaction_item(user_id, self.id, self.kind)
        item = ReactItem(**item)
        return item.reaction_type if item else None
