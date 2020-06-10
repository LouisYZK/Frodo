package models



type User struct {
	Model
	Email    string `json:"email"`
	Name     string `json:"name"`
	Avatar   string `json:"avatar"`
	password string `json:"password"`
	active   bool   `json:"active"`
}

func GetUsers(pageNum int, pageSize int, maps interface{}) (users []User) {
	db.Where(maps).Offset(pageNum).Limit(pageSize).Find(&users)
	return
}

func GetUsersTotal(maps interface{}) (count int) {
	db.Model(&User{}).Where(maps).Count(&count)
	return
}
