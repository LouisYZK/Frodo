import base64
import asyncio
import mimetypes
import jwt
from jwt import PyJWTError
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, UploadFile, File
from typing import List, Optional, Any
from ext import mako, oauth2_scheme
from models import schemas, forms
from models.user import User, create_user, modify_user, search_user_by_name, get_current_user
from models.post import Post, Tag, PostTag
from models.utils import generate_id
from models.activity import create_new_status, create_activity_after_post_created
import config

router = APIRouter()


@router.get('/users')
async def list_users(token: str = Depends(oauth2_scheme)) -> schemas.CommonResponse:
    users: list = await User.async_all()
    users = [schemas.User(**u) for u in users]
    return {'items': users, 'total': len(users)}

@router.post('/user/new', response_model=schemas.User)
async def create_new_user(name: str = Form(...),
                          email: str = Form(...),
                          password: str = Form(...),
                          avatar: str = Form(...),
                          token=Depends(oauth2_scheme)):
    data = schemas.UserCreate(name=name, email=email,
                              password=password, avatar=avatar)
    user = await create_user(**dict(data))
    if not user:
        raise HTTPException(status_code=500,
                            detail='Create User fails...')
    return user

@router.delete('/users')
async def delete_user(data: schemas.UserDelete, token=Depends(oauth2_scheme)):
    try:
        await User.adelete(id=data.id)
    except:
        raise HTTPException(status_code=402, detail='delte fails')
    
    
@router.get('/user/info')
async def current_user(request: Request, token: str=Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials',
            headers={"WWW-Authenticate": "Bearer"})
    try:
        playload = jwt.decode(token, config.JWT_SECRET, algorithms=config.JWT_ALGORITHM)
        username: str = playload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
    user = await User.async_first(name=token_data.username)
    user = schemas.User(**user)
    if user is None:
        raise credentials_exception
    request.session['admin_user'] = dict(user)
    return user

@router.get('/user/{user_id}/')
async def get_user_by_id(request: Request, user_id: int, token=Depends(oauth2_scheme)):
    user = await User.cache(id=user_id)
    if not user:
        raise HTTPException(404, 'not such user!')
    avatar = user.get('avatar', None)
    user['avatar_url'] = (request.app.url_path_for('static', path=f'upload/{avatar}') if avatar else 
    '')
    user.pop('password')
    return user

@router.put('/user/{user_id}')
async def update_user(user_id: int,
                      name: str = Form(...),
                      id: str = Form(...),
                      email: str = Form(...),
                      password: str = Form(...),
                      avatar: str = Form(...),
                      active: bool = Form(...),
                      token=Depends(oauth2_scheme)):
    user = schemas.UserUpdate(name=name, id=id,
                              email=email, password=password,
                              avatar=avatar, active=active)
    rv = await modify_user(user)

@router.post('/upload')
async def upload(request: Request,
                 avatar: UploadFile=Form(None),
                 file: UploadFile=Form(None)):
    user = request.session.get('user', {})
    if not user:
        return {'msg': 'Auth required.'}
    if avatar is not None:
        file = avatar
        is_avarta = True
    else:
        is_avarta = False

    suffix = file.filename.split('.')[-1]
    fid = generate_id()
    filename = f'{fid}.{suffix}'
    uploaded_file = Path(config.UPLOAD_FOLDER) / filename
    content = await file.read()
    with open(uploaded_file, 'wb') as f:
        f.write(content)
    mime, _ = mimetypes.guess_type(str(uploaded_file))
    encoded = b''.join(base64.encodestring(content).splitlines()).decode()

    if is_avarta:
        dct = {
            'files': {
                'avatar': f'data:{mime};base64,{encoded}', 'avatar_path':  filename
            }
        }
    else:
        dct = {'r': 0, 'filename': filename}
    return dct


@router.get('/user/search', response_model=schemas.CommonResponse)
async def search_user(name: str):
    results = await search_user_by_name(name)
    return {'items': results, 'total': len(results)}


@router.post('/post/new')
async def create_post(title: str = Form(...),
                      slug: str = Form(...),
                      summary: str = Form(None),
                      content = Form(...),
                      is_page: bool = Form(...),
                      can_comment: bool = Form(...),
                      author_id: int = Form(...),
                      status: int = Form(...),
                      tags: List[str] = Form(...),
                      token: str = Depends(oauth2_scheme)):
    new_post = await Post.acreate(title=title,
                        slug=slug,
                        summary=summary,
                        content=content,
                        type=is_page,
                        can_comment=can_comment,
                        author_id=author_id,
                        tags=tags,
                        status=status)
    if not new_post:
        raise HTTPException(status_code=500,
                            detail='Create User fails...')
    task = create_activity_after_post_created(post_id=new_post.id, user_id=author_id)
    asyncio.create_task(task)

    return new_post

@router.get('/posts')
async def list_posts(limit: int=config.PER_PAGE, page: int=1, with_tag: int = 0):
    offset = (page - 1) * limit
    total = len(await Post.async_all())
    _posts = await Post.async_all(limit=limit, offset=offset,
                                  order_by='created_at', desc=True)
    _posts = sorted(_posts, key=lambda x: -x['id'])
    posts = []
    for post in _posts:
        dct = post
        post = Post(**post)
        if with_tag:
            author = await post.author
            dct['author_name'] = author['name']
            dct['author_id'] = author['id']
            tags = await post.tags
            dct['tags'] = [t.name for t in tags]
        posts.append(dct)
    return {'items': posts, 'total': total}


@router.delete('/post/{post_id}')
async def delete_post(post_id: int, token=Depends(oauth2_scheme)):
    await Post.adelete(id=post_id)
    await PostTag.adelete(post_id=post_id)
    return {'r': 1}

@router.get('/post/{post_id}')
async def get_post_by_id(post_id: int, token=Depends(oauth2_scheme)):
    post = await Post.async_first(id=post_id)
    if not post:
        return {}
    obj = Post(**post)
    post['author'] = await obj.author
    post['preview_url'] = obj.preview_url
    post['content'] = await obj.content 
    post['url'] = obj.url
    post['tags'] = [t.name for t in await obj.tags]
    return post

@router.put('/post/{post_id}')
async def modfiy_post(post_id: int,
                      title: str = Form(...),
                      slug: str = Form(...),
                      summary: str = Form(None),
                      content = Form(...),
                      type: int = Form(...),
                      can_comment: bool = Form(...),
                      author_id: int = Form(...),
                      tags: List[str] = Form(...),
                      status: int = Form(...),
                      token=Depends(oauth2_scheme)):
    post = schemas.Post(id=post_id,
                    title=title,
                    slug=slug,
                    summary=summary,
                    content=content,
                    can_comment=can_comment,
                    author_id=author_id,
                    type=type,
                    status=status)
    obj_data = dict(post)
    content = obj_data.pop('content')
    obj = Post(**dict(obj_data))
    rv = await obj.asave(**dict(obj_data))
    await obj.set_content(content)
    await obj.update_tags(tags)
    
    return rv


@router.get('/tags')
async def list_tags():
    tags = await Tag.async_all()
    return {'items': [t['name'] for t in tags] }


@router.post('/status')
async def create_status(request: Request):
    user = request.session.get('admin_user', {})
    if not user:
        return {'r': 0, 'msg': 'Auth required.'}
    data = await request.json()
    obj, msg = await create_new_status(user.get('id'), data)
    activity = None if not obj else await obj.to_full_dict()
    return {'r': not bool(obj), 'msg': msg, 'activity': activity}


