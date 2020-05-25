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

## FrontEnd Path