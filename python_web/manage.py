import os
import aiofiles
import yaml
import click
import asyncio
from datetime import datetime
from models.user import create_user
from models import Post, User

def run_async(coro):
    asyncio.run(coro)

@click.group()
def cli():
    ...

async def _adduser(**kwargs):
    try:
        user = await create_user(**kwargs)
    except Exception as e:
        print(e)
        click.echo(str(e))
    else:
        click.echo(f'User {user.name} created!!! ID: {user.id}')


async def extract_meta(file_path: str):
    data = ''
    data_exist = False
    content = ''
    async with aiofiles.open(file_path) as fp:
        async for line in fp:
            if line.strip() == '---' and data_exist:
                data_exist = False
                continue
            if line.strip() == '---':
                data_exist = True
                continue
            if data_exist:
                data += line
            else:
                content += line
    return data, content
    
async def add_post(dct, content, user_id=None):
    title = dct.get('title', '')
    tags = dct.get('tags', [])
    author_id = user_id
    date = dct.get('date', None)
    if not title:
        return 
    post = await Post.async_first(title=title)
    if post:
        return
    if date is None:
        date = datetime.now()
    await Post.acreate(title=title, content=content,
                       author_id=author_id, slug=title,
                       summary='', 
                       status=Post.STATUS_ONLINE,
                       can_comment=True,
                       type=Post.TYPE_ARTICLE,
                       created_at=date)
    print(f'{title} save...')

async def _hexo_export(dir, uname):
    user = await User.async_first(name=uname)
    id = user.get('id', '')
    if not id:
        return 
    for article in os.listdir(dir):
        if not article.endswith('.md'):
            continue
        else:
            file = f'{dir}/{article}'
            metdata, content = await extract_meta(file)
            dct = yaml.load(metdata)
            if 'title' not in dct:
                title = ' '.join(file.split('-')[3:])
                title = title.replace('.md', '')
                dct.update(title=title)
            asyncio.create_task(add_post(dct, content, user_id=id))

@cli.command()
@click.option('--name', required=True, prompt=True)
@click.option('--email', required=False, default=None, prompt=True)
@click.option('--password', required=True, prompt=True, hide_input=True,
              confirmation_prompt=True)
def adduser(name, email, password):
    run_async(_adduser(name=name, password=password, email=email))


@cli.command()
@click.option('--dir', required=True)
@click.option('--uname', required=True)
def hexo_export(dir, uname):
    run_async(_hexo_export(dir=dir, uname=uname))
    click.echo('Export Hexo Finished!')

if __name__ == '__main__':
    cli()