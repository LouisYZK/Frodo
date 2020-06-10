package models

type UserBase struct {
	Model
	Email  string `json:"email"`
	Name   string `json:"name"`
	Avatar string `json:"avatar"`
	Active bool   `json:"active"`
}

type UserCreate struct {
	UserBase
	Password string `json:"password"`
}

type User struct {
	UserBase
	AvatarUrl string `json:"avatar_url"`
}

func GetUsers(pageNum int, pageSize int, maps interface{}) (users []User) {
	db.Where(maps).Offset(pageNum).Limit(pageSize).Find(&users)
	return
}

func GetUsersTotal(maps interface{}) (count int) {
	db.Model(&User{}).Where(maps).Count(&count)
	return
}

func GetUserById(id int) (user User) {
	db.Where("id=?", id).First(&user)
	user.AvatarUrl = "/static/upload/" + user.Avatar
	return
}

func CreateUser(data map[string]interface{}) bool {
	db.Create(&UserCreate{
		Email:    data["email"].(string),
		Name:     data["name"].(string),
		Avatar:   data["avatar"].(string),
		Password: data["password"].(string),
		Active:   data["active"].(bool),
	})
	return true
}
