package models

import "time"

type User struct {
	Model
	Email    string `json:"email"`
	Name     string `json:"name"`
	Avatar   string `json:"avatar"`
	Active   bool   `json:"active"`
	Password string `json:"password"`
}

type UserReturn struct {
	User
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

func GetUserById(id int) UserReturn {
	user := new(User)
	db.Where("id=?", id).First(user)
	userReturn := UserReturn{User: *user, AvatarUrl: "/static/upload/" + user.Avatar}
	return userReturn
}

func CreateUser(data map[string]interface{}) bool {
	user := User{
		Email:    data["email"].(string),
		Name:     data["name"].(string),
		Avatar:   data["avatar"].(string),
		Password: hashPassword(data["password"].(string)),
		Active:   data["active"].(bool),
	}
	user.CreatedAt = time.Now()
	db.Create(&user)
	return true
}
