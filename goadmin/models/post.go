package models

import (
	"strconv"
)

type Post struct {
	Model
	Title      string `json:"title"`
	AuthorID   int    `json:"author_id"`
	Slug       string `json:"slug"`
	Summary    string `json:"summary"`
	CanComment bool   `json:"can_comment"`
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

func (post Post) GetAuthor() (user User) {
	DB.Select("id, name").Where("id = ?", post.AuthorID).First(&user)
	return
}

func (post Post) PostUrl() string {
	postID := strconv.Itoa(post.ID)
	return "Post/" + postID
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
	var tagNames []string
	for _, t := range p.GetTags() {
		tagNames = append(tagNames, t.Name)
	}
	post.Post = p
	post.Author = p.GetAuthor()
	post.Content = ""
	post.Url = p.PostUrl()
	post.Tags = tagNames
	return
}
