package models

import (
	"errors"
	"fmt"
	"goadmin/setting"
	"log"
	"reflect"
	"time"

	"github.com/go-redis/redis/v7"
	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/mysql"
)

var DB *gorm.DB
var RedisClient *redis.Client

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
	host = setting.DbHost + ":" + setting.DbPort

	DB, err = gorm.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=utf8&parseTime=True&loc=Local",
		user,
		password,
		host,
		dbName))

	if err != nil {
		log.Println(err)
	}
	DB.SingularTable(true)
	DB.LogMode(true)
	DB.DB().SetMaxIdleConns(10)
	DB.DB().SetMaxOpenConns(100)

	RedisClient = redis.NewClient(&redis.Options{
		Addr:     setting.RedisURL,
		DB:       0,
		Password: "",
		PoolSize: 10,
	})
}

func Contain(obj interface{}, target interface{}) (bool, error) {
	targetValue := reflect.ValueOf(target)
	switch reflect.TypeOf(target).Kind() {
	case reflect.Slice, reflect.Array:
		for i := 0; i < targetValue.Len(); i++ {
			if targetValue.Index(i).Interface() == obj {
				return true, nil
			}
		}
	case reflect.Map:
		if targetValue.MapIndex(reflect.ValueOf(obj)).IsValid() {
			return true, nil
		}
	}

	return false, errors.New("not in array")
}

func CloseDB() {
	defer DB.Close()
}
