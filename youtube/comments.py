"""
评论获取与分析模块
"""

import re
import html
import time
import logging

logger = logging.getLogger(__name__)


def get_all_comments(youtube, video_id, max_comments=300):
    """
    获取视频评论（含回复）。

    返回: list[dict]
    """
    comments = []
    next_page = None

    while len(comments) < max_comments:
        try:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                order="relevance",
                pageToken=next_page,
                textFormat="plainText",
            )
            response = request.execute()
        except Exception as e:
            logger.warning(f"  评论获取失败 ({video_id}): {e}")
            break

        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "video_id": video_id,
                "comment_id": item["id"],
                "author": top["authorDisplayName"],
                "text": html.unescape(top["textDisplay"]),
                "like_count": top["likeCount"],
                "published_at": top["publishedAt"],
                "is_reply": False,
                "parent_id": None,
            })

            if item["snippet"]["totalReplyCount"] > 0 and "replies" in item:
                for reply in item["replies"]["comments"]:
                    r = reply["snippet"]
                    comments.append({
                        "video_id": video_id,
                        "comment_id": reply["id"],
                        "author": r["authorDisplayName"],
                        "text": html.unescape(r["textDisplay"]),
                        "like_count": r["likeCount"],
                        "published_at": r["publishedAt"],
                        "is_reply": True,
                        "parent_id": item["id"],
                    })

        next_page = response.get("nextPageToken")
        if not next_page:
            break
        time.sleep(0.3)

    return comments


def clean_comment(text):
    """清洗评论文本"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
