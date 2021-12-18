package models

import (
	"bytes"
	"fmt"
	"goadmin/setting"
	"net/http"
	"strconv"
	"time"

	"github.com/athom/goset"
)

type Post struct {
	Model
	Title      string `json:"title"`
	AuthorID   int    `json:"author_id"`
	Slug       string `json:"slug"`
	Summary    string `json:"summary"`
	CanComment int    `json:"can_comment"`
	Type       int    `json:"type"`
	Status     int    `json:"status"`
}

type PostDict struct {
	Post
	Tags       []string `json:"tags"`
	Content    string   `json:"content"`
	AuthorName string   `json:"author_name"`
	Author     User     `json:"author"`
	Url        string   `json:"url"`
}

type Tag struct {
	Model
	Name string `json:"name"`
}

type Posttag struct {
	Model
	PostID int `json:"post_id"`
	TagID  int `json:"tag_id"`
}

func (post Post) GetTags() (tags []Tag) {
	var postTags []Posttag
	DB.Where("post_id = ?", post.ID).Find(&postTags)
	var tagsIDs []int
	for _, item := range postTags {
		tagID := item.TagID
		tagsIDs = append(tagsIDs, tagID)
	}
	DB.Where("id in (?)", tagsIDs).Find(&tags)
	return
}

func (post Post) PostUrl() string {
	postID := strconv.Itoa(post.ID)
	return "Post/" + postID
}

func (post *Post) GetAuthor() (user User) {
	DB.Select("id, name").Where("id = ?", post.AuthorID).First(&user)
	return
}

func (post *Post) SetProps(key string, value interface{}) {
	key = post.PostUrl() + "/props/" + key
	RedisClient.Set(key, value, 0)
}

func (post Post) GetProps(key string) interface{} {
	key = post.PostUrl() + "/props/" + key
	val, err := RedisClient.Get(key).Result()
	if err != nil {
		panic(err)
	}
	return val
}

func (post *Post) UpdateTags(tagNames []string) {
	var originTags []Posttag
	var originTagNames []string

	DB.Where("post_id = ?", post.ID).Find(&originTags)
	for _, item := range originTags {
		var tag Tag
		DB.Select("name").Where("id = ?", item.TagID).First(&tag)
		originTagNames = append(originTagNames, tag.Name)
	}
	_, _, deleteTagNames, addTagNames := goset.Difference(originTagNames, tagNames)
	for _, tag := range addTagNames.([]string) {
		HasTagID := make(chan bool)
		go CreateTags(tag, HasTagID)
		go CreatePostTags(post.ID, tag, HasTagID)
	}
	for _, tag := range deleteTagNames.([]string) {
		go DeletePostTags(post.ID, tag)
	}
}

func CreateTags(tagName string, HasTagID chan bool) {
	tag := new(Tag)
	DB.Where("name = ?", tagName).First(tag)
	if tag.ID == 0 {
		tag.Name = tagName
		DB.Create(tag)
		HasTagID <- true
	} else {
		HasTagID <- true // [YZK] bug fix at Dec 2021
	}
}

func CreatePostTags(postID int, tagName string, HasTagID chan bool) {
	for {
		select {
		case <-HasTagID:
			tag := new(Tag)
			DB.Select("id").Where("name = ?", tagName).First(tag)
			DB.Create(&Posttag{
				PostID: postID,
				TagID:  tag.ID,
			})
		default:
			time.Sleep(500 * time.Millisecond)
		}
	}
}

func DeletePostTags(postID int, tagName string) {
	tag := new(Tag)
	DB.Select("id").Where("name = ?", tagName).First(tag)
	pg := Posttag{
		PostID: postID,
		TagID:  tag.ID,
	}
	DB.Where(&pg).Find(&pg)
	if pg.ID != 0 {
		DB.Delete(&pg)
	}
}

func GetPostsCount(data interface{}) (count int) {
	DB.Model(&Post{}).Where(data).Count(&count)
	return
}

func ListPosts(page int) (postDicts []PostDict) {
	limit := 10
	offset := (page - 1) * limit
	var posts []Post
	DB.Offset(offset).Limit(limit).Order("created_at desc").Find(&posts)
	for _, item := range posts {
		author := item.GetAuthor()
		var tagNames []string
		for _, tag := range item.GetTags() {
			tagNames = append(tagNames, tag.Name)
		}
		postDicts = append(postDicts, PostDict{
			Post:       item,
			Tags:       tagNames,
			AuthorName: author.Name,
		})
	}
	return
}

func GetPostById(postId int) (post PostDict) {
	var p Post
	DB.Where("id = ?", postId).First(&p)

	post.Tags = make([]string, 0) // [YZK] fix bug
	for _, t := range p.GetTags() {
		post.Tags = append(post.Tags, t.Name)
	}
	post.Post = p
	post.Author = p.GetAuthor()
	post.Content = ""
	post.Url = p.PostUrl()
	post.Content = p.GetProps("content").(string)
	return
}

func CreatePost(data map[string]interface{}) {
	post := new(Post)
	post.Title = data["title"].(string)
	post.Summary = data["summary"].(string)
	post.Type = data["type"].(int)
	post.CanComment = data["can_comment"].(int)
	post.AuthorID = data["author_id"].(int)
	post.Status = data["status"].(int)

	tags := data["tags"].([]string)
	content := data["content"]
	DB.Create(&post)

	fmt.Println(post)

	go post.SetProps("content", content)
	go post.UpdateTags(tags)
	go post.Flush()
	go CreateActivity(post)
}

func UpdatePost(postID int, data map[string]interface{}) {
	post := new(Post)
	post.ID = postID
	post.Title = data["title"].(string)
	post.Summary = data["summary"].(string)
	post.Type = data["type"].(int)
	post.CanComment = data["can_comment"].(int)
	post.AuthorID = data["author_id"].(int)
	post.Status = data["status"].(int)

	DB.Save(post)

	content := data["content"]
	tags := data["tags"].([]string)
	go post.SetProps("content", content)
	go post.UpdateTags(tags)
	go post.Flush()
}

func DeletePost(postID int) {
	var post Post
	DB.Where("id = ?", postID).First(&post)
	if post.ID != 0 {
		DB.Delete(&post)
		DB.Where("post_id = ?", postID).Delete(Posttag{})
	}
	go post.Flush()
}

func CreateActivity(post *Post) {
	url := "http://localhost:" + setting.PythonServerPort + "/api/activity"
	data := `{"post_id": %d, "user_id": %d}`
	data = fmt.Sprintf(data, post.ID, post.AuthorID)
	fmt.Println(data)
	req := bytes.NewBuffer([]byte(data))
	_, err := http.Post(url, "application/json;charset=utf-8", req)
	if err != nil {
		fmt.Print(err)
	}
}
