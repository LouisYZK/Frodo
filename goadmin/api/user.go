package api

import (
	"github.com/gin-gonic/gin"
)

func GetUsers(c *gin.Context) {
	c.JSON(200, gin.H{
		"msg": "ok",
	})
}