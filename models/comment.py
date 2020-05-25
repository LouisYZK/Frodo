import asyncio

import mistune
import markupsafe

from config import REDIS_URL, partials, K_COMMENT, ONE_HOUR
from .base import BaseModel
from .user import GithubUser

markdown = mistune.Markdown()