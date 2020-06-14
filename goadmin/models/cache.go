package models

import "fmt"

var (
	MC_KEY_TAGS_BY_POST_ID string = "post:%s:tags"
	MC_KEY_RELATED         string = "post:related_posts:%d:limit:%d"
	MC_KEY_POST_BY_SLUG    string = "post:%s:slug"
	MC_KEY_ALL_POSTS       string = "core:posts:%s:v2"
	MC_KEY_FEED            string = "core:feed"
	MC_KEY_SITEMAP         string = "core:sitemap"
	MC_KEY_SEARCH          string = "core:search.json"
	MC_KEY_ARCHIVES        string = "core:archives"
	MC_KEY_ARCHIVE         string = "core:archive:%d"
	MC_KEY_TAGS            string = "core:tags"
	MC_KEY_TAG             string = "core:tag:%s"
	RK_PAGEVIEW            string = "frodo:pageview:{}:v2"
	RK_ALL_POST_IDS        string = "frodo:all_post_ids"
	RK_VISITED_POST_IDS    string = "frodo:visited_post_ids"
	PAGEVIEW_FIELD         string = "pv"
)

func ClearMC(keys []string) {
	for _, k := range keys {
		go func(k string) {
			err := RedisClient.Del(k).Err()
			if err != nil {
				fmt.Println(err)
			}
			fmt.Println("Clear Cache: ", k)
		}(k)
	}
}

func (post *Post) Flush() {
	postYear := post.CreatedAt.Year()
	keys := []string{
		MC_KEY_FEED, MC_KEY_SEARCH,
		MC_KEY_ARCHIVES, MC_KEY_TAGS,
		fmt.Sprintf(MC_KEY_RELATED, post.ID, 4),
		fmt.Sprintf(MC_KEY_POST_BY_SLUG, post.Slug),
		fmt.Sprintf(MC_KEY_ARCHIVE, postYear),
	}

	for _, item := range []string{"False", "True"} {
		keys = append(keys, fmt.Sprintf(MC_KEY_ALL_POSTS, item))
	}

	tags := post.GetTags()

	for _, t := range tags {
		keys = append(keys, fmt.Sprintf(MC_KEY_TAG, t.ID))
	}
	keys = append(keys, fmt.Sprintf("Post:%d", post.ID))
	ClearMC(keys)
}
