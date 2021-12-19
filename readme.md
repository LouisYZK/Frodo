[zh-中文](./readme_zh.md)

# Frodo V2.0
![python-version](https://img.shields.io/badge/python-3.7-green)
![Frodo-v2.0](https://img.shields.io/badge/tag-v2.0-blue)

Frodo is a personal blog using python and golang's **asynchronous** technique.

[Document(only Chinese now and Eng version will be soon)~](http://zhikai.pro/html/index.html)

![](http://zhikai.pro/static/img/frodo-min.gif)
## Overview

v2.0 add new language golang to rebuild the `admin` module's api, blog's front end page is still rendered by python.

### techniques selection

Frodo's technique selection is as follows:

- Blog Page Web Framework：`python/fastapi`
- Page ORM: `sqlalchemy` + `encode/databases` (as FastAPI recommends)
- Page Templates: `Mako/FastAPI-Mako`
- python async web service: `asgi/uvicorn`
- Admin Web Framework: `golang/gin`
- Addmin ORM: `gorm`
- Admin UI: [vue-element-admin](https://github.com/PanJiaChen/vue-element-admin)
- KV database: `redis`
- cached: `redis/memcached`
- reverse web proxy: `nginx`
- data persistence: `mysql`
- database migration: `alembic`
- authentication: `JWT`
- python type hints: `pydantic`

### features

- Admin platform supports posts, users and topics Create, Read, Update, Delete (CRUD)
- Admin posts editor suport preview and markdown
- Page supports programming lang highlights, Latex Math equations and TOC.
- Blog has posts global searching
- Visitors' react and comments based on Github Auth
- Batch posts in markdown or HEXO exportation
- Customize your persion partail diplay
- Activities like twitter
- Docker deploments

### why fastapi?

`fastapi` is a python web framework gathering features of flask, django. It supports both asynchronous checkpoints and normal blog ways. Using `uvicorn` to support eventloop make fastapi faster. More excellent feature is the pydantic and data scheme, encouraging to follow the OpenAPI rules, the `swagger-docs` will be generated automatically.

### why golang?
python service use asynchornous asyncio ecosystem. Golang supports asynchronous primitively. `goroutine` is like python's corouine can be controlled by eventloop. Admin's api is very easy to rebuilt via golang.

### Display：
Admin paltform：

![](doc/images/admin.png)

Blog Pages：

![](doc/images/index.png)

Activity：

![](doc/images/activity.png)


## Setup

### Docker deployment (Recommends!)
The following are based on `docker-compose-1.25.5`, `MacOS-Majave 15.15` version.

Other verion could be fine as well (not tested!)

#### Modify the config
`python_web/config/config.ini.model` and `goadmin/config.ini.model`,

```
[global]
debug = True
author = yzk
site_title = Zhikai-Yang Space
host_path = localhost:9080 ## alter this to your web port, like localhost for example
```
Note: the `host_path` in config file should be with ip:port


The rest configuration is every service's port, if some port are not accessed, please modify the corresponding config in `nginx.conf`, `docker-compose.yml`.

#### build images

```
git clone https://github.com/LouisYZK/Frodo
cd Frodo
sh build.sh
```
There are two web images(python and golang) should be built for a while, if there are some errors about network, you can rebuild it.

**Note: Raspberry Pi images' building**
Raspberry Pi using linux/arm64, related docker-compose configuration are in `docker-compose-arm.yml`, some images that only can run on x86 should be replaced. Some bugs also fixed in arm64.

#### Start
```
docker-compose up ## start the whole servcie
```

It will start five service in docker-compose in some order:

- mysql
- redis
- python_web
- golang_web
- nginx

You can use `docker-compose ps ` to see wether all service are initailizaed correctly, if some service's status are `Exited` or other errors, please check the start logs and figure out the failure reasons. 

Please issue me if the errors are about the program itself!

#### Usage 
If start successfully, you should create an admin user firstly:

```
docker exec -it $(docker ps | grep frodo/pyweb | awk '{print $1}') python manage.py adduser
```
confirm the usernam and password according to the hints


then, you can visit `<host_ip>:<nginx_server_port>/admin`, for example `localhost:9080/admin` on local PC. Using the accounts you've just created to enter the admin platform.

You can creating some posts for test, and visit `localhost:9080` to see its performance.

User's custome partial config is in `python_web/config.yaml`, modify it and it will work without docker-compose restartinf.


#### Environment Test
There are some os already testing without errors

- [x] Ubuntu LTS 16.06 | x86_64
- [x] MacOS Majave 15 | x86_64
- [x] Raspberry 4b Debian 10 | arm64/v8 ...
- [ ] Windows ...


Welcom to deploy Frodo on your device!~ And issue me for any problems!~



## For developers
The api docs are generated automically in `:/docs`, it can be tested directly. 

I'm sorry that developing documents only in Chinese version currently.


  
