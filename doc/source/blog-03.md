# 异步篇 Await Something Awaitable

> 异步篇最接近Frodo的初衷了。通信与数据的内容使用传统框架的思路是相同的。而异步思路只改变了若干场景的实现方法。

异步编程不是新鲜概念，但他并没有指定很明确的技术特点和路线。相关概念也不是很清晰，很少有文章能细致地说明白 **阻塞/非阻塞、异步/同步、并行/并发、分布式、IO多路复用、协程** 这些概念的区别与联系。这些概念在CS专业的OS、分布式系统课程中可能有设计，但具体实现层面可能鲜有涉及。具体到Python这门语言，我阅读了很多工业界、python届的工作者（或者称为pythonista们）写的文章，下面两篇是最值得阅读的：

[小白的 asyncio ：原理、源码 到实现（1） - 闲谈后的文章 - 知乎](https://zhuanlan.zhihu.com/p/64991670)； 当然标题是作者在自谦。该文作者结合CPython中asyncio标准源码、函数栈帧的源码和python函数上下文源码实现讲述了python异步的设计原理，并手写了一个简易版的事件循环和asyncio-future对象。

[深入理解 Python 异步编程（上）](https://mp.weixin.qq.com/s/GgamzHPyZuSg45LoJKsofA)；这篇文章写于2017年，当时asyncio还没成为标准库。这篇文章大篇幅使用python和linux的epoll接口一步步实现了单线程异步IO，最后引出了asyncio的事件循环，证实了其便捷性。作者规划还有中下篇讲述asyncio的原理，可是目前还没等到下文。作者安放文章代码的仓库已经累计了数十条催更的issue。

## 基本问题
还记得我们再「通信篇」绘制的时序图吗？用它表示一次用户执行的逻辑是没问题的，但实际实现中，我们真的能这样写代码吗？这里有两个基本问题：

- 并发访问问题，如何实现多人同时访问你的博客web进程？

- 如何避免io阻塞，从而充分利用cpu的时间片？

第一个问题做过web开发的都很熟悉了，他的解决方案很多，因为这是软件发展中必须面对的问题：

- os级别，io多路复用机制，成熟的为linux的epoll机制，`nginx`便是基于此实现访问并发。

- 编程语言使用多线程解决，以`Flask`为例，使用本地线程解决线程安全问题。

- 编程语言使用异步编程解决，以`nodejs`为例，`promise`+回调的方式。python就是以`asyncio`为代表的异步生态圈。

第二个问题其实跟第一个问题是一个意思，把对象换成cpu即可。`Frodo`解决第一个问题使用的是类似asyncio事件循环的`uvloop`循环，他包装成了一个机遇`ASGI`协议的web服务器`uvicorn`,他可以启动多个`ASGI`标准写的app，内置一套事件循环实现并发访问。

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

重点是`Frodo`对于第二个问题的解决，这些都是在程序细节中体现出的。

## 问题分析：哪里存在IO阻塞
我们拿「通信篇」中CRUD的通信逻辑举例，我们先标注出IO阻塞的地方, 然后对应到程序设计中的环节，再来思考在实现中怎么解决。

![](https://pic.downk.cc/item/5ee3542ec2a9a83be57147cf.png)

图中标注出了三类io场景，并有的是串行的需求，有的是并发（可以并发）的需求。我来分别解释下：

- _第一类：_ 网络的连接和断开，http是基于tcp的可靠传输协议，建立连接的过程也是耗时的io操作。数据库的连接是网络连接或套接字文件读写类的链接，也是io耗时的。这些代码主要在web中的checkpoin函数，在`Frodo`的`views`目录下。

- _第二类：_ 通信异步是指客户端发送请求，等待数据准备好到返回的过程，这部分等到的时间其实是后端的数据io操作，cpu不应被这段时间占用。这部分代码在`Frodo`的`mdoels`下。

- _第三类：_ 数据异步是指跟数据库操作等待数据返回所需的时间消耗。这部分时间也应该还给cpu。

上述的很多场景必须是串行完成的，比如建立数据库连接-->数据操作-->断开连接。也有一些场景（主要是不涉及数据一致性的场景）可以是并行的，如缓存的更新与删除，因为KV数据库不涉及关系的联立，可以并行地删除。

## 解决方案

### 第一类：连接耗时
数据库的连接与退出同步中都会想到使用带`with`关键字的连接池，异步为了这一连接过程可以「被等待」或者说交出执行权给主程序，需要使用`async`关键字包装一下，并实现异步上下文的方法`__aenter__`, `__aexit__`.

```python
import databases

class AioDataBase():
    async def __aenter__(self):
        db = databases.Database(DB_URL.replace('+pymysql', ''))
        await db.connect()
        self.db = db
        return db

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            traceback.print_exc()
        await self.db.disconnect()
```

事实上，`aiomysql`已经帮助我们实现了类似的功能，但很遗憾`aiomysql`不能和`sqlalchemy`配套使用，`database`是一个简单的异步的数据库驱动引擎，能执行`sqlalchemy`生成的sql。

### 第二类：通信耗时
这点能否异步直觉决定了web应用的响应速度，异步下的checkpoint函数本身为`async def `关键字的协程，再由`uvloop`调度。对于此类函数的要求是对于阻塞操作一律使用`await`等待，看个例子：

```python
@app.post('/auth')
async def login(req: Request, username: str=Form(...), password: str=Form(...)):
    user_auth: schemas.User = \
            ## 涉及到IO的函数需要等待
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
    return { ... }

async def authenticate_user(
        username: str, password: str) -> schemas.User:
    user = await User.async_first(name=username)
    user = schemas.UserAuth(**user)
    if not user: return False
    if not verify_password(password, user.password): return False
    return user
```

你可能注意到了有些函数如`verify_password`并没有等待他，因为他是计算任务，不可被等待。我们只需按照逻辑把io耗时操作等待即可。

### 第三类：数据操作耗时
这体现在异步`ORM`方法的设计上，`database` + `sqlalchemy`的实现范例如下：

```python
@classmethod
async def asave(cls, *args, **kwargs):
    '''  update  '''
    table = cls.__table__
    id = kwargs.pop('id')
    async with AioDataBase() as db:
        query = table.update().\
                        where(table.c.id==id).\
                        values(**kwargs)
        ## 等待1： 执行sql语句
        rv = await db.execute(query=query)
    ## 等待2： 拿取数据构造对象
    obj = cls(**(await cls.async_first(id=id)))
    ## 等待3： 清除对象涉及的缓存
    await cls.__flush__(obj)
    return rv
```

以更新数据数据为例，涉及到的等待。同步的ORM框架像`pymysql`在`db.execute(...)`这类方法上式不可以被等待的，直接是阻塞的，异步的写法里要等待他的结果，带来的好处便是等待的时间执行权归还主程序，使其可以处理其他事务。

### 并行的实现
异步下的并行是指很多io操作并不涉及数据一致性，可以并行处理，比如删除没有关系的数据，查询若干数据，更新没有关系的数据等，这些都可以并行。异步中也允许这些并行，借助`asycio.gather(*coros)`方法实现，这个方法将传递进去的协程都放入事件循环队列，逐个执行类似`coro.send(None)`的操作，因为协程立马退出，所以所有协程可以立马「同时」被唤醒等待，达到并行的效果。

## 类设计中使用的tricks
本节的内容是在使用python异步中的一些小技巧，可以帮助我们实现更好的设计。

### 将类的@property属性序列化
序列化对象很常见，尤其是想在缓存中存储对象时需要序列化。对象的有些属性是用异步`@property`完成的，跟其他属性不同，他们需要特殊的调用：

```python
class Post(BaseModel):
    ...
    @property
    async def html_content(self):
        content = await self.content
        if not content:
            return ''
        return markdown(content)

```
这个`property`有些是异步的，每次使用此属性时都需要`content = await post.html_content`, 而不带`async`和`await`的属性可以直接访问`content = post.html_content`。 

这就给我们的序列化方法带来了麻烦。 我们想让类拥有一个知道自己有哪些异步property的功能，从而能在`BaseModel`中实现统一的序列化方法（在子类分别实现序列化方法是不现实的）。

让类附加一个`partials`的属性，存储需要等待的`property`， 对于python，控制类的行为（注意是类的创建行为，不是实例的创建行为）需要改变其元类，我们设计一个叫`PropertyHolder`的元类，让他的行为控制所有数据类的生成：

```python
class PropertyHolder(type):
    """
    We want to make our class with som useful properties 
    and filter the private properties.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        new_cls.property_fields = []

        for attr in list(attrs) + sum([list(vars(base))
                                       for base in bases], []):
            if attr.startswith('_') or attr in IGNORE_ATTRS:
                continue
            if isinstance(getattr(new_cls, attr), property):
                new_cls.property_fields.append(attr)
        return new_cls
```
他的功能是过滤出我们所需要的`@property`, 直接付给类的`properties`属性。

接下来就是改变`BaseModel`的生成元类：

```python
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

class ModelMeta(Base.__class__, PropertyHolder):
    ...


class BaseModel(Base, metaclass=ModelMeta):
    ...
```

`Base`是ORM的基类，他本身的元类也被改变（意味着不是type）,如果直接改变它则会让我们的数据类型丧失ORM的功能，两全其美的办法是创建一个新的类同时继承`Base`和`PropertyHolder`, 使这个类成为新的混合元类。（_好绕啊，这里的套娃现象我也不想的，我会慢慢找到更好的方案的..._）。

> tricks: 类的元类如何拿到？ 调用`cls.__class__` 获取他基于的元类。记住，python中类本身也是对象。他的创建也是受控制的。

###  关于fastapi
好了，`Frodo`第一个版本的核心设计思路已经介绍完了，前面的叙述中，我很少提`fastapi`，因为异步web本身和框架是没关系的，这套内容换成`sanic`,`aiohttp`,`tornado`甚至是`Django`都是一样的，只是具体的实现手段不同，比如`Django`的异步是基于他自己设计的`channel`实现的。

但`fastapi`也有他的特别之处，设计思想兼容并蓄，也思考了很多，在开发中我强烈推荐使用的几个地方：

- 数据模式`schema`的设计，配套`pydantic`的类型检查，让python这门动态语言变得更加可读、调试更加容易、语法更加规范，我相信这是未来的趋势。

- `Depends`的设计，我们曾想过把复用的逻辑封装成类、函数、装饰器，但`fastapi`直接在参数上做文章，令我惊讶，他在参数上就代替了上下文、多参数、表单参数、认证参数等。

- 兼容同步写法，包含`WSGI`，使用同步的技术库搭配`fastapi`完全没问题，他允许同步函数的存在，原因便是他基于的`ASGI`认为自己是`WSGI`的超集，应当兼容两种写法。

- 配套swagger-doc, 后端福利，使得你不需要花费时间学习OpenAPI 语法便可顺利做出前后端人员都能用、都能理解的调试平台和文档，省时省力。


> Frodo的三篇介绍到此就完结了，靠课余、科研时间之外的空隙完成的项目难免漏洞百出。但一个月的战线后总算是完成了第一个版本。未来的目标是星辰大海，新语言的加入、多服务的拆分、虚拟化部署都需要时间的检验，努力吧~！



