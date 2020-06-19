import re
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse
from models import Post
from models.user import create_github_user
from ext import mako, GithubClient
import config


router = APIRouter()

CODE_RE = re.compile('```([A-Za-z]+\n)?|#+')

@router.get('/search')
@mako.template('search.html')
async def search(request: Request, q: str = ''):
    return {'q': q}

async def _search_json(request: Request):
    posts = await Post.get_all(with_page=False)
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
    
@router.get('/oauth/post/{post_id}')
async def oauth_in_post(request: Request, post_id=None):
    if post_id is None:
        url = '/'
    else:
        url = request.url_for('post', ident=post_id)
    if 'github_user' in request.session:
        return RedirectResponse(url)
    else:
        client = GithubClient()
        request.session['post_url'] = str(request.url)
        return RedirectResponse(client.auth_url)
    


@router.get('/oauth')
async def oauth(request: Request):
    if 'error' in str(request.url):
        raise HTTPException(status_code=400)
    client = GithubClient()
    rv = await client.get_access_token(code=request.query_params.get('code'))
    token = rv.get('access_token', '')
    try:
        user_info = await client.user_info(token)
    except:
        return RedirectResponse(config.OAUTH_REDIRECT_PATH)
    rv = await create_github_user(user_info)
    request.session['github_user'] = rv
    return RedirectResponse(request.session.get('post_url'))