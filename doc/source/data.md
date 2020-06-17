数据篇
======================

## 简要系统分析
数据库设计是紧跟需求来的，在我本科学UML时，数据库设计是在需求分析和系统分析之后，架构设计之前的设计。但博客项目的需求比较简单，主要大需求:

- 内容管理（文章、用户、标签、评论、反馈、动态的增删改查）
- 管理员用户的验证、评论人用户的验证
- 小功能：边栏组件、归档、分类等

再简单地做一个系统分析：
- 博客前台页面（不需要认证，内容展示）
    - 博文内容
    - 博客作者
    - 标签
    - 访问量
- 管理页面（需要登录认证进行内容管理）
- 动态页面（需要认证）
- 评论（访问者需要登录认证）

接下来的工作就是根据功能需求设计前后台API，一般如果你是全栈自己开发的话，API形式可以随意些，因为后续还可以灵活调整。如果需要和前端同事合作的话，你需要严格按照restful风格编写，接口的参数、命名、方法和返回体的构造上严格体现需求。

> API 格式理应最大化地体现功能需求

前后台API的形式也取决于所用技术，Frodo前台页面是选择模板渲染的，后台是使用Vue, 那么模板就可以在页面上编程，可以实时决定上下文，可以不事先指定。

### 后台API
| url | method | params | response | info|
|  --- | --- | --- | --- | --- |
|  api/posts  |   GET | limit:1<br>page: 页面数 <br> with_tag<br>  |  {'items': [post.*.,], 'total': number}  | 查询Posts<br> 需要登录| 
|  api/posts/new| POST | FormData <br> title <br> slug<br> summary <br> content <br> is_page <br> can_comment <br> author_id <br> status| x| x|
| api/post/<post_id>| GET/PUT/DELETE| x | items.*.created_at <br> items.\*.author_id <br> items.\*.slug <br> items.\*.id <br> items.\*.title <br> items.\*.type <br> items.\*._pageview <br> items.\*.summary <br> status <br> items.\*.can_comment <br> items.\*.author_name <br> items.\*.tags.\* <br> total|需要登录|
| api/users | GET | x | {'items':[user.*.,], 'total': num} | 需要登录|
| api/user/new | POST | FormData <br>active <br> name<br>email <br>password <br> avatar: avatar.png | x | 需要登录|
| api/user/<user_id> | GET/PUT | x | user.created_at <br> user.avatar <br> user.id <br> user.active <br> user.email <br> user.name <br> user.url(/user/3/)<br> ok (true) |需要登录 |
| api/upload| POST/OPTIONS |x | x | na|
| api/user/search | GET | name | items.\*.id <br> items.\*.name | 需要登录|
| api/tags | GET | x | items.*.name |需要登录 |
| api/user/info | GET | user (token)| user{'name', 'avartar'} | 相当于current_user|
| api/get_url_info | POST | url | x | na |
| api/status | POST | text, url, fids = ["png", ...] | r, msg, activity.id, activity.layout, activity.n_comments, activity.n_likes, activity.created_at, activity.can_comment, activity.attachments.\*.layout, activity.attachments.\*.url, activity.attachments.\*.title, activity.attachments.*.size |

## 数据库设计
设计数据库就是设计表、表字段、表关系。严格上要先绘制E-R模型图，他金石停留在逻辑层面的关系图。下一步根据E-R图，结合使用的数据库类型（关系、Nosql、KV还是图数据库）设计表关系图，随后要考虑如下几个方面：

- 数据存储在哪里？
    - 小型记录数据存储在mysql （查询较快）
    - 长数据如「博客内容」查询较慢 适合存储在内存数据库
    - 分布式还是单一式存储？
- 那些是高频使用数据？
    - 经常需要做查询的
    - 需要经常累加、统计计算的
    - 经常不变化的
- 持久化方案
    - 数据库如何定期备份？
    - KV数据库的过期策略、定期存储策略

其实博客项目很多都不需要考虑，但再大的项目这些都需要考虑了。其实还应该考虑的是数据库并发访问的问题，这涉及到锁与同步机制，这部分我再`通信` 部分阐述。

思考过上述问题后，大致有如下图形：

