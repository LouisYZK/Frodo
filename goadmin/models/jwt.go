package models

import (
	"fmt"
	"time"

	"goadmin/setting"

	jwt "github.com/dgrijalva/jwt-go"
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
	db.Select("password").Where(User{Name: username}).First(user)
	hashedPwd := user.Password
	return checkPassword(password, hashedPwd)
}
