import os
import configparser
import yaml
import ast
from pathlib import Path


HERE = Path(__file__).parent.absolute()
config_dir = HERE / 'config/config.ini.model'
config = configparser.ConfigParser()
config.read(config_dir)

ACCESS_TOKEN_EXPIRE_MINUTES = config.get('security', 'access_token_expire_minutes')
JWT_ALGORITHM = config.get('security', 'jwt_algorithm')

OAUTH_REDIRECT_PATH = config.get('github', 'oauth_redirect_path')
REDIRECT_URI = config.get('github', 'redirect_uri')
CLIENT_ID = config.get('github', 'client_id')
CLIENT_SECRET = config.get('github', 'client_secret')


DB_URL = os.getenv('DB_URL',
            config.get('database', 'db_url'))
REDIS_URL = os.getenv('REDIS_URL', 
            config.get('redis', 'redis_url'))
DEBUG = os.getenv('DEBUG', config.get('global', 'debug')).lower() \
            in ('true', 'y', 'yes', '1')
WTF_CSRF_SECRET_KEY = 123
AUTH_LOGIN_ENDPOINT = 'index.login'
MEMCACHED_HOST = os.getenv('MEMCACHED_HOST', 
                    config.get('memcached', 'memcached_host'))
MEMCACHED_PORT = config.get('memcached', 'memcached_port')
oauth_redirect_path = '/oauth'
redirect_uri = 'http://127.0.0.1:8000/oauth'

client_id = "098a2e6da880878e05da"
client_secret = "854cc0d86e61a83bb1dd00c3b23a3cc5b832d45c"

REACT_PROMPT = '喜欢这篇文章吗? 记得给我留言或订阅哦'
PLOAD_FOLDER = HERE / 'static/upload'
AUTHOR = 'zhikai'
SITE_TITLE = 'Zhikai-Yang Space'
PER_PAGE = 10
GOOGLE_ANALYTICS = ''
SENTRY_DSN = ''
REQUEST_TIMEOUT = 15
SHOW_PAGEVIEW = True
PERMALINK_TYPE = 'slug'  # 可选 id、slug、title

# [(Endpoint, Name, IconName, Color), ...]
# SITE_NAV_MENUS = [('blog.index', '首页'), ('blog.topics', '专题'),
#                   ('blog.archives', '归档'), ('blog.tags', '标签'),
#                   ('index.search', '搜索'), ('/page/aboutme', '关于我'),
#                   ('index.feed', 'RSS', 'rss', '#fc6423')]
SITE_NAV_MENUS = [('blog.index', '首页'),
                   ('blog.activities', '动态'),
                  ('blog.tags', '标签'),
                  ('index.search', '搜索'),
                  ('blog.archives', '归档'),
                  ('/post/aboutme', '关于我')
                  ]
BEIAN_ID = ''

JWT_SECRET = config.get('security', 'jwt_secret')
EXPIRATION_DELTA = 60 * 60
WTF_CSRF_ENABLED = False

MAIL_SERVER = 'smtp.qq.com'
MAIL_PORT = 465
MAIL_USERNAME = ''
MAIL_PASSWORD = ''

BLOG_URL = 'https://example.com'
UPLOAD_FOLDER = HERE / 'static/upload'

# Redis sentinel
REDIS_SENTINEL_SERVICE_HOST = None
REDIS_SENTINEL_SERVICE_PORT = 26379

SHOW_AUTHOR = True

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

try:
    with open(HERE / 'config.yaml') as f:
        yaml_content = f.read()
        partials = AttrDict(yaml.load(yaml_content)).partials   
    USE_YAML = True
except FileNotFoundError:
    USE_YAML = False
    partials = {}
try:
    from local_settings import *  # noqa
except ImportError:
    pass


K_POST = 1001
K_COMMENT = 1002

ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60
ONE_DAY = ONE_HOUR * 24

K_STATUS = 1003
K_ACTIVITY = 1004
CDN_DOMAIN = ''

STATIC_FILE_TYPES = ('jpg', 'png', 'webp', 'gif', 'mp4', 'css', 'js')