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
	DB.Where(maps).Offset(pageNum).Limit(pageSize).Find(&users)
	return
}

// GetUsersTotal get number of users
func GetUsersTotal(maps interface{}) (count int) {
	DB.Model(&User{}).Where(maps).Count(&count)
	return
}

// GetUserByID get user by id
func GetUserByID(id int) UserReturn {
	user := new(User)
	DB.Where("id=?", id).First(user)
	userReturn := UserReturn{User: *user, AvatarUrl: "/static/upload/" + user.Avatar}
	return userReturn
}

// CreateUser add new user
func CreateUser(data map[string]interface{}) bool {
	user := User{
		Email:    data["email"].(string),
		Name:     data["name"].(string),
		Avatar:   data["avatar"].(string),
		Password: hashPassword(data["password"].(string)),
		Active:   data["active"].(bool),
	}
	user.CreatedAt = time.Now()
	DB.Create(&user)
	return true
}

func UpdateUser(data map[string]interface{}) (user User) {
	DB.Where("id = ?", data["id"].(int)).First(&user)
	user.Name = data["name"].(string)
	user.Password = hashPassword(data["password"].(string))
	user.Email = data["email"].(string)
	user.Avatar = data["avatar"].(string)
	DB.Save(&user)
	return user
}

// GetUserInfo Retrun User info
func GetUserInfo(token string) (*User, error) {
	claims, err := ParseToken(token)
	if err != nil {
		return nil, err
	}

	name := claims.Username
	user := new(User)
	DB.Where("name=?", name).First(user)
	return user, err
}

// DeleteUser delete user by id
func DeleteUser(userID int) {
	user := new(User)
	DB.Where("id=?", userID).Delete(user)
}
