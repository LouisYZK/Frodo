# 拥抱Golang, go~!


![](https://pic.downk.cc/item/5ee73bebc2a9a83be523ff9f.jpg)

> Frodo-v2.0 没有添加新功能，而是将后端最重要的部分，后台API使用`golang`重构，python现在只负责前台模板的渲染。这样原本的单服务应用就成了多服务。本文将简介v2.0的调整思路和golang异步的特性，新版本的部署文档请参看项目地址


主要重构的模块为：

- 博文、用户、标签等的后台CRUD接口
- 缓存清理模块
- JWT认证模块

## why golang?
golang是年轻的语言，新世纪的静态语言。设计理念很好地平衡了`C++`和 `javascript/python`等动态语言的优劣，独具特色的`goroutine`设计范式旨在告别多线程式的并发。而web后台和微服务是go语言用的的最多的领域，故我将后台纯api部分拿go来重写。

我是2019年开始使用`kubernetes`时开始接触的go语言，当时项目有需求想要扩展一个k8s的api, 官方给的意见是如果想真正的contributor,最好使用golang开发。go语言的代表一定是`docker`和`kubernetes`这一最主流的容器与容器编排工具。

其次，使用go语言对我并不痛苦，他的风格介于静态和动态语言，因此你要使用指针来避免冗余的对象复制，同时你也能使用便捷的如python里的动态数据结构。比类C的好处在于他不是那么地接近底层，只需考虑必要的指针操作和类型问题。

而python也越来越多地提倡使用显示类型，在v1.0中就已经使用了类型检查，在python中虽然不能带来性能的提升，但有利于调试和对接静态语言。因此golang的语并不会带来困难。

带类型的python与golang风格十分相似：

```python
async def get_user_by_id(id: int) -> User:
    user: User = await User.async_first(id)
    return user
```

在golang中类型是强制的：

```go
func GetUsers(page int) (users []User) {
    DB.Where(...).First(&user)
    return
}
```

再来看C++, 明显的不同时类型的位置不一样:

```C
User* getUserById(int id) {
    user = User{id}
    User::first(&user)
    return user
}
```

最后，最重要的是golang的圈子如何，跟python-web比，golang可选择的余地并不是很多，但也足够用。这次选择的框架是`gin`和`gorm`都是轻量且简单的框架。

## Challenge

### golang的轮子

写习惯动态原因的人(尤其是python/js)会感觉golang数据结构的麻烦：

- `map/struct`不能动态添加新属性
- 没有`in `这一经常使用的特性
- 任意类型`interface{}`到其他类型的转换并没有那么简单
- `struct`，`map`, `json`之间的转换并不是很自然
- 值传递和地址传递时刻要注意
- 没有方便的集合运算，如交并差，如排序，如格式化生成等。
- ...

庆幸的是，go语言的开源社区做的很不错，可以直接饮用github的他人完成的包，很多轮子都有现成的实现，首先可以去 `https://godoc.org/` 去搜索官方支持的轮子，这些一般是稳定的，受官方认可的，同时可以方便地查看他们的文档。如集合运算我就使用了`goset`这个库。如果没有在官方找到，可以直接寻求github，直接引用仓库地址即可。（_感觉golang包模块很方便吗？目前看来是的，但其实坑也不少..._）

### 多服务网络结构部署

> 没想到V2.0版本麻烦最多是在部署上... 

这样我们的博客系统就有两个服务了，golang和uvicorn分别占两个端口，静态文件中做相应的调整，但因为我的部署只能暴露一个端口（因为域名问题，见下图），这样只能借助`nginx`来转发了。

![](https://pic.downk.cc/item/5ee74ab4c2a9a83be539a9d2.jpg)

上图结构有几个配置上的难点：

- 静态资源寻址、路由配置。v1.0但语言版本时比较好配置直接都映射本地地址即可。现在需要明确地分服务在nginx配置转发。同时静态资源上，也要将原先的本地地址更换为域名地址。

- golang部分功能还要调用python的服务，如「动态」的api的还是保留在python里，post的 api在golang, 而创建「文章」后需要创建动态，这时golang需要调用python的服务。（这其实很正常，很大的项目也避免不了互相通信的需要。）好在在一台机器上此问题容易解决的多。

- 等等，缓存会冲突吗？ 在「数据篇」中讲到Frodo是有缓存机制的，现在发现python的前台和golang的后台都依赖缓存，这点需要严格的key的统一来保证两个缓存数据的一致性。

## Golang的异步与并发
既然将原来python的服务换为golang, 前面提到的异步特性golang能满足吗？其实思想是一致的，只是从asycio和可等待对象变为了goroutine, 拿「博文」创建接口举例：

```go
func CreatePost(data map[string]interface{}) {
	post := new(Post)
	post.Title = data["title"].(string)
	post.Summary = data["summary"].(string)
	post.Type = data["type"].(int)
	post.CanComment = data["can_comment"].(int)
	post.AuthorID = data["author_id"].(int)
	post.Status = data["status"].(int)

	tags := data["tags"].([]string)
	content := data["content"]
	DB.Create(&post)

	fmt.Println(post)

	go post.SetProps("content", content) // go设置内容
	go post.UpdateTags(tags) // go 更新标签
	go post.Flush() // go 清除缓存
	go CreateActivity(post) // go 创建动态
}
```

可以看到连续使用了4个`go`分发不能阻塞的任务，这些都是`goroutine`, 配套的有对他们管理的通信工具和同步原语，每个`goroutine`也可以继续分发协程，如其中的更新标签：

```go
func (post *Post) UpdateTags(tagNames []string) {
	var originTags []Posttag
	var originTagNames []string

	DB.Where("post_id = ?", post.ID).Find(&originTags)
	for _, item := range originTags {
		var tag Tag
		DB.Select("name").Where("id = ?", item.TagID).First(&tag)
		originTagNames = append(originTagNames, tag.Name)
	}
	_, _, deleteTagNames, addTagNames := goset.Difference(originTagNames, tagNames)
	for _, tag := range addTagNames.([]string) {
		go CreateTags(tag)
		go CreatePostTags(post.ID, tag)
	}
	for _, tag := range deleteTagNames.([]string) {
		go DeletePostTags(post.ID, tag)
	}
}
```
golang没有类似`asyncio.gather(*coros)`式的分发，采用for循环是一样的实现。

> 目前我已经把简单的系统拆成了两个不同技术类型的服务，可以见到部署难题渐显，接下来的更新就是虚拟化解决环境依赖难题和自动化部署了~