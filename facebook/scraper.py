#!/usr/bin/env python3
"""
Facebook 群组数据采集工具 (Playwright)

功能:
  - 自动登录 Facebook 并滚动加载群组帖子
  - 展开并采集每个帖子的评论
  - 每 N 条帖子自动保存 checkpoint，崩溃后可断点续抓
  - 输出格式与 analyze.py 完全兼容

使用方法:
    # 首次运行（会打开浏览器窗口供你手动登录）
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327" --login

    # 后续运行（使用已保存的 cookie）
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327"

    # 断点续抓（从上次 checkpoint 继续）
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327" --resume

    # 指定抓取数量
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327" --max-posts 500

依赖:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PwTimeout
except ImportError:
    print("请先安装 Playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


# ── 常量 ────────────────────────────────────────────────────────

COOKIE_FILE = "fb_cookies.json"
CHECKPOINT_DIR = "scraper_checkpoints"
SCROLL_PAUSE = 2.0        # 每次滚动后等待秒数
COMMENT_LOAD_PAUSE = 1.5  # 展开评论后等待秒数
CHECKPOINT_EVERY = 50     # 每 N 条帖子保存一次 checkpoint
MAX_SCROLL_RETRIES = 5    # 连续无新内容时的最大重试次数
MAX_COMMENT_PAGES = 20    # 单个帖子最多展开评论的次数


# ── Cookie 管理 ──────────────────────────────────────────────────

def save_cookies(context: BrowserContext, path: str):
    cookies = context.cookies()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"  Cookie 已保存到 {path} ({len(cookies)} 条)")


def load_cookies(context: BrowserContext, path: str) -> bool:
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)
    print(f"  已加载 {len(cookies)} 条 Cookie")
    return True


# ── Checkpoint 管理 ──────────────────────────────────────────────

def _checkpoint_path(group_id: str) -> str:
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    return os.path.join(CHECKPOINT_DIR, f"checkpoint_{group_id}.json")


def save_checkpoint(group_id: str, posts: list, scroll_position: int, group_info: dict):
    path = _checkpoint_path(group_id)
    data = {
        "group_id": group_id,
        "group_info": group_info,
        "scroll_position": scroll_position,
        "posts": posts,
        "saved_at": datetime.now().isoformat(),
        "total_posts": len(posts),
    }
    # 写入临时文件后重命名，防止写入中断导致数据损坏
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    print(f"  ✓ Checkpoint 已保存: {len(posts)} 条帖子")


def load_checkpoint(group_id: str) -> Optional[dict]:
    path = _checkpoint_path(group_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  发现 checkpoint: {data['total_posts']} 条帖子 (保存于 {data['saved_at']})")
    return data


def clear_checkpoint(group_id: str):
    path = _checkpoint_path(group_id)
    if os.path.exists(path):
        os.remove(path)
        print("  Checkpoint 已清理")


# ── 工具函数 ──────────────────────────────────────────────────────

def extract_group_id(url: str) -> str:
    """从群组 URL 提取 ID 或名称。"""
    url = url.rstrip("/")
    match = re.search(r"/groups/([^/?#]+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"无法从 URL 提取群组 ID: {url}")


def extract_post_id(element, page: Page) -> Optional[str]:
    """尝试从帖子元素提取唯一 ID。"""
    try:
        # 尝试从帖子链接提取 post ID
        link = element.query_selector('a[href*="/posts/"], a[href*="permalink"]')
        if link:
            href = link.get_attribute("href") or ""
            match = re.search(r"/posts/(\d+)", href)
            if match:
                return match.group(1)
            match = re.search(r"permalink/(\d+)", href)
            if match:
                return match.group(1)
    except Exception:
        pass

    # 回退：使用帖子文本的 hash
    try:
        text = element.inner_text()[:200]
        import hashlib
        return "hash_" + hashlib.md5(text.encode()).hexdigest()[:12]
    except Exception:
        return None


# ── 核心采集逻辑 ──────────────────────────────────────────────────

def login_interactive(page: Page, context: BrowserContext):
    """打开 Facebook 登录页面，等待用户手动登录。"""
    print("\n=== 手动登录模式 ===")
    print("浏览器已打开 Facebook 登录页面，请手动登录。")
    print("登录成功后（看到新闻动态），按 Enter 继续...")

    page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
    input()  # 等待用户按 Enter

    # 验证登录状态
    if "login" in page.url.lower():
        print("警告: 似乎尚未登录成功，请确认后再次运行。")
        sys.exit(1)

    save_cookies(context, COOKIE_FILE)
    print("登录成功！\n")


def dismiss_popups(page: Page):
    """关闭 Facebook 常见弹窗。"""
    selectors = [
        # Cookie 同意弹窗
        'button[data-cookiebanner="accept_button"]',
        'button[title="Allow all cookies"]',
        'button[title="允许所有 Cookie"]',
        # 通知弹窗
        'div[role="dialog"] button:has-text("Not Now")',
        'div[role="dialog"] button:has-text("以后再说")',
        'div[role="dialog"] button:has-text("暂不")',
    ]
    for sel in selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(0.5)
        except Exception:
            pass


def get_group_name(page: Page) -> str:
    """获取群组名称。"""
    selectors = [
        'h1 a span',
        'h1 span',
        'div[role="main"] h1',
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                name = el.inner_text().strip()
                if name:
                    return name
        except Exception:
            pass
    return "Unknown Group"


def scrape_post_comments(page: Page, post_element) -> list:
    """采集单个帖子的所有评论。"""
    comments = []

    # 尝试展开"查看更多评论"
    for _ in range(MAX_COMMENT_PAGES):
        try:
            more_btn = post_element.query_selector(
                'div[role="button"]:has-text("View more comments"), '
                'div[role="button"]:has-text("查看更多评论"), '
                'span:has-text("View more comments"), '
                'span:has-text("previous comments")'
            )
            if more_btn and more_btn.is_visible():
                more_btn.click()
                time.sleep(COMMENT_LOAD_PAUSE)
            else:
                break
        except Exception:
            break

    # 也展开"查看更多回复"
    try:
        reply_buttons = post_element.query_selector_all(
            'div[role="button"]:has-text("replies"), '
            'div[role="button"]:has-text("条回复")'
        )
        for btn in reply_buttons[:10]:  # 限制展开数量
            try:
                if btn.is_visible():
                    btn.click()
                    time.sleep(0.5)
            except Exception:
                pass
    except Exception:
        pass

    # 提取评论
    try:
        comment_elements = post_element.query_selector_all(
            'div[role="article"] div[role="article"]'
        )
        # 回退选择器
        if not comment_elements:
            comment_elements = post_element.query_selector_all(
                'ul li div[data-testid="UFI2Comment/root_depth_0"]'
            )

        for ce in comment_elements:
            try:
                # 展开"查看更多"截断的评论
                see_more = ce.query_selector('div[role="button"]:has-text("See more"), div[role="button"]:has-text("查看更多")')
                if see_more and see_more.is_visible():
                    see_more.click()
                    time.sleep(0.3)

                text_el = ce.query_selector('div[dir="auto"]')
                text = text_el.inner_text().strip() if text_el else ""

                author_el = ce.query_selector('a[role="link"] span')
                author = author_el.inner_text().strip() if author_el else "Unknown"

                if text:
                    comments.append({
                        "author": author,
                        "text": text,
                    })
            except Exception:
                continue
    except Exception:
        pass

    return comments


def scrape_posts(page: Page, max_posts: int, existing_post_ids: set) -> list:
    """滚动页面并采集帖子。"""
    posts = []
    no_new_count = 0
    last_post_count = 0

    while len(posts) < max_posts:
        # 获取页面上所有帖子容器
        post_elements = page.query_selector_all('div[role="article"]')

        # 过滤：只处理顶层帖子（非嵌套评论）
        top_level_posts = []
        for el in post_elements:
            try:
                # 顶层帖子通常有 data-pagelet 或在 feed 容器内
                parent = el.evaluate('el => el.parentElement?.closest(\'div[role="article"]\')')
                if not parent:
                    top_level_posts.append(el)
            except Exception:
                top_level_posts.append(el)

        new_posts_found = 0
        for post_el in top_level_posts:
            if len(posts) >= max_posts:
                break

            post_id = extract_post_id(post_el, page)
            if not post_id or post_id in existing_post_ids:
                continue

            existing_post_ids.add(post_id)
            new_posts_found += 1

            try:
                # 展开"查看更多"
                see_more = post_el.query_selector(
                    'div[role="button"]:has-text("See more"), '
                    'div[role="button"]:has-text("查看更多")'
                )
                if see_more and see_more.is_visible():
                    see_more.click()
                    time.sleep(0.3)

                # 提取帖子文本
                text_divs = post_el.query_selector_all('div[dir="auto"][data-ad-preview="message"], div[data-ad-comet-preview="message"]')
                if not text_divs:
                    text_divs = post_el.query_selector_all('div[dir="auto"]')

                text = ""
                for td in text_divs[:3]:
                    t = td.inner_text().strip()
                    if len(t) > len(text):
                        text = t

                # 提取作者
                author_el = post_el.query_selector('a[role="link"] strong, h3 a span, h4 a span')
                author = author_el.inner_text().strip() if author_el else "Unknown"

                # 提取互动数据
                reactions = 0
                comment_count = 0
                try:
                    reaction_el = post_el.query_selector(
                        'span[role="toolbar"] span, '
                        'div[aria-label*="reaction"], div[aria-label*="个人觉得"]'
                    )
                    if reaction_el:
                        r_text = reaction_el.inner_text().strip()
                        nums = re.findall(r'[\d,]+', r_text.replace(",", ""))
                        if nums:
                            reactions = int(nums[0])
                except Exception:
                    pass

                try:
                    comment_count_el = post_el.query_selector(
                        'span:has-text("comment"), span:has-text("条评论")'
                    )
                    if comment_count_el:
                        c_text = comment_count_el.inner_text().strip()
                        nums = re.findall(r'\d+', c_text)
                        if nums:
                            comment_count = int(nums[0])
                except Exception:
                    pass

                # 检测媒体
                has_image = bool(post_el.query_selector('img[src*="scontent"], img[data-visualcompletion]'))
                has_video = bool(post_el.query_selector('video, div[data-video-id]'))

                # 采集评论
                comments = scrape_post_comments(page, post_el)

                post_data = {
                    "post_id": post_id,
                    "author": author,
                    "text": text,
                    "reactions": reactions,
                    "comment_count": max(comment_count, len(comments)),
                    "has_image": has_image,
                    "has_video": has_video,
                    "comments": comments,
                }

                posts.append(post_data)
                print(f"  [{len(posts)}/{max_posts}] {author}: {text[:60]}... ({len(comments)} 评论)")

            except Exception as e:
                print(f"  跳过帖子 {post_id}: {e}")
                continue

        # 检查是否有新帖子
        if len(posts) == last_post_count:
            no_new_count += 1
            if no_new_count >= MAX_SCROLL_RETRIES:
                print(f"\n连续 {MAX_SCROLL_RETRIES} 次滚动无新内容，采集结束。")
                break
        else:
            no_new_count = 0
            last_post_count = len(posts)

        # Checkpoint
        if len(posts) > 0 and len(posts) % CHECKPOINT_EVERY == 0:
            yield posts  # 通过 generator 通知调用方保存 checkpoint

        # 滚动加载更多
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(SCROLL_PAUSE)

        # 清理 DOM 节点（防内存膨胀）— 移除已处理的、视口之上的帖子
        page.evaluate("""
            () => {
                const articles = document.querySelectorAll('div[role="article"]');
                const threshold = window.scrollY - 2000;
                let removed = 0;
                for (const el of articles) {
                    if (el.getBoundingClientRect().bottom + window.scrollY < threshold && removed < 20) {
                        el.remove();
                        removed++;
                    }
                }
            }
        """)

    yield posts  # 最终结果


def run_scraper(args):
    """主采集流程。"""
    group_id = extract_group_id(args.group_url)
    group_url = args.group_url.rstrip("/")

    # 加载 checkpoint
    existing_posts = []
    existing_post_ids = set()
    scroll_position = 0

    if args.resume:
        cp = load_checkpoint(group_id)
        if cp:
            existing_posts = cp["posts"]
            existing_post_ids = {p["post_id"] for p in existing_posts}
            scroll_position = cp.get("scroll_position", 0)
            print(f"  从 checkpoint 恢复: 已有 {len(existing_posts)} 条帖子")
        else:
            print("  未找到 checkpoint，从头开始。")

    remaining = args.max_posts - len(existing_posts)
    if remaining <= 0:
        print(f"已达到目标数量 ({args.max_posts})，直接输出。")
        return existing_posts, {"group_name": "Resumed", "group_url": group_url}

    print(f"\n开始采集: {group_url}")
    print(f"  目标: {args.max_posts} 条帖子 (已有 {len(existing_posts)}，还需 {remaining})")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.login,  # 登录模式用有头浏览器
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        page = context.new_page()

        # 登录 / 加载 cookie
        if args.login:
            login_interactive(page, context)
        else:
            if not load_cookies(context, COOKIE_FILE):
                print("未找到 Cookie 文件。请先用 --login 参数登录。")
                browser.close()
                sys.exit(1)

        # 进入群组页面
        print(f"正在打开群组: {group_url}")
        page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # 验证登录状态
        if "login" in page.url.lower():
            print("Cookie 已过期，请重新使用 --login 登录。")
            browser.close()
            sys.exit(1)

        dismiss_popups(page)
        time.sleep(1)

        # 获取群组信息
        group_name = get_group_name(page)
        group_info = {
            "group_name": group_name,
            "group_url": group_url,
        }
        print(f"  群组名称: {group_name}")

        # 如果有 checkpoint，恢复滚动位置
        if scroll_position > 0:
            print(f"  恢复滚动位置: {scroll_position}px")
            page.evaluate(f"window.scrollTo(0, {scroll_position})")
            time.sleep(2)

        # 开始采集
        all_posts = list(existing_posts)
        for posts_snapshot in scrape_posts(page, remaining, existing_post_ids):
            all_posts = existing_posts + posts_snapshot
            scroll_pos = page.evaluate("window.scrollY")
            save_checkpoint(group_id, all_posts, scroll_pos, group_info)

        # 更新 cookie（可能已刷新）
        save_cookies(context, COOKIE_FILE)
        browser.close()

    return all_posts, group_info


def build_output(posts: list, group_info: dict) -> dict:
    """构建与 analyze.py 兼容的 JSON 输出。"""
    comments_flat = []
    for post in posts:
        for comment in post.get("comments", []):
            comments_flat.append({
                "post_id": post["post_id"],
                "author": comment.get("author", "Unknown"),
                "text": comment.get("text", ""),
            })

    return {
        "group_name": group_info.get("group_name", "Unknown"),
        "group_url": group_info.get("group_url", ""),
        "extraction_time": datetime.now().isoformat(),
        "total_posts": len(posts),
        "total_comments": len(comments_flat),
        "posts": posts,
        "comments_flat": comments_flat,
    }


def validate_output(data: dict) -> list:
    """验证输出数据完整性，返回警告列表。"""
    warnings = []

    posts = data.get("posts", [])
    if not posts:
        warnings.append("❌ 无帖子数据")
        return warnings

    # 检查帖子完整性
    empty_text = sum(1 for p in posts if not p.get("text", "").strip())
    if empty_text > 0:
        pct = empty_text / len(posts) * 100
        warnings.append(f"⚠ {empty_text} 条帖子 ({pct:.0f}%) 文本为空")

    # 检查 post_id 唯一性
    ids = [p["post_id"] for p in posts]
    dupes = len(ids) - len(set(ids))
    if dupes > 0:
        warnings.append(f"⚠ 发现 {dupes} 个重复 post_id")

    # 检查评论采集率
    posts_with_comments = sum(1 for p in posts if p.get("comment_count", 0) > 0)
    posts_with_actual_comments = sum(1 for p in posts if len(p.get("comments", [])) > 0)
    if posts_with_comments > 0:
        rate = posts_with_actual_comments / posts_with_comments * 100
        warnings.append(f"ℹ 评论采集率: {rate:.0f}% ({posts_with_actual_comments}/{posts_with_comments} 有评论的帖子)")

    # 统计摘要
    total_comments = sum(len(p.get("comments", [])) for p in posts)
    warnings.append(f"ℹ 总计: {len(posts)} 帖子, {total_comments} 条评论")

    return warnings


# ── 入口 ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Facebook 群组数据采集工具")
    parser.add_argument(
        "--group-url", required=True,
        help="Facebook 群组 URL，例如 https://www.facebook.com/groups/603696475392327",
    )
    parser.add_argument(
        "--max-posts", type=int, default=500,
        help="最多采集帖子数 (默认 500)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="输出 JSON 文件路径 (默认: facebook_data_<group_id>.json)",
    )
    parser.add_argument(
        "--login", action="store_true",
        help="打开浏览器窗口手动登录 Facebook",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="从上次 checkpoint 断点续抓",
    )
    parser.add_argument(
        "--validate-only", default=None,
        help="仅验证已有 JSON 文件的数据完整性",
    )

    args = parser.parse_args()

    # 仅验证模式
    if args.validate_only:
        print(f"验证数据: {args.validate_only}")
        with open(args.validate_only, "r", encoding="utf-8") as f:
            data = json.load(f)
        warnings = validate_output(data)
        for w in warnings:
            print(f"  {w}")
        sys.exit(0)

    # 采集
    posts, group_info = run_scraper(args)

    if not posts:
        print("未采集到任何帖子。")
        sys.exit(1)

    # 构建输出
    output = build_output(posts, group_info)

    # 验证
    print("\n=== 数据完整性检查 ===")
    warnings = validate_output(output)
    for w in warnings:
        print(f"  {w}")

    # 保存
    group_id = extract_group_id(args.group_url)
    output_path = args.output or f"facebook_data_{group_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 数据已保存到: {output_path}")
    print(f"  可直接用于分析: python analyze.py {output_path}")

    # 清理 checkpoint
    clear_checkpoint(group_id)


if __name__ == "__main__":
    main()
