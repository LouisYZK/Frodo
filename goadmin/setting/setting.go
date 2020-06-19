package setting

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"strings"

	"github.com/go-ini/ini"
)

var (
	Cfg *ini.File

	DbUsername       string
	DbHost           string
	DbPwd            string
	DbPort           string
	DbDatabase       string
	DbCharset        string
	JwtSecret        string
	RedisURL         string
	RedisPort        string
	RedisHost        string
	PythonServerPort string
	PythonServerHost string
	WebPort          string
)

func ListDir(dirPth string, suffix string) (files []string, err error) {
	files = make([]string, 0, 10)
	dir, err := ioutil.ReadDir(dirPth)
	if err != nil {
		return nil, err
	}
	PthSep := string(os.PathSeparator)
	suffix = strings.ToUpper(suffix) //忽略后缀匹配的大小写
	for _, fi := range dir {
		if fi.IsDir() { // 忽略目录
			continue
		}
		if strings.HasSuffix(strings.ToUpper(fi.Name()), suffix) { //匹配文件
			files = append(files, dirPth+PthSep+fi.Name())
		}
	}
	return files, nil
}

func init() {
	var err error
	Cfg, err = ini.Load("config.ini.model")

	fmt.Println(ListDir(".", ""))
	if err != nil {
		log.Fatalf("Fail to parse 'conf/app.ini': %v", err)
	}
	DbUsername = Cfg.Section("database").Key("username").MustString("")
	DbPwd = Cfg.Section("database").Key("password").MustString("")
	DbPort = Cfg.Section("database").Key("port").MustString("")
	DbDatabase = Cfg.Section("database").Key("db").MustString("")
	DbCharset = Cfg.Section("database").Key("charset").MustString("")
	DbHost = Cfg.Section("database").Key("host").MustString("")

	JwtSecret = Cfg.Section("security").Key("jwt_secret").MustString("")

	RedisURL = Cfg.Section("redis").Key("redis_url").MustString("")
	RedisPort = Cfg.Section("redis").Key("port").MustString("")
	RedisHost = Cfg.Section("redis").Key("host").MustString("")
	PythonServerHost = Cfg.Section("server").Key("python").MustString("")
	PythonServerPort = Cfg.Section("port").Key("fastapi").MustString("")

	WebPort = Cfg.Section("port").Key("golang").MustString("")
}
