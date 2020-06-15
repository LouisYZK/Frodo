package models

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"goadmin/setting"

	jwt "github.com/dgrijalva/jwt-go"
	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
)

var jwtSecret = []byte(setting.JwtSecret)

type Claims struct {
	Username string `json:"username"`
	Password string `json:"password"`
	jwt.StandardClaims
}

func GenerateToken(username, password string) (string, error) {
	nowTime := time.Now()
	expireTime := nowTime.Add(3 * time.Hour)
	claims := Claims{
		username,
		password,
		jwt.StandardClaims{
			ExpiresAt: expireTime.Unix(),
			Issuer:    "gin-blog",
		},
	}

	tokenClaims := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	token, err := tokenClaims.SignedString(jwtSecret)

	return token, err
}

func ParseToken(token string) (*Claims, error) {
	tokenClaims, err := jwt.ParseWithClaims(token, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		return jwtSecret, nil
	})

	if tokenClaims != nil {
		if claims, ok := tokenClaims.Claims.(*Claims); ok && tokenClaims.Valid {
			return claims, nil
		}
	}

	return nil, err
}

func hashPassword(plain_pwd string) string {
	hash, err := bcrypt.GenerateFromPassword([]byte(plain_pwd), bcrypt.DefaultCost)
	if err != nil {
		fmt.Println(err)
	}
	encodePW := string(hash)
	fmt.Println("hashed:", encodePW)
	return encodePW
}

func checkPassword(plainPwd, hashPwd string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(hashPwd), []byte(plainPwd))
	if err != nil {
		return false
	} else {
		return true
	}
}

func CheckAuth(username, password string) bool {
	user := new(User)
	DB.Select("password").Where(User{Name: username}).First(user)
	hashedPwd := user.Password
	return checkPassword(password, hashedPwd)
}

func JWT() gin.HandlerFunc {
	return func(c *gin.Context) {
		var code int
		var data interface{}

		code = 200
		token := c.GetHeader("Authorization")
		if token == "" {
			code = 401
		} else {
			jwtToken := strings.Split(token, " ")[1]
			claims, err := ParseToken(jwtToken)
			if err != nil {
				code = 401
			} else if time.Now().Unix() > claims.ExpiresAt {
				code = 401
			}
		}

		if code != 200 {
			c.JSON(http.StatusUnauthorized, gin.H{
				"code": code,
				"msg":  "not authorization",
				"data": data,
			})

			c.Abort()
			return
		}
	}
}
