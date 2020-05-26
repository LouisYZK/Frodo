import re
import ast
import types
import random
import inspect
from datetime import datetime, timedelta
from html.parser import HTMLParser
from sqlalchemy import Column, SmallInteger, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
import pangu
import mistune

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from .base import Base, BaseModel, ModelMeta
# from .mc import cache, clear_mc
from .user import User
from .utils import trunc_utf8
# from .comment import CommentMixin
# from .react import ReactMixin
from .toc import TocMixin
from . import schemas
import config


BQ_REGEX = re.compile(r'<blockquote>.*?</blockquote>')

class MLStripper(HTMLParser):

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


class PanguMeta(type):
    def __new__(cls, name, bases, attrs):
        for base in bases:
            for name, fn in inspect.getmembers(base):
                if (isinstance(fn, types.FunctionType) and
                        name not in ('codespan', 'paragraph')):
                    try:
                        idx = inspect.getfullargspec(fn).args.index('text')
                    except ValueError:
                        continue
                    setattr(base, name, cls.deco(fn, idx))

        return super().__new__(cls, name, bases, attrs)

    @classmethod
    def deco(cls, func, index):
        def wrapper(*args, **kwargs):
            _args = list(args)
            _args[index] = pangu.spacing_text(_args[index])
            result = func(*_args, **kwargs)
            return result
        return wrapper


class BlogHtmlFormatter(HtmlFormatter):

    def __init__(self, **options):
        super().__init__(**options)
        self.lang = options.get('lang', '')

    def _wrap_div(self, inner):
        style = []
        if (self.noclasses and not self.nobackground and
                self.style.background_color is not None):
            style.append('background: %s' % (self.style.background_color,))
        if self.cssstyles:
            style.append(self.cssstyles)
        style = '; '.join(style)

        yield 0, ('<figure' + (self.cssclass and ' class="%s"' % self.cssclass) +  # noqa
                  (style and (' style="%s"' % style)) +
                  (self.lang and ' data-lang="%s"' % self.lang) +
                  '><table><tbody><tr><td class="code">')
        for tup in inner:
            yield tup
        yield 0, '</table></figure>\n'

    def _wrap_pre(self, inner):
        style = []
        if self.prestyles:
            style.append(self.prestyles)
        if self.noclasses:
            style.append('line-height: 125%')
        style = '; '.join(style)

        if self.filename:
            yield 0, ('<span class="filename">' + self.filename + '</span>')

        # the empty span here is to keep leading empty lines from being
        # ignored by HTML parsers
        yield 0, ('<pre' + (style and ' style="%s"' % style) + (
            self.lang and f' class="hljs {self.lang}"') + '><span></span>')
        for tup in inner:
            yield tup
        yield 0, '</pre>'


def block_code(text, lang, inlinestyles=False, linenos=False):
    if not lang:
        text = text.strip()
        return '<pre><code>%s</code></pre>\n' % mistune.escape(text)

    try:
        if lang in ('py', 'python'):
            lang = 'python3'
        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = BlogHtmlFormatter(
            noclasses=inlinestyles, linenos=linenos,
            cssclass='highlight %s' % lang, lang=lang
        )
        code = highlight(text, lexer, formatter)
        return code
    except Exception:
        # Github Card
        if lang == 'card':
            try:
                dct = ast.literal_eval(text)
                user = dct.get('user')
                if user:
                    repo = dct.get('repo')
                    card_html = f'''<div class="github-card" data-user="{ user }" { f'data-repo="{ repo }"' if repo else "" }></div>'''  # noqa
                    if dct.get('right'):
                        card_html = f'<div class="card-right">{card_html}</div>'  # noqa
                    return card_html
            except (ValueError, SyntaxError):
                ...

        return '<pre class="%s"><code>%s</code></pre>\n' % (
            lang, mistune.escape(text)
        )


class BlogRenderer(mistune.Renderer, metaclass=PanguMeta):
    def header(self, text, level, raw=None):
        hid = text.replace(' ', '')
        return f'<h{level} id="{hid}">{text}</h{level}>\n'

    def block_code(self, code, lang):
        inlinestyles = self.options.get('inlinestyles')
        linenos = self.options.get('linenos')
        return block_code(code, lang, inlinestyles, linenos)

    def link(self, link, title, text):
        return f' {super().link(link, title, text) } '


class TocRenderer(TocMixin, mistune.Renderer):
    ...

renderer = BlogRenderer(linenos=False, inlinestyles=False)
toc = TocRenderer()
markdown = mistune.Markdown(escape=True, renderer=renderer)
toc_md = mistune.Markdown(renderer=toc)

   


class Post(BaseModel):
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

    @classmethod
    async def acreate(cls, **kwargs):
        tags = kwargs.pop('tags', [])
        content = kwargs.pop('content')
        obj_id = await super().acreate(**kwargs)
        kwargs['id'] = obj_id
        if tags:
            print('tags', tags)
            try:
                await PostTag.update_multi(obj_id, tags)
            except:
                import traceback
                traceback.print_exc()
                await Post.adelete(id=obj_id)
                return
        obj = cls(**kwargs)
        await obj.set_content(content)
        return obj
    
    async def update_tags(self, tagnames):
        if tagnames:
            await PostTag.update_multi(self.id, tagnames)
        return True

    @property
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
        rv = await User.async_first(id=self.author_id)
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
    async def get_by_slug(cls, slug):
        return await cls.async_first(slug=slug) 

    @classmethod
    async def get_all(cls, with_page=True):
        if with_page:
            posts = await Post.async_filter(status=Post.STATUS_ONLINE)
        else:
            posts = await Post.async_filter(status=Post.STATUS_ONLINE,
                                            type=Post.TYPE_ARTICLE)
        return sorted(posts, key=lambda p: p['id'], reverse=True)

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
            else: need_del_tags_id.append(rv['id'])

        if need_del_tags_id:
            for id in list(need_del_tags_id):
                await cls.adelete(post_id=post_id, tag_id=id)

        for tag_id in need_add_tags_id:
            await cls.get_or_create(post_id=post_id, tag_id=tag_id)