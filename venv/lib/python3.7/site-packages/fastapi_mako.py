"""
Notice:
    Modified from https://github.com/dongweiming/sanic-mako
"""

import os
import sys
import pkgutil
import asyncio
import functools
from typing import Mapping
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import HTMLResponse
from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import TemplateLookupException, text_error_template

APP_KEY = os.getenv('APP_KEY', 'fastapi_mako')
REQUEST_CONTEXT_KEY = 'mako_context'


__version__ = '0.6.2'

__all__ = ('get_lookup', 'render_template', 'render_template_def',
           'render_string')

def get_root_path(import_name: str) -> str:
    mod = sys.modules.get(import_name)
    if mod is not None and hasattr(mod, '__file__'):
        return os.path.dirname(os.path.abspath(mod.__file__))
    
    loader = pkgutil.get_loader(import_name)
    if loader is None or import_name == '__main__':
        return os.getcwd()
    if filepath is None:
        raise RuntimeError("No actually root path found.")

class TemplateError(RuntimeError):
    def __init__(self, template):
        super(TemplateError, self).__init__()
        self.einfo = sys.exc_info()
        self.text = text_error_template().render()
        if hasattr(template, 'uri'):
            msg = f"Error occurred while rendering template '{template.uri}'"
        else:
            msg = template.args[0]
        super(TemplateError, self).__init__()


class FastAPIMako:
    def __init__(self, app: FastAPI=None,
                 pkg_path: str=None,
                 app_key_name: str=APP_KEY):
        self.app = app
        
        if app:
            self.init_app(app, pkg_path)


    def init_app(self, app, pkg_path=None,
                 app_key_name=APP_KEY):
        if pkg_path is not None and os.path.isdir(pkg_path):
            paths = [pkg_path]
        else:
            paths = [os.path.join(get_root_path(app.__name__), 'templates')]
        kw = {
            'input_encoding': 'utf-8'
        }
        setattr(app, app_key_name, TemplateLookup(directories=paths, **kw))
	
        return getattr(app, app_key_name)
    
    @staticmethod
    def template(template_name: str,
                 app_key_name: str = APP_KEY,
                 status: int= 200):
        def wrapper(func):
            @functools.wraps(func)
            async def wrapped(*args, **kwargs):
                if asyncio.iscoroutinefunction(func):
                    coro = func
                else:
                    coro = asyncio.coroutine(func)
                context = await coro(*args, **kwargs)
                request = kwargs.get('request')
                response = await render_template(template_name, request,
                                                 context,
                                                 app_key_name=app_key_name)
                response.status = status
                return response
            return wrapped
        return wrapper


def get_lookup(app, app_key_name=APP_KEY):
    return getattr(app, app_key_name)

async def render_string(template_name: str, request: Request,
                          context: Mapping, *, app_key_name: str = APP_KEY):
    lookup: TemplateLookup = get_lookup(request.app, app_key_name)

    if lookup is None:
        raise HTTPException(status_code=404, 
                            detail=f'Template engine is not initialized, '
                            "call fastapi_mako.init_app first.")
    try:
        template: Template = lookup.get_template(template_name)
    except TemplateLookupException as e:
        raise HTTPException(status_code=404,
                            detail=f'template {template_name} not found.') from e
    
    if request.scope.get(REQUEST_CONTEXT_KEY):
        context = dict(request.scope.get(REQUEST_CONTEXT_KEY), **context)
    try:
        text = template.render(request=request, app=request.app, **context)
    except Exception:
        template.uri = template_name
        raise TemplateError(template)

    return text

async def render_template(template_name: str, request: Request,
                          context: Mapping, *, app_key_name=APP_KEY):
    text = await render_string(template_name, request, context,
                               app_key_name=app_key_name)
    
    return HTMLResponse(text, media_type='text/html')

async def render_template_def(template_name, def_name, request, context, *,
                              app_key=APP_KEY):
    lookup = get_lookup(request.app, app_key)

    if lookup is None:

        raise HTTPException(status_code=500,
                details=f"Template engine is not initialized, "
            "call sanic_mako.init_app first")
    try:
        template = lookup.get_template(template_name)
    except TemplateLookupException as e:
        raise HTTPException(status_code=404,
                            detail=f'template {template_name} not found.') from e
    if not isinstance(context, Mapping):
        raise HTTPException(status_code=500,
                            detail=f'context is not mapping type.') from e

    try:
        text = template.get_def(def_name).render(request=request, app=request.app, **context)
    except Exception:
        translate = True
        if translate:
            template.uri = template_name
            raise TemplateError(template)
        else:
            raise

    return text
