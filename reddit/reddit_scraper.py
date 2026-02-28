#!/usr/bin/env python3
"""
Reddit Snapmaker U1 用户反馈采集工具

从 r/snapmaker 和 r/3Dprinting 采集 Snapmaker U1 相关帖子和评论，
输出结构化 JSON 文件供后续分析使用。
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

# Auto-install requests if missing
try:
    import requests
except ImportError:
    print("[INFO] Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── Configuration ──────────────────────────────────────────────────────────

USER_AGENT = "SnapmakerU1Research/1.0 (research project)"
REQUEST_DELAY = 2  # seconds between requests
MAX_RETRIES = 3
BASE_URL = "https://www.reddit.com"

OUTPUT_DIR = "reddit_output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "reddit_u1_data.json")

# U1 keywords for filtering (all lowercase)
U1_KEYWORDS = [
    "u1",
    "snapmaker u1",
    "snap maker u1",
    "snapswap",
    "snap swap",
    "tool change",
    "snapmaker multi",
    "snapmaker 4-head",
]

# Search queries per subreddit
SEARCH_CONFIG = {
    "snapmaker": {
        "browse_new": True,  # browse /new listing
        "browse_new_limit": 500,
        "search_queries": ["U1", "snapmaker U1", "snapswap", "tool change"],
    },
    "3Dprinting": {
        "browse_new": False,
        "search_queries": ["Snapmaker U1", "snapmaker U1", "U1 printer snapmaker"],
    },
}

# ── HTTP helpers ───────────────────────────────────────────────────────────

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def reddit_get(url, params=None):
    """GET with rate limiting, retry, and 429 handling."""
    for attempt in range(1, MAX_RETRIES + 1):
        time.sleep(REQUEST_DELAY)
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 10))
                print(f"  [429] Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"  [WARN] Request failed (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt == MAX_RETRIES:
                print(f"  [ERROR] Giving up on {url}")
                return None
            time.sleep(2 * attempt)
    return None


# ── Post collection ────────────────────────────────────────────────────────


def fetch_listing(subreddit, sort="new", limit=100, max_pages=5):
    """Fetch posts from a subreddit listing (new/hot/etc), paginated."""
    url = f"{BASE_URL}/r/{subreddit}/{sort}.json"
    posts = []
    after = None

    for page in range(max_pages):
        params = {"limit": limit, "raw_json": 1}
        if after:
            params["after"] = after
        print(f"    Listing page {page + 1} (after={after})...")
        data = reddit_get(url, params)
        if not data or "data" not in data:
            break
        children = data["data"].get("children", [])
        if not children:
            break
        for child in children:
            if child.get("kind") == "t3":
                posts.append(child["data"])
        after = data["data"].get("after")
        if not after:
            break

    return posts


def search_subreddit(subreddit, query):
    """Search a subreddit for posts matching query, paginated."""
    url = f"{BASE_URL}/r/{subreddit}/search.json"
    posts = []
    after = None

    for page in range(5):
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "relevance",
            "t": "all",
            "limit": 100,
            "raw_json": 1,
        }
        if after:
            params["after"] = after
        print(f"    Search '{query}' page {page + 1}...")
        data = reddit_get(url, params)
        if not data or "data" not in data:
            break
        children = data["data"].get("children", [])
        if not children:
            break
        for child in children:
            if child.get("kind") == "t3":
                posts.append(child["data"])
        after = data["data"].get("after")
        if not after:
            break

    return posts


def is_u1_related(post):
    """Check if post title + selftext contain U1 keywords."""
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    return any(kw in text for kw in U1_KEYWORDS)


def collect_posts_for_subreddit(subreddit, config):
    """Collect and deduplicate all U1-related posts for a subreddit."""
    raw_posts = {}  # id -> post data

    # Browse new listing
    if config.get("browse_new"):
        total = config.get("browse_new_limit", 500)
        pages = (total + 99) // 100  # ceil division
        print(f"  [r/{subreddit}] Browsing /new (up to {total} posts)...")
        for post in fetch_listing(subreddit, sort="new", limit=100, max_pages=pages):
            raw_posts[post["id"]] = post

    # Search queries
    for query in config.get("search_queries", []):
        print(f"  [r/{subreddit}] Searching: {query}")
        for post in search_subreddit(subreddit, query):
            raw_posts[post["id"]] = post

    # Filter U1-related
    u1_posts = {pid: p for pid, p in raw_posts.items() if is_u1_related(p)}
    print(
        f"  [r/{subreddit}] Found {len(raw_posts)} unique posts, "
        f"{len(u1_posts)} U1-related"
    )
    return u1_posts


# ── Comment collection ─────────────────────────────────────────────────────


def flatten_comments(comment_data, post_id, post_url, depth=0, parent_id=None):
    """Recursively flatten a comment tree."""
    comments = []

    if isinstance(comment_data, dict) and comment_data.get("kind") == "Listing":
        for child in comment_data.get("data", {}).get("children", []):
            comments.extend(
                flatten_comments(child, post_id, post_url, depth, parent_id)
            )
    elif isinstance(comment_data, dict) and comment_data.get("kind") == "t1":
        cd = comment_data["data"]
        author = cd.get("author", "")
        body = cd.get("body", "")

        # Skip deleted/removed
        if author in ("[deleted]", "[removed]") or body in ("[deleted]", "[removed]"):
            pass
        else:
            created_ts = int(cd.get("created_utc", 0))
            created_str = ""
            if created_ts:
                created_str = (
                    datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime(
                        "%Y-%m-%d %H:%M:%S UTC"
                    )
                )

            comment = {
                "comment_id": cd.get("id", ""),
                "post_id": post_id,
                "post_url": post_url,
                "author": author,
                "text": body,
                "score": cd.get("score", 0),
                "created_utc": created_str,
                "created_ts": created_ts,
                "depth": depth,
                "parent_id": cd.get("parent_id", parent_id or ""),
                "is_op": cd.get("is_submitter", False),
            }
            comments.append(comment)

        # Recurse into replies
        replies = cd.get("replies", "")
        if isinstance(replies, dict):
            comments.extend(
                flatten_comments(
                    replies, post_id, post_url, depth + 1, f"t1_{cd.get('id', '')}"
                )
            )
    elif isinstance(comment_data, dict) and comment_data.get("kind") == "more":
        pass  # Skip "load more" stubs

    return comments


def fetch_comments(permalink, post_id):
    """Fetch full comment tree for a post."""
    url = f"{BASE_URL}{permalink}.json"
    params = {"raw_json": 1, "limit": 500, "depth": 10}
    data = reddit_get(url, params)
    if not data or not isinstance(data, list) or len(data) < 2:
        return []

    post_url = f"{BASE_URL}{permalink}"
    comment_listing = data[1]
    return flatten_comments(comment_listing, post_id, post_url)


# ── Main pipeline ──────────────────────────────────────────────────────────


def format_post(post, comments):
    """Format a post dict with its comments for output."""
    created_ts = int(post.get("created_utc", 0))
    created_str = ""
    if created_ts:
        created_str = datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

    permalink = post.get("permalink", "")
    post_url = f"{BASE_URL}{permalink}" if permalink else ""

    return {
        "id": post.get("id", ""),
        "subreddit": post.get("subreddit", ""),
        "title": post.get("title", ""),
        "author": post.get("author", ""),
        "text": post.get("selftext", ""),
        "url": post_url,
        "score": post.get("score", 0),
        "upvote_ratio": post.get("upvote_ratio", 0),
        "num_comments": post.get("num_comments", 0),
        "created_utc": created_str,
        "created_ts": created_ts,
        "flair": post.get("link_flair_text", ""),
        "is_self": post.get("is_self", True),
        "link_url": "" if post.get("is_self", True) else post.get("url", ""),
        "comments": comments,
        "fetched_comment_count": len(comments),
    }


def print_summary(result):
    """Print a summary of the scraping results."""
    print("\n" + "=" * 60)
    print("  SCRAPING SUMMARY")
    print("=" * 60)
    print(f"  Total posts:    {result['total_posts']}")
    print(f"  Total comments: {result['total_comments']}")

    # Per-subreddit breakdown
    sub_counts = {}
    for p in result["posts"]:
        sub = p["subreddit"]
        sub_counts.setdefault(sub, {"posts": 0, "comments": 0})
        sub_counts[sub]["posts"] += 1
        sub_counts[sub]["comments"] += p["fetched_comment_count"]

    print("\n  Per subreddit:")
    for sub, counts in sorted(sub_counts.items()):
        print(f"    r/{sub}: {counts['posts']} posts, {counts['comments']} comments")

    # Average score
    if result["posts"]:
        avg_score = sum(p["score"] for p in result["posts"]) / len(result["posts"])
        print(f"\n  Average post score: {avg_score:.1f}")

    # Top 5
    top5 = sorted(result["posts"], key=lambda p: p["score"], reverse=True)[:5]
    if top5:
        print("\n  Top 5 posts by score:")
        for i, p in enumerate(top5, 1):
            title = p["title"][:60] + ("..." if len(p["title"]) > 60 else "")
            print(f"    {i}. [{p['score']}] {title}")
            print(f"       {p['url']}")

    print("=" * 60)


def main():
    print("=" * 60)
    print("  Reddit Snapmaker U1 Feedback Scraper")
    print("=" * 60)

    # Collect posts from all subreddits
    all_posts = {}  # id -> post data
    for subreddit, config in SEARCH_CONFIG.items():
        print(f"\n[Phase 1] Collecting posts from r/{subreddit}...")
        posts = collect_posts_for_subreddit(subreddit, config)
        all_posts.update(posts)

    print(f"\n[Summary] Total unique U1-related posts: {len(all_posts)}")

    if not all_posts:
        print("[WARN] No U1-related posts found. Saving empty result.")

    # Fetch comments for each post
    print(f"\n[Phase 2] Fetching comments for {len(all_posts)} posts...")
    formatted_posts = []
    all_comments_flat = []

    for i, (post_id, post) in enumerate(all_posts.items(), 1):
        title_short = post.get("title", "")[:50]
        permalink = post.get("permalink", "")
        print(f"  [{i}/{len(all_posts)}] Fetching comments: {title_short}...")

        comments = []
        if permalink:
            comments = fetch_comments(permalink, post_id)
        print(f"    -> {len(comments)} comments")

        formatted = format_post(post, comments)
        formatted_posts.append(formatted)
        all_comments_flat.extend(comments)

    # Sort posts by created_ts descending
    formatted_posts.sort(key=lambda p: p["created_ts"], reverse=True)

    # Build output
    result = {
        "source": "reddit",
        "subreddits": ["r/snapmaker", "r/3Dprinting"],
        "extraction_time": datetime.now(timezone.utc).isoformat(),
        "total_posts": len(formatted_posts),
        "total_comments": len(all_comments_flat),
        "posts": formatted_posts,
        "comments_flat": all_comments_flat,
    }

    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[Done] Output saved to {OUTPUT_FILE}")
    print_summary(result)


if __name__ == "__main__":
    main()
