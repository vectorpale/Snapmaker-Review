"""
YouTube Data API v3 封装模块

提供视频搜索、视频详情、频道画像、评论获取等功能。
"""

import time
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import SEARCH_QUERIES, KNOWN_REVIEWERS, PUBLISHED_AFTER

logger = logging.getLogger(__name__)


def init_youtube_client(api_key):
    """创建 YouTube Data API v3 客户端"""
    return build("youtube", "v3", developerKey=api_key)


def _retry_api_call(api_callable, max_retries=3, base_delay=1.0):
    """带指数退避的 API 调用重试"""
    for attempt in range(max_retries + 1):
        try:
            return api_callable()
        except HttpError as e:
            if e.resp.status in (403, 429, 500, 503) and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"API error {e.resp.status}, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                raise


def search_videos(youtube, queries, published_after, max_results_per_query=20):
    """
    Step 1.1: 关键词搜索视频
    返回: (all_video_ids: set, video_search_results: list[dict])
    """
    all_video_ids = set()
    video_search_results = []

    for query in queries:
        logger.info(f"搜索: {query}")
        response = _retry_api_call(lambda q=query: youtube.search().list(
            part="snippet",
            q=q,
            type="video",
            order="relevance",
            maxResults=max_results_per_query,
            publishedAfter=published_after,
        ).execute())

        for item in response.get("items", []):
            vid = item["id"]["videoId"]
            if vid not in all_video_ids:
                all_video_ids.add(vid)
                video_search_results.append({
                    "video_id": vid,
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    "description": item["snippet"]["description"][:500],
                    "search_query": query,
                })
        time.sleep(0.5)

    logger.info(f"关键词搜索: {len(all_video_ids)} 个独立视频")
    return all_video_ids, video_search_results


def search_known_reviewers(youtube, reviewers, existing_results, all_video_ids, published_after):
    """
    Step 1.2: 已知评测频道补充搜索
    """
    for reviewer in reviewers:
        channel_found = any(
            reviewer["channel"].lower() in v["channel"].lower()
            for v in existing_results
        )
        if not channel_found:
            logger.info(f"补充搜索: {reviewer['search']}")
            try:
                response = _retry_api_call(lambda r=reviewer: youtube.search().list(
                    part="snippet",
                    q=r["search"],
                    type="video",
                    maxResults=5,
                    publishedAfter=published_after,
                ).execute())

                for item in response.get("items", []):
                    vid = item["id"]["videoId"]
                    if vid not in all_video_ids:
                        all_video_ids.add(vid)
                        existing_results.append({
                            "video_id": vid,
                            "title": item["snippet"]["title"],
                            "channel": item["snippet"]["channelTitle"],
                            "published_at": item["snippet"]["publishedAt"],
                            "description": item["snippet"]["description"][:500],
                            "search_query": reviewer["search"],
                        })
            except HttpError as e:
                logger.warning(f"补充搜索失败 ({reviewer['channel']}): {e}")
            time.sleep(0.5)

    logger.info(f"补充搜索后: {len(all_video_ids)} 个独立视频")
    return all_video_ids, existing_results


def get_video_details(youtube, video_ids):
    """
    Step 2.1: 批量获取视频详情
    返回: dict[video_id -> video_detail]
    """
    video_ids_list = list(video_ids)
    video_details = {}

    for i in range(0, len(video_ids_list), 50):
        batch = video_ids_list[i:i + 50]
        response = _retry_api_call(lambda b=batch: youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(b),
        ).execute())

        for item in response.get("items", []):
            vid = item["id"]
            stats = item.get("statistics", {})
            video_details[vid] = {
                "video_id": vid,
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "channel_id": item["snippet"]["channelId"],
                "published_at": item["snippet"]["publishedAt"],
                "description": item["snippet"]["description"],
                "tags": item["snippet"].get("tags", []),
                "duration": item["contentDetails"]["duration"],
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            }

    logger.info(f"获取详情: {len(video_details)} 个视频")
    return video_details


def get_channel_profiles(youtube, channel_ids):
    """
    Step 2.2: 获取频道画像数据
    返回: dict[channel_id -> channel_profile]
    """
    unique_channel_ids = list(set(channel_ids))
    channel_profiles = {}

    for i in range(0, len(unique_channel_ids), 50):
        batch = unique_channel_ids[i:i + 50]
        response = _retry_api_call(lambda b=batch: youtube.channels().list(
            part="snippet,statistics",
            id=",".join(b),
        ).execute())

        for item in response.get("items", []):
            ch_id = item["id"]
            ch_stats = item.get("statistics", {})
            ch_snippet = item.get("snippet", {})
            channel_profiles[ch_id] = {
                "channel_id": ch_id,
                "channel_name": ch_snippet.get("title", ""),
                "channel_description": ch_snippet.get("description", "")[:500],
                "channel_country": ch_snippet.get("country", "Unknown"),
                "channel_created_at": ch_snippet.get("publishedAt", ""),
                "subscriber_count": int(ch_stats.get("subscriberCount", 0)),
                "total_video_count": int(ch_stats.get("videoCount", 0)),
                "total_view_count": int(ch_stats.get("viewCount", 0)),
                "subscriber_hidden": ch_stats.get("hiddenSubscriberCount", False),
            }

    logger.info(f"获取频道画像: {len(channel_profiles)} 个频道")
    return channel_profiles
