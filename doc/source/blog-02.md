# 通信篇 模板、增删改查与认证
> Frodo的第一个版本已经实现了，在下一个版本前，我将目前的开发思路整理成三篇文章，分别是数据篇、通信篇、异步篇。



> 本篇就来到实现具体功能的逻辑流程了，在Web应用汇总，我个人更倾向于将业务流程成为「通信」。因为是整个流程就是后台将数据组织加工发往前端，这个过程协议可以不同（http(s), websocket）, 方法可能不同（rcp, ajax, mq）, 返回的内容格式不同（json, xml, html(templates), 早年的Flash等）; 刚才讲的是前后台通信，其实逻辑模块间、进程间甚至是后续的容器间都涉及到通信的问题。本篇先介绍Web通信的核心，前后台通信。

## 模板技术与前后端分离
- 模板技术: 本世纪头十年广泛采用的Web技术，他有更有名的称呼`MVC`模式。核心思想是在html模板中使用后端代码写入数据，模板引擎会将渲染后html返回。`Django`内嵌了这种技术，python其他框架需要依赖`jinjia`,`Mako`等单独模板。其他语言如java的`JSP`也是采用此模式。他的特点是操作直接，直接在需要的地方写对应的数据。还可以直接使用后端语言在页面写逻辑，开发速度快。但缺点也很明显，前后端严重耦合，维护困难，不适合大型项目。
    - 协议: http
    - 方法: 均可
    - 内容: html(templates)

- 前后端分离: 当下主流模式，当项目越来越大，前端工程化的需求催生了`webpack`工具。随后`Vue`,`React`,`Angular`框架专注`MVVC`模式，也就是只向后端拿数据，渲染和业务逻辑放进前端框架中。这样前后端开发人员可以最大程度的分离。
    - 协议：均可
    - 方法: 均可
    - 内容: json/xml

## Mako模板和他的朋友FastAPI-Mako
Frodo使用模板来做博客的展示前台，考虑的是这部分页面少、逻辑简单、后端人员方便维护，模板完全够用。_没有过时的技术，只有合不合适的技术_。

`Mako`是python主流模板之一，他的原生接口其实可以直接使用，但有些重复的逻辑需要我们包装一下：

- 模板中固定需要的几个上下文变量
    - 请求对象（后端框架使用的request对象，在`Flask`,`Django`,`fastapi`中都存在），模板需要用到他的一些方法和属性，如反向寻址`request.url_for()`, `request.host`,甚至是`request.Session`中的内容
    - 请求上下文 context (主要指body，接触过Web开发的朋友都能列举出主要的请求体：Formdata, QueryParam, PathParam, 这些在模板中可能会用到)
    - 返回上下文 (不用封装叶涛提供)
- 模板文件自动寻址
- 静态文件寻址
- 模板异常处理

同`Flask`一样，`fastapi`的路由也是函数式的，为了将上述模板功能封装进路由函数，直接的做法是借助python的装饰器。最终高达到下述的效果：

```python
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from models import cache, Post
from ext import mako

@router.get('/archives', name='archives', response_class=HTMLResponse)
@mako.template('archives.html') # 指定模板文件名称
@cache(MC_KEY_ARCHIVES)
async def archives(request: Request): # 需要显示地传递 Request
    post_data = await Post.async_filter(status=Post.STATUS_ONLINE)
    post_obj = [Post(**p) for p in post_data]
    post_obj = sorted(post_obj, key=lambda p: p.created_at, reverse=True)
    rv = dict()
    for year, items in groupby(post_obj, lambda x: x.created_at.year):
        if year in rv: rv[year].extend(list(items))
        else: rv[year] = list(items)
    archives = sorted(rv.items(), key=lambda x: x[0], reverse=True)
    # 只返回上下文
    return {'archives': archives}
```
其实很好理解，唯一要说明的是为什么要显示地传递`request`, `fastapi`最大程度上避免传递`request`, 这一点和`Flask`的想法是相同的，利用Local线程栈完全可以做到区别不同请求的上下文。但模板中需要经常反向寻址，类似于：

```html
% for year, posts in archives:
  <h3 class="archive-year-wrap">
      <a href="${ request.url_for('archives', year=year) }" class="archive-year">
      ${ year }
    </a>
  </h3>
% endfor
```

`@mako`简单装饰器完整在LouisYZK/FastAPI-Mako, 感兴趣的朋友可以看看。

此外还有`@cached`装饰器，他是将函数的返回结果模板缓存，如果当前页面的数据不发生变化的话下次访问将直接从redis拿数据，详细的逻辑将在下面CRUD逻辑中介绍。

## CRUD的通信逻辑
本节是针对所有的数据模型讲述的，个别的如`Posts`,`Activity`的数据存储方式有多重，他们需要的trick多一些。而所有数据的操作都遵循下列流程：

