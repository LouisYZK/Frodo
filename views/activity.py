import mistune

from fastapi import APIRouter, Request, Form, Depends
from models import Post, GithubUser, ReactItem, Status, Activity
from models.utils import date_to_timestamp

router = APIRouter()

@router.get('/activities')
async def activities(request: Request, page: int = 1):
    total = await Activity.count()
    print(total)
    items = await Activity.get_multi_by(page)
    guser = request.session.get('github_user', {})
    if not guser:
        user_id = 841395
    else:
        user_id = guser['gid']
    # reactions ...

    activities = []
    for item in items:
        item['created_at'] = date_to_timestamp(item['created_at'])
        item['target']['created_at'] = date_to_timestamp(item['target']['created_at'])
        activities.append(item)
    from pprint import pprint
    return {'items': activities, 'total': total}