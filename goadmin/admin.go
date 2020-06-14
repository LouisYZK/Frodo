package main

import (
	"fmt"
	"goadmin/models"
	"log"
	"net/http"
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
		AllowHeaders:     []string{"Origin", "Content-Length", "Content-Type", "Authorization"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))
	apiv1 := r.Group("/api")
	apiv1.Use(models.JWT())
	{
		apiv1.GET("/users", GetUsers)
		apiv1.GET("/user/:id", GetUserItem)
		apiv1.POST("/user/new", AddUser)
		apiv1.DELETE("/users", DeleteUser)
		apiv1.PUT("/user/:id", UpdateUser)
		apiv1.GET("/posts", ListPosts)
		apiv1.GET("/post/:id", GetPostByID)
		apiv1.GET("/tags", ListTags)
		apiv1.POST("/post/new", CreatePost)
		apiv1.PUT("/post/:id", UpdatePost)
		apiv1.DELETE("/post/:id", DeletePost)
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

func GetUserItem(c *gin.Context) {
	if c.Param("id") == "info" {
		GetUserInfo(c)
		return
	} else if c.Param("id") == "search" {
		SearchUserbyName(c)
		return
	} else {
		id := com.StrTo(c.Param("id")).MustInt()
		user := models.GetUserByID(id)
		c.JSON(200, user)
	}
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

func DeleteUser(c *gin.Context) {
	models.DeleteUser(com.StrTo(c.Query("id")).MustInt())
	c.JSON(http.StatusOK, gin.H{"msg": "delete ok"})
}

type auth struct {
	Username string `valid:"Required; MaxSize(50)" json:"username"`
	Password string `valid:"Required; MaxSize(50)" json:"password"`
}

func GetAuth(c *gin.Context) {
	valid := validation.Validation{}
	var a auth
	c.BindJSON(&a)
	ok, _ := valid.Valid(&a)
	var Token string
	code := 200
	if ok {
		isCorrect := models.CheckAuth(a.Username, a.Password)
		fmt.Println(isCorrect)
		if isCorrect {
			token, err := models.GenerateToken(a.Username, a.Password)
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

func GetUserInfo(c *gin.Context) {
	user, err := models.GetUserInfo(c.Query("token"))
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{
			"msg": "Non authorized!",
		})
	} else {
		c.JSON(http.StatusOK, user)
	}
}

func SearchUserbyName(c *gin.Context) {
	name := c.Query("name")
	var users []models.User
	name = "%" + name + "%"
	models.DB.Where("name like ?", name).Find(&users)
	c.JSON(http.StatusOK, gin.H{
		"items": users,
		"total": len(users),
	})
}

func UpdateUser(c *gin.Context) {
	data := map[string]interface{}{
		"id":       com.StrTo(c.PostForm("id")).MustInt(),
		"email":    c.DefaultPostForm("email", ""),
		"name":     c.PostForm("name"),
		"password": c.PostForm("password"),
		"avatar":   c.DefaultPostForm("avatar", ""),
		"active":   true,
	}
	user := models.UpdateUser(data)
	c.JSON(http.StatusOK, user)
}

func ListTags(c *gin.Context) {
	var tags []models.Tag
	models.DB.Find(&tags)
	var tagNames []string
	for _, tag := range tags {
		tagNames = append(tagNames, tag.Name)
	}
	c.JSON(http.StatusOK, gin.H{
		"items": tagNames,
	})
}

func ListPosts(c *gin.Context) {
	page := com.StrTo(c.Query("page")).MustInt()
	c.JSON(http.StatusOK, gin.H{
		"items": models.ListPosts(page),
		"total": models.GetPostsCount(nil),
	})
}

func GetPostByID(c *gin.Context) {
	id := com.StrTo(c.Param("id")).MustInt()
	c.JSON(http.StatusOK, models.GetPostById(id))
}

func CreatePost(c *gin.Context) {
	data := map[string]interface{}{
		"title":       c.PostForm("title"),
		"slug":        c.PostForm("slug"),
		"summary":     c.DefaultPostForm("summary", ""),
		"content":     c.PostForm("content"),
		"type":        com.StrTo(c.PostForm("type")).MustInt(),
		"can_comment": com.StrTo(c.PostForm("can_comment")).MustInt(),
		"author_id":   com.StrTo(c.PostForm("author_id")).MustInt(),
		"tags":        c.PostFormArray("tags"),
		"status":      com.StrTo(c.PostForm("status")).MustInt(),
	}
	models.CreatePost(data)
	c.JSON(http.StatusOK, gin.H{"msg": "ok"})
}

func UpdatePost(c *gin.Context) {
	id := com.StrTo(c.Param("id")).MustInt()
	data := map[string]interface{}{
		"title":       c.PostForm("title"),
		"slug":        c.PostForm("slug"),
		"summary":     c.DefaultPostForm("summary", ""),
		"content":     c.PostForm("content"),
		"type":        com.StrTo(c.PostForm("type")).MustInt(),
		"can_comment": com.StrTo(c.PostForm("can_comment")).MustInt(),
		"author_id":   com.StrTo(c.PostForm("author_id")).MustInt(),
		"tags":        c.PostFormArray("tags"),
		"status":      com.StrTo(c.PostForm("status")).MustInt(),
	}
	models.UpdatePost(id, data)
	c.JSON(http.StatusOK, gin.H{"msg": "ok"})
}

func DeletePost(c *gin.Context) {
	id := com.StrTo(c.Param("id")).MustInt()
	models.DeletePost(id)
	c.JSON(http.StatusOK, gin.H{"r": 1})
}

func main() {
	r := InitRouter()
	r.Run("0.0.0.0:8003")
}
