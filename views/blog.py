from collections import Counter
from itertools import groupby
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from ext import mako
from models import Post, Tag, PostTag, ReactItem
from models import schemas
from models.post import (MC_KEY_ARCHIVES, MC_KEY_ARCHIVE, MC_KEY_TAGS, MC_KEY_TAG)
from models.utils import Pagination
from models.mc import cache
import config


router = APIRouter()

async def _tags():
    """Get the tags' name and their numbers.
    """
    tag_ids = [
        tag['tag_id']
        for tag in (await PostTag.async_all())
    ]
    counter = Counter(tag_ids)
    tags_ = await Tag.async_in('id', list(counter.keys()))
    tags_ = [Tag(**t) for t in tags_]
    return [
        (tags_[index], count)
        for index, count in enumerate(counter.values())
    ]
    
@router.get('/tags', name='tags', response_class=HTMLResponse)
@mako.template('tags.html')
@cache(MC_KEY_TAGS)
async def tags(request: Request):
    tags = await _tags()
    return {'tags': sorted(tags, key=lambda x: x[1], reverse=True)}


@router.get('/tag/{tag_id}', name='tags')
@cache(MC_KEY_TAG % '{tag_id}')
@mako.template('tag.html')
async def tag(request: Request, tag_id):
    tag = await Tag.async_first(id=tag_id)
    tag_obj = Tag(**tag)
    if not tag:
        raise HTTPException(status_code=404, detail='no such tag.')
    post_ids = [ p['post_id']
        for p in (await PostTag.async_filter(tag_id=tag_id))
    ]
    posts = await Post.async_in('id', post_ids)
    posts = [p for p in posts if p['status'] == Post.STATUS_ONLINE]
    post_objs = [Post(**p) for p in posts]
    return {'tag': tag_obj, 'posts': post_objs}


@router.get('/archives', name='archives', response_class=HTMLResponse)
@mako.template('archives.html')
@cache(MC_KEY_ARCHIVES)
async def archives(request: Request):
    post_data = await Post.async_filter(status=Post.STATUS_ONLINE)
    post_obj = [Post(**p) for p in post_data]
    post_obj = sorted(post_obj, key=lambda p: p.created_at, reverse=True)
    rv = dict()

    for year, items in groupby(post_obj, lambda x: x.created_at.year):
        if year in rv:
            rv[year].extend(list(items))
        else:
            rv[year] = list(items)
    archives = sorted(rv.items(), key=lambda x: x[0], reverse=True)
    return {'archives': archives}


@router.get('/archives/{year}', name='archives')
@mako.template('archives.html')
@cache(MC_KEY_ARCHIVE % '{year}')
async def archive(request: Request, year):
    post_data = await Post.async_filter(status=Post.STATUS_ONLINE)
    post_obj = [Post(**p) for p in post_data if p['created_at'].year == int(year)]
    archives = [(year, post_obj)]
    return {'archives': archives}


@router.get('/', name='index', response_class=HTMLResponse)
@mako.template('index.html')
async def index(request: Request, page=1):
    start = (page - 1) * config.PER_PAGE
    posts = await Post.get_all(with_page=False)
    total = len(posts)
    posts = posts[start: start + config.PER_PAGE]
    post_objs = [await Post(**p).to_async_dict(**p) for p in posts]
    paginatior = Pagination(page, config.PER_PAGE, total, post_objs)
    json = {'paginatior': paginatior}
    return json
    


@router.get('/page/{ident}', name='page')
@mako.template('index.html')
async def page(request: Request, ident: int =1):
    page = ident
    start = (page - 1) * config.PER_PAGE
    posts = await Post.get_all(with_page=False)
    total = len(posts)
    posts = posts[start: start + config.PER_PAGE]
    post_objs = [await Post(**p).to_async_dict(**p) for p in posts]
    paginatior = Pagination(page, config.PER_PAGE, total, post_objs)
    json = {'paginatior': paginatior}
    return json

@router.get('/page/{ident}', name='page')
@mako.template('post.html')
async def page_(request: Request, ident):
    if isinstance(ident, str):
        post = await Post.get_by_slug(ident)
    if not post:
        raise HTMLResponse(status_code=404)
    post = await Post(**post).to_async_dict(**post)
    post.author = config.AttrDict(post.author)
    return {'post': post }

@router.get('/post/{ident}', name='post')
@mako.template('post.html')
async def post(request: Request, ident):
    ident = ident.replace('+', ' ')
    if ident.isdigit():
        post_data = await Post.cache(id=int(ident))
    else:
        post_data = await Post.get_by_slug(ident)
    if not post_data:
        raise HTMLResponse(status_code=404)
    post = Post(**post_data)

    stats = await post.stats
    reaction_type = None
    liked_comment_ids = []
    github_user = request.session.get('user')
    pageview = await post.incr_pageview()
    if github_user:
        reaction_type = await post.get_reaction_type(github_user['gid'])
        liked_comment_ids = await post.comment_ids_liked_by(github_user['gid'])

    post = await post.to_async_dict(**post_data)
    post.author = config.AttrDict(post.author)
    return {'post': post , 'github_user': github_user, 
            'stats': stats, 'reaction_type': reaction_type,
            'liked_comment_ids': liked_comment_ids,
            'pageview': pageview}