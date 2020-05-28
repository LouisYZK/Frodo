# Frodo
Personal Blog via FastAPI.
## Overview
2019年初开始，`Fastapi` 差不多成为了python届的网红，这个号称使用了异步、最快、集各大框架之有点于一身的框架需要实践检验。 不得不说他的文档写的很迷人，除了名字中体现的性能优势外，他集合了`Flask`, `Django` 中的很多特点，又直接以restful时代下的`OpenAPI`为默认接口标准。自带集成`swagger-docs` 不论是前端或是后端调试起来都很方便。

言归正传，`Frodo`是一个使用了python异步生态开发的个人博客，使用的技术栈如下：
- Web框架：fastapi
- ORM: sqlalchemy + 异步 databases (FastAPI 推荐做法)
- KV数据库: aioredis
- 模板: Mako/FastAPI-Mako
- python类型检查: pydantic

管理后台界面参考使用 [vue-element-admin](https://github.com/PanJiaChen/vue-element-admin)

## 原型
项目的原型是根据dongweiming的项目 [lyana](https://github.com/dongweiming/lyanna) 修改完成，参考了大量的设计模式和架构。只是将其中使用到的`Sanic`和`tortoise`部分替换为fastapi的模式。

在此特向原作者感谢，这是一个十分有趣且意义十足的学习过程。

修改的思路:
- 抽取出数据组织形式和前后端API
- 重写后台管理界面API
- 重写前端模板API
  
## API
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

## ToDo
- [x] 用户模块及认证模块完成 2020-05-17
- [x] 后台API调通 2020-05-20
- [x] 前后台联通 2020-05-24
- [x] 评论模块（Github认证） 2020-05-27
- [ ] Hexo文章批量迁移
- [ ] 反馈模块
- [ ] 加入缓存（统一用redis）
- [ ] 动态模块
- [ ] 专题模块
- [ ] 更换前端
- [ ] 文档和心得