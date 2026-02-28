# Reddit Snapmaker U1 用户反馈采集工具

从 Reddit 采集 Snapmaker U1 3D打印机相关的用户帖子和评论，输出结构化 JSON 文件供后续分析使用。

## 采集范围

- **r/snapmaker**：浏览最新帖子 + 搜索 U1 相关关键词
- **r/3Dprinting**：搜索 Snapmaker U1 相关帖子

自动过滤仅保留与 U1 相关的帖子，并获取每条帖子的完整评论树。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python reddit_scraper.py
```

输出文件保存在 `reddit_output/reddit_u1_data.json`。

## 输出 JSON 结构

```json
{
  "source": "reddit",
  "subreddits": ["r/snapmaker", "r/3Dprinting"],
  "extraction_time": "ISO format",
  "total_posts": 123,
  "total_comments": 456,
  "posts": [
    {
      "id": "帖子ID",
      "subreddit": "子版块",
      "title": "标题",
      "author": "作者",
      "text": "正文",
      "url": "帖子链接",
      "score": 42,
      "num_comments": 15,
      "created_utc": "时间",
      "comments": [{ "comment_id": "...", "author": "...", "text": "...", "depth": 0 }],
      "fetched_comment_count": 12
    }
  ],
  "comments_flat": []
}
```

- `posts`：每个帖子包含其所有评论
- `comments_flat`：所有评论的扁平化数组，每条带 `post_id` 和 `post_url` 关联

## 注意事项

- 使用 Reddit 公开 JSON 接口，无需 API Key
- 请求间隔 2 秒，遵守 Reddit API 使用规范
- 仅用于研究目的
