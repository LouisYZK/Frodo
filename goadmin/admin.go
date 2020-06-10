package main

import (
	"github.com/gin-gonic/gin"
	"goadmin/models"
	"goadmin/setting"
)

func InitRouter() *gin.Engine {
	r := gin.New()
	r.Use(gin.Logger())
	r.Use(gin.Recovery())
	r.Static("/static", "../static")
	apiv1 := r.Group("/api")
	{
		apiv1.GET("/users", GetUsers)
		// apiv1.GET("/user/:id", api.GetUserById)
		apiv1.GET("/msg", func (c *gin.Context) {
			c.JSON(200, gin.H{"msg": setting.DbUsername})
		})
	}
	return r
}

func GetUsers(c *gin.Context) {
	c.JSON(200, gin.H{
		"items": models.GetUsers(0, 10, make(map[string]interface{})),
		"total": models.GetUsersTotal(make(map[string]interface{})),
	})
}


func main() {
	r := InitRouter()
	r.Run("0.0.0.0:8004")
}