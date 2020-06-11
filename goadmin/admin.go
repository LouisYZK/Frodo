package main

import (
	"goadmin/models"
	"log"
	"time"

	"github.com/astaxie/beego/validation"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/unknwon/com"
)

func InitRouter() *gin.Engine {
	r := gin.New()

	r.Use(gin.Logger())
	r.Use(gin.Recovery())
	r.Static("/static", "../static")
	r.Use(cors.New(cors.Config{
		AllowOriginFunc:  func(origin string) bool { return true },
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "PATCH"},
		AllowHeaders:     []string{"Origin", "Content-Length", "Content-Type"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))
	apiv1 := r.Group("/api")
	{
		apiv1.GET("/users", GetUsers)
		apiv1.GET("/user/:id", GetUserById)
		apiv1.POST("/user/new", AddUser)
	}
	r.POST("/auth", GetAuth)
	return r
}

func GetUsers(c *gin.Context) {
	c.JSON(200, gin.H{
		"items": models.GetUsers(0, 10, make(map[string]interface{})),
		"total": models.GetUsersTotal(make(map[string]interface{})),
	})
}

func GetUserById(c *gin.Context) {
	id := com.StrTo(c.Param("id")).MustInt()
	user := models.GetUserById(id)
	c.JSON(200, user)
}

func AddUser(c *gin.Context) {
	data := map[string]interface{}{
		"email":    c.DefaultPostForm("email", ""),
		"name":     c.PostForm("name"),
		"password": c.PostForm("password"),
		"avatar":   c.DefaultPostForm("avatar", ""),
		"active":   true,
	}
	models.CreateUser(data)
	c.JSON(200, gin.H{"msg": "ok"})
}

type auth struct {
	Username string `valid:"Required; MaxSize(50)"`
	Password string `valid:"Required; MaxSize(50)"`
}

func GetAuth(c *gin.Context) {
	username := c.PostForm("username")
	password := c.PostForm("password")

	valid := validation.Validation{}
	a := auth{Username: username, Password: password}
	ok, _ := valid.Valid(&a)
	var Token string
	code := 200
	if ok {
		isExist := models.CheckAuth(username, password)
		if isExist {
			token, err := models.GenerateToken(username, password)
			if err != nil {
				code = 500
			} else {
				code = 200
				Token = token
			}
		} else {
			code = 404
		}
	} else {
		for _, err := range valid.Errors {
			log.Println(404, "Wrong text", err)
		}
	}
	c.JSON(code, gin.H{
		"code":          code,
		"access_token":  Token,
		"refresh_token": Token,
		"token_type":    "bearer",
	})
}

func main() {
	r := InitRouter()
	r.Run("0.0.0.0:8003")
}