![](https://pic.downk.cc/item/5ede0defc2a9a83be5ab1308.jpg)

上图中不同的颜色字段考虑了不同的特点，分别是：
- 数据库存储，选用mysql
- KV存储，选用redis
- 高频字段项，需要缓存选用redis或memcached

## ORM类设计模式
ORM 是简化SQL操作的产物，python将其做的最好的就是`Django`框架，主要做两件事：
- 类到数据库表的映射(通过改造元类实现，达到创建这些_类_时便有了`table`属性，注意不是类实例)
- 提供简化的面向对象的sql操作接口
### 表结构与表迁移
表结构在类中体现，Frodo使用的`sqlalchemy`是采用`Column()`类的形式。在类比较多是，建议先写一个_基类_，规定共有字段，在会面还可以规定共有方法。
```python
from sqlalchemy import Column, Integer, String, DateTime, and_, desc
@as_declarative()
class Base():
    __name__: str
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @property
    def url(self):
        return f'/{self.__class__.__name__.lower()}/{self.id}/'

    @property
    def canonical_url(self):
        pass
```
上述的基类就规定了表名称为类名称的小写。接下来可以规定一些公共字段和方法：
```python
id = Column(Integer, primary_key=True, index=True)
created_at = Column(DateTime)

@classmethod
def to_dict(cls, 
            results: Union[RowProxy, List[RowProxy]]) -> Union[List[dict], dict]:
    if not isinstance(results, list):
        return {col: val for col, val in zip(results.keys(), results)}
    list_dct = []
    for row in results:
        dct = {col: val for col, val in zip(row.keys(), row)}
        list_dct.append(dct)
    return list_dct
```

如`id`和`created_at` 都是公共字段，而`to_dict`是非常常用的序列化方法。

接下来就是单独的表，如`Post`表：
```python
class Post(BaseModel, CommentMixin, ReactMixin):
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
```
这其中是`Column`的类属性才是对应到数据库的属性，其他的是类其他功能需要而设定的。

需要注意的`Post`类重写了`created_at`字段, 这是规定默认的创建日期。
> 为什么继承的是 `Basemodel` ，这一点采用了一些元类编程方法，主要原因是异步，`Basemodel`类的设计在「异步篇」阐述。

接下来就是迁移到数据库了，你可以直接使用`sqlalchemy`的`metadata.create(engine)`，但这不利于调试，`alembic`是单独做数据库迁移管理的。把你写好的类都导入到`models/__init__.py`中：
```python
from .base import Base
from .user import User, GithubUser
from .post import Post, PostTag, Tag
from .comment import Comment
from .react import ReactItem, ReactStats
from .activity import Status, Activity
```
在`alembic`的`env.py`文件中导入`Base`, 再规定迁移产生的行为。这样后连每次修改类（增加字段、更新字段属性等）可以使用`alembic migrate`来自动迁移。

### 类设计模式
数据库表建立完成，接下来就是最重要的，编写数据类，涉及到增删改查的基本操作和类特定的一些方法。此时从「需求」到「接口」再到「类方法」的设计需要考虑如下两点：
- 语言的特性可以带来什么，比如Python类中的`@property`, `__get__`、`__call__`等特色函数能付发挥作用？
- 类设计的思考，类方法，实例方法 甚至是 虚拟方法？
- 设计模式的使用，比如Frodo使用到的Mixin模式

本篇这是从类方法的功能设计来讲的，具体实现细节牵涉到的东西，比如负责通信的一些方法细节将在「通信篇」介绍。

接下来我们都能大致地画一个图：
![](https://pic.downk.cc/item/5ede26b2c2a9a83be5d69614.png)

上图挑选了几个代表性的类设计，不同的颜色表示不同的设计思路，当然了这些都是根据需求场景来的，这一步也可以在开发过程中不断调整：

- Classmethod: 类方法，不需要实例化的方法，因为数据库字段属性都是类属性，因此很多数据操作的方法都不需要实例化，适合设计为类方法

- Property: 属性方法，适合的场景多是需要频繁访问，但又需要数据io的情况，比如很多类都依赖作者id：
```python
await cls.get_user_id()
await cls.user
```

- Cached Decorator: 需要将结果缓存在`redis`的方法使用此类装饰器，例如：
```python
@classmethod
@cache(MC_KEY_ALL_POSTS % '{with_page}')
async def get_all(cls, with_page=True):
    if with_page:
        posts = await Post.async_filter(status=Post.STATUS_ONLINE)
    else:
        posts = await Post.async_filter(status=Post.STATUS_ONLINE,
                        type=Post.TYPE_ARTICLE)
    return sorted(posts, key=lambda p: p['created_at'], reverse=True)
```
`@cache`的处理规则将在「通信篇」介绍。

- Cached Property： 需要将结果缓存在内存的方法使用此类装饰器，他的场景是在一个调用过程中需要反复使用的数据，但获取昂贵。
```python
@cached_property
async def target(self) -> dict:
    kls = None
    if self.target_kind == config.K_POST:
        kls = Post
        data = await kls.cache(ident=self.target_id)
    elif self.target_kind == config.K_STATUS:
        kls = Status
        data = await kls.cache(id=self.target_id)
    if kls is None:
        return
    return await kls(**data).to_async_dict(**data)
```
例如一个请求中需要多次使用到`await self.target` 而`target`的获取是十分昂贵的，此时可以存储在程序内存中。当然了这一特性早已进入python的标准库`functools.lri_cached`, 但还没支持异步，`@cached_property`是参考别人的项目创造的类装饰器，他的实现在`models/utils.py`.

> 总结：数据库设计是十分重要的第一步，后续API的开发效率很大程度取决于此。而数据关系到具体的语言实现又需要综合考虑场景的多种特性。

> PS: 写此文时，Frodo下一步的打算是Golang重写后台API，算是把Go真正用起来。Frodo的前端我没有全程手写，因此添加新功能模块有些困难，说到底我还只是后端工程师-.-..., 不过向全栈迈出一小步也算是进步吧~