![](https://pic.downk.cc/item/5ee0a928c2a9a83be58bfdc1.jpg)

控制用例中的`DataModel` 就是在数据篇中设计的数据类，他们有若干方法处理CRUD的需求，其中最最重要的两点：

- 生成操作的SQL
- 生成KV数据库缓存使用的 key

上述两点均使用了一些`sqlalchemy`和python装饰器的一点trick。大家可以重点参考源码`models/base.py` 和 `models/mc.py`. 

非常值得一提的是更新删除缓存的实现：

```python
## mc.py中的clear_mc方法
async def clear_mc(*keys):
    redis = await get_redis()
    print(f'Clear cached: {keys}')
    assert redis is not None
    await asyncio.gather(*[redis.delete(k) for k in keys],
                        return_exceptions=True)

## base类中的__flush__方法
from models.mc import clear_mc
@classmethod
async def __flush__(cls, target):
    await asyncio.gather(
        clear_mc(MC_KEY_ITEM_BY_ID % (target.__class__.__name__, target.id)),
        target.clear_mc(), return_exceptions=True
    )

## target是具体数据实例，他们重写clear_mc()方法，用于删除指定不同的key, 例如下面的Post类的重写：
async def clear_mc(self):
    keys = [
        MC_KEY_FEED, MC_KEY_SITEMAP, MC_KEY_SEARCH, MC_KEY_ARCHIVES,
        MC_KEY_TAGS, MC_KEY_RELATED % (self.id, 4),
        MC_KEY_POST_BY_SLUG % self.slug,
        MC_KEY_ARCHIVE % self.created_at.year
    ]
    for i in [True, False]:
        keys.append(MC_KEY_ALL_POSTS % i)
    for tag in await self.tags:
        keys.append(MC_KEY_TAG % tag.id)
    await clear_mc(*keys)
```

这样就确保每次的创建、更新、删除数据能把相关的缓存都删除，保持数据的一致性。你可能注意到了，删除缓存的操作是可等待的(awaitable)，这意味着异步可以在这里发挥优势实现并发。因此我们看到了`asyncio.gather(*coros)`的使用，他可以并发地删除多个key，因为redis创建了连接池，这样不使用多线程，`asyncio`就是这样实现io并发的。（其实这点应该在异步 篇介绍的，不过这点很重要）。

## 认证
认证的需求来自两个：

- 内容管理系统后台只能由博客拥有者进行数据操作，如博客的发布、密码的修改等。

- 访问者评论需要验证身份。

### 管理员的认证--使用JWT
JWT是目前广泛使用的验证方式之一，他比cookie的优势可以参考相关文章。而`fastapi`已经内嵌了对于JWT的支持，我们使用他来验证非常方便。

在讲具体实现前，还是得先想明白他的通信逻辑：

![](https://pic.downk.cc/item/5ee0ad20c2a9a83be5922c14.jpg)

上述流程表示login的逻辑以及访问需要验证API的一般逻辑。大家发现问题了嘛？`Token`在哪里存储呢？

> Token 存在哪里呢？ 服务器生成Token客户端接收，下次请求要带上他。这种经常使用且小体积的数据直接存储在内存最合适。放在程序语言中少不了要共享全局变量，例如`multiprocess.Value`就是解决此问题的。但异步是针对事件循环来研究的，没有线程进程的概念，此时`contextvar`是专门解决异步的变量共享问题的，需要python大于3.7

`fastapi` 帮我们维护此Token，只需要简单的定义如下：

```python
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth')
```

意思是Token的生成路径为`/auth`，同时`oauth2_scheme`形就作为全局依赖的token来源, 每当接口需要使用Token时仅需：

```python
@router.get('/users')
async def list_users(token: str = Depends(oauth2_scheme)) -> schemas.CommonResponse:
    users: list = await User.async_all()
    users = [schemas.User(**u) for u in users]
    return {'items': users, 'total': len(users)}
```

`Depends` 是fastapi的特色，直接写在接口函数的参数里，可以在请求前执行一些逻辑，类似中间件。这里的逻辑就是检查请求头是否带有`Auth: Bear+Token`, 如没有就不能发出此请求。

Token的生成逻辑在login接口完成，这差不多是`Frodo`最复杂的逻辑了：

```python
@app.post('/auth')
async def login(req: Request, username: str=Form(...), password: str=Form(...)):
    user_auth: schemas.User = \
            await user.authenticate_user(username, password)
    if not user_auth:
        raise HTTPException(status_code=400, 
                            detail='Incorrect User Auth.')
    access_token_expires = timedelta(
        minutes=int(config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    access_token = await user.create_access_token(
                        data={'sub': user_auth.name},
                        expires_delta=access_token_expires)
    return {
        'access_token': access_token,
        'refresh_token': access_token,
        'token_type': 'bearer'
    }
```

基本按照本节时序图执行。
### 访问认证--使用Session
访问认证有很多，受博客内容所限，访问Frodo的应该都有Github, 因此采用他认证，逻辑如下：

![](https://pic.downk.cc/item/5ee0b167c2a9a83be597e7e6.jpg)

整个逻辑很简单，遵循Github的认证逻辑，换种方式比如微信扫码就要换一套。注意一下跳转的url即可。同时存储访客的信息就不使用`JWT`了，因为不限制过时等，session的cookie最直接。

```python
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
    ## 使用session存储
    request.session['github_user'] = rv
    return RedirectResponse(request.session.get('post_url'))
```

注意`fastapi` 开启session需要加入中间件

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key='YOUR KEY')
```

`starlette`是什么东西？ 不是`fastapi`吗？ 简单讲`starlette`与`fastapi`的关系就跟`werkzurg`和`Flask`的关系一样，WSGI 和 ASGI的区别，现在ASGI的思路就是超越WSGI，当然自己也要搞一套基本标准和工具库。

Fine, 通信逻辑基本上就是这些，Frodo使用到的通信模型还是很少的。下一篇「异步篇」跟通信和数据都有关系，异步博客与一般python实现的博客就区别在这里。

