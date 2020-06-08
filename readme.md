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

### 效果：
后台内容管理系统：

![](doc/images/admin.png)

博客页面：

![]((doc/images/index.png)

动态页面：

![]((doc/images/activity.png)


## 如何使用？
### 本地部署
依赖要求
- python >=3.7
- mysql
- redis
- Unbuntu/MacOS (Windows请看Docker版本部署)

首先clone项目
```bash
git clone https://github.com/LouisYZK/Frodo
```
创建并进入python虚拟环境，请使用本地任意大于3.7版本的python创建
```
cd Frodo
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```
如果没有安装virtualenv 先pip安装
```
pip install virtualenv
```
修改数据库配置，初始化数据库。(确保mysql与redis都已运行)

修改config/config.ini.model
```
username = 
password = 
port = 3306
db = fast_blog
charset = utf8
```
然后运行脚本使用alembic 创建表与迁移
```
bash migrate.sh
```
然后创建你的用户
```
python manage.py adduser
```
根据提示输入用户名密码等就ok， 之后就可以启动项目了
```
bash start.sh
```
成功启动后（输出信息不报错），首先访问`localhost:8001/admin` 登进管理后台创建几篇文章。或使用
```
python manage.py hexo_export.py --dir xx --uname
```
进行markdown文章的批量导入。随后访问`localhost:8001`正常的话可以看到界面。

`动态功能` 需要先去`admin`下登录，然后动态页面才会出现发送动态的输入表单。

此外，`localhost:8001/docs` 是项目所有的API文档和调试入口，这是`fastapi`自动生成的，如果你在开发时严格执行`OpenAPI` 规范，那么这份文档可以直接输出供他人参考。
 
### Docker部署

## 参考
项目的架构和功能设计很多参考了dongweiming的项目 [lyana](https://github.com/dongweiming/lyanna).

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
| api/status | POST | text, url, fids = ["png", ...] | r, msg, activity.id, activity.layout, activity.n_comments, activity.n_likes, activity.created_at, activity.can_comment, activity.attachments.\*.layout, activity.attachments.\*.url, activity.attachments.\*.title, activity.attachments.*.size |

## ToDo
- [x] 用户模块及认证模块完成 2020-05-17
- [x] 后台API调通 2020-05-20
- [x] 前后台联通 2020-05-24
- [x] 评论模块（Github认证） 2020-05-27
- [x] Hexo文章批量迁移 2020-05-28
- [x] 反馈模块 2020-05-29
- [x] 加入缓存（统一用redis) 2020-05-31 Changed a lot
- [x] 阅读量 (require: cached) 2020-05-31
- [x] 动态模块 (Activity) 最后的功能模块 2020-06-02
- [ ] ~~动态集成评论与反馈 _放弃不做了，没意义且麻烦_~~
- [x] 本地部署测试与文档
- [ ] Golang重写后台部分API
- [ ] Docker虚拟化部署
- [ ] 整体迁移至Rowsberry
- [ ] 自动化部署 使用 Ansible
- [ ] 更换前端 (require: Modify Hexo Theme to Mako) 延后
- [ ] 文档和心得 


  