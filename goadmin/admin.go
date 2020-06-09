package main

import (
	"github.com/gin-gonic/gin"
	"goadmin/api"
	"goadmin/setting"
)

func InitRouter() *gin.Engine {
	r := gin.New()
	r.Use(gin.Logger())
	r.Use(gin.Recovery())
	
	apiv1 := r.Group("/api")
	{
		apiv1.GET("/users", api.GetUsers)
		apiv1.GET("/msg", func (c *gin.Context) {
			c.JSON(200, gin.H{"msg": setting.DbUsername})
		})
	}
	return r
}

func main() {
	
	r := InitRouter()
	r.Run("0.0.0.0:8004")
}