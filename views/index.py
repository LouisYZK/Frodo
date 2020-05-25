import re
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from models import Post
from ext import mako


router = APIRouter()

CODE_RE = re.compile('```([A-Za-z]+\n)?|#+')

@router.get('/search')
@mako.template('search.html')
async def search(request: Request, q: str = ''):
    return {'q': q}

async def _search_json(request: Request):
    posts = await Post.get_all()
    post_objs = [Post(**post_data) for post_data in posts]
    return [{
        'url': post.url,
        'title': post.title,
        'content': CODE_RE.sub('', await post.content) if (await post.content) else ''
    } for post in post_objs]

@router.get('/search.json')
async def search_json(request: Request):
    dct = await _search_json(request)
    return JSONResponse(dct)
    
