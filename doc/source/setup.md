# 部署

## 本地
依赖要求
- python >=3.7
- golang >=1.10
- nginx
- mysql
- redis
- Unbuntu/MacOS (Windows请看Docker版本部署)

clone项目
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
根据提示输入用户名密码等就ok

配置后台
```
cd goadmin
go mod init goadmin
```
如果报错请检查go语言是否安装成功。启动web：

```
bash start.sh
```
如果没报错则python和golang的服务都启动了，此时访问python的端口即可看到界面。

如果要在服务器部署，请修改`config.ini.model`的端口和`host_path`项。同时如需要反向代理同时修改nginx配置`nginx.conf`。

成功启动后（输出信息不报错），首先访问`localhost:8004/admin` 登进管理后台创建几篇文章。或使用
```
python manage.py hexo_export.py --dir xx --uname
```
进行markdown文章的批量导入。随后访问`localhost:8004`正常的话可以看到界面。

`动态功能` 需要先去`admin`下登录，然后动态页面才会出现发送动态的输入表单。

此外，`localhost:8001/docs` 是项目所有的API文档和调试入口，这是`fastapi`自动生成的，如果你在开发时严格执行`OpenAPI` 规范，那么这份文档可以直接输出供他人参考。
 
## Docker部署

