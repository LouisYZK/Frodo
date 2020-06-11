package models

import (
	"fmt"
	"goadmin/setting"
	"log"
	"time"

	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/mysql"
)

var db *gorm.DB

type Model struct {
	ID        int       `gorm:"primary_key" json:"id"`
	CreatedAt time.Time `json:"created_at"`
}

func init() {
	var (
		err                          error
		dbName, user, password, host string
	)

	dbName = setting.DbDatabase
	user = setting.DbUsername
	password = setting.DbPwd
	host = "localhost:" + setting.DbPort

	db, err = gorm.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=utf8&parseTime=True&loc=Local",
		user,
		password,
		host,
		dbName))

	if err != nil {
		log.Println(err)
	}
	db.SingularTable(true)
	db.LogMode(true)
	db.DB().SetMaxIdleConns(10)
	db.DB().SetMaxOpenConns(100)
}

func CloseDB() {
	defer db.Close()
}

// func GetAll(items interface{}) interface{}{
// 	db.Find(items)
// 	return items
// }

// func GetTotal(items interface{}) (count int) {
// 	db.Find(items).Count(&count)
// 	return
// }

// func First(table interface{} , id int) interface{} {
// 	db.Find(table, id)
// 	return table
// }

// func Filter(table interface{}, maps interface{}) {
// 	...
// }
