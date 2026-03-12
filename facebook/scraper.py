#!/usr/bin/env python3
"""
Facebook 群组数据采集工具 (Playwright)

基于已验证的篡改猴脚本 v2.4 的 DOM 提取逻辑，用 Playwright 重写。
解决篡改猴脚本的三大痛点：卡顿崩溃、数据丢失、耗时过长。

功能:
  - 复用篡改猴脚本完全一致的 DOM 选择器和提取逻辑（注入浏览器执行）
  - 每 50 条帖子自动保存 checkpoint（原子写入，崩溃不丢数据）
  - 断点续抓：从上次 checkpoint 继续
  - DOM 瘦身：自动清理已采集的帖子节点，防内存膨胀
  - 拟人滚动：随机延迟 + 定期暂停，降低被限流风险

使用方法:
    # 首次运行（打开浏览器窗口手动登录）
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327" --login

    # 后续运行（使用已保存的 cookie）
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327"

    # 断点续抓
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327" --resume

    # 指定数量 + 输出路径
    python scraper.py --group-url "https://www.facebook.com/groups/603696475392327" --max-posts 800 -o data.json

    # 仅验证已有数据
    python scraper.py --validate-only data.json

依赖:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
except ImportError:
    print("请先安装 Playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


# ── 常量 ────────────────────────────────────────────────────────

COOKIE_FILE = "fb_cookies.json"
CHECKPOINT_DIR = "scraper_checkpoints"
CHECKPOINT_EVERY = 50          # 每 N 条新帖子保存一次 checkpoint
DOM_CLEANUP_EVERY = 10         # 每 N 次滚动清理一次 DOM

# 拟人滚动参数（与篡改猴脚本一致）
SCROLL_DELAY_MIN = 0.5
SCROLL_DELAY_MAX = 1.0
SCROLL_STEP_MIN = 900
SCROLL_STEP_MAX = 1600
PAUSE_EVERY_N = 150            # 每 N 次滚动暂停
PAUSE_DURATION_MIN = 3.0
PAUSE_DURATION_MAX = 8.0
MICRO_PAUSE_CHANCE = 0.03
MICRO_PAUSE_MIN = 0.5
MICRO_PAUSE_MAX = 1.5
MAX_NO_NEW_RETRIES = 25        # 连续无新内容后的恢复尝试次数
MAX_RECOVERY_ROUNDS = 3        # 恢复策略最多尝试几轮


# ── 注入浏览器的 JS 提取逻辑 ─────────────────────────────────────
# 直接移植自篡改猴脚本，保证 DOM 选择器完全一致

JS_EXTRACT_POSTS = """
() => {
    const processedIds = new Set(window.__processedPostIds || []);
    const results = [];

    function simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const c = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + c;
            hash |= 0;
        }
        return Math.abs(hash).toString(36);
    }

    // ── 评论提取（与篡改猴 extractComments 一致）──
    function extractComments(child) {
        const comments = [];
        const commentEls = child.querySelectorAll('div[role="article"]');
        commentEls.forEach((cmt) => {
            try {
                let cmtAuthor = "Unknown";
                let cmtText = "";
                let cmtDate = "";

                for (const link of cmt.querySelectorAll("a")) {
                    const t = link.textContent.trim();
                    if (t.length < 2 || t.length > 80) continue;
                    if (/^\\d+\\s*(小時|分鐘|天|週|月|年|h|d|w|m)/i.test(t)) { cmtDate = t; continue; }
                    if (/^(讚|回覆|Reply|Like|查看|顯示|See)/i.test(t)) continue;
                    if (cmtAuthor === "Unknown") cmtAuthor = t;
                }

                const textBlock = cmt.querySelector('div[dir="auto"]');
                if (textBlock) {
                    const t = textBlock.textContent.trim();
                    if (t.length >= 2 && !/^(讚|回覆|Reply|Like|查看更多|顯示更多|See more|翻譯年糕)$/i.test(t)) {
                        cmtText = t;
                    }
                }
                if (cmtText.length < 2) return;
                comments.push({
                    author: cmtAuthor,
                    text: cmtText.substring(0, 3000),
                    date: cmtDate,
                    reactions: 0,
                });
            } catch (e) { /* skip */ }
        });
        return comments;
    }

    const feed = document.querySelector('div[role="feed"]');
    if (!feed) return { posts: [], processedIds: [] };

    const children = feed.children;
    for (let i = children.length - 1; i >= 0; i--) {
        const child = children[i];
        if (child.dataset.cleaned === "1") continue;

        try {
            // ── 必须有作者 heading 才是帖子 ──
            const heading = child.querySelector("h2, h3, h4");
            if (!heading) continue;
            const headingText = heading.textContent.trim();
            if (headingText.length < 2 || /^(最相關|新貼文|Most Relevant|New Posts|熱門貼文|Top Posts)$/i.test(headingText)) continue;

            // ── 帖子唯一 ID ──
            let postUrl = "";
            let postId = "";
            const postsLink = child.querySelector('a[href*="/posts/"], a[href*="/permalink/"]');
            if (postsLink) {
                postUrl = postsLink.href.split("?")[0];
                const idMatch = postUrl.match(/\\/(\\d{10,})\\/?$/);
                if (idMatch) postId = idMatch[1];
            }
            if (!postId) {
                const photoLink = child.querySelector('a[href*="pcb."]');
                if (photoLink) {
                    const pcbMatch = photoLink.href.match(/pcb\\.(\\d{10,})/);
                    if (pcbMatch) {
                        postId = pcbMatch[1];
                        const groupPath = window.location.pathname.replace(/\\/$/, "");
                        postUrl = "https://www.facebook.com" + groupPath + "/posts/" + postId + "/";
                    }
                }
            }
            if (!postId) {
                const fbidLink = child.querySelector('a[href*="fbid="]');
                if (fbidLink) {
                    const fbidMatch = fbidLink.href.match(/fbid=(\\d{10,})/);
                    if (fbidMatch) {
                        postId = "fbid_" + fbidMatch[1];
                        postUrl = "https://www.facebook.com/photo/?fbid=" + fbidMatch[1];
                    }
                }
            }
            if (!postId) {
                const rawText = child.textContent.trim().substring(0, 100);
                postId = "hash_" + simpleHash(headingText + rawText);
                postUrl = "no_url_" + postId;
            }

            // 去重
            if (processedIds.has(postId)) continue;

            // ── 作者 ──
            let author = headingText
                .replace(/\\s*·\\s*追蹤.*$/s, "")
                .replace(/\\s*·\\s*[Ff]ollow.*$/s, "")
                .replace(/最常發言的成員.*$/s, "")
                .replace(/Top contributor.*$/is, "")
                .replace(/管理員.*$/s, "")
                .replace(/Admin.*$/is, "")
                .replace(/\\s*·\\s*Sponsored.*$/is, "")
                .trim();
            if (author.length === 0 || author.length >= 80) author = "Unknown";

            // ── 正文 ──
            const textSet = new Set();
            const textParts = [];
            child.querySelectorAll('div[dir="auto"]').forEach((block) => {
                let inArticle = false;
                let p = block.parentElement;
                while (p && p !== child) {
                    if (p.getAttribute("role") === "article") { inArticle = true; break; }
                    p = p.parentElement;
                }
                if (inArticle) return;
                const t = block.textContent.trim();
                if (t.length < 3) return;
                if (/^(讚|留言|分享|Like|Comment|Share|最相關|所有留言|查看更多|顯示更多|See more|Most relevant|回覆|Reply|撰寫回應|撰寫留言|Write a comment|翻譯年糕)$/i.test(t)) return;
                const key = t.substring(0, 80);
                if (!textSet.has(key)) {
                    textSet.add(key);
                    textParts.push(t);
                }
            });
            let text = textParts.join("\\n").trim();
            if (text.length === 0 && !child.querySelector('img[src*="scontent"], video')) continue;

            // ── 反应数 + 评论数 + 分享数 ──
            let reactions = 0, commentCount = 0, shareCount = 0;
            child.querySelectorAll("[aria-label]").forEach((el) => {
                let inArt = false;
                let p = el.parentElement;
                while (p && p !== child) {
                    if (p.getAttribute("role") === "article") { inArt = true; break; }
                    p = p.parentElement;
                }
                if (inArt) return;
                const label = el.getAttribute("aria-label") || "";
                if (label.length > 80) return;
                const zhMatches = label.matchAll(/(讚|大心|哈哈|加油|嗚嗚|怒)[：:]\\s*(\\d+)\\s*人?/g);
                for (const m of zhMatches) reactions += parseInt(m[2]);
                const enMatch = label.match(/(\\d+)\\s*(likes?|reactions?|people reacted)/i);
                if (enMatch) reactions = Math.max(reactions, parseInt(enMatch[1]));
                if (commentCount === 0) {
                    const cm = label.match(/(\\d+)\\s*(則留言|comments?|則回應)/i);
                    if (cm) commentCount = parseInt(cm[1]);
                }
                if (shareCount === 0) {
                    const sh = label.match(/(\\d+)\\s*(次分享|shares?)/i);
                    if (sh) shareCount = parseInt(sh[1]);
                }
            });
            if (commentCount === 0 || shareCount === 0) {
                child.querySelectorAll("span, a").forEach((el) => {
                    if (commentCount > 0 && shareCount > 0) return;
                    let inArt = false;
                    let p = el.parentElement;
                    while (p && p !== child) {
                        if (p.getAttribute("role") === "article") { inArt = true; break; }
                        p = p.parentElement;
                    }
                    if (inArt) return;
                    const t = el.textContent.trim();
                    if (t.length > 25 || t.length < 2) return;
                    if (commentCount === 0) {
                        const cm = t.match(/^(\\d+)\\s*(則留言|comments?|則回應|条评论)$/i);
                        if (cm) commentCount = parseInt(cm[1]);
                    }
                    if (shareCount === 0) {
                        const sh = t.match(/^(\\d+)\\s*(次分享|shares?|次轉發)$/i);
                        if (sh) shareCount = parseInt(sh[1]);
                    }
                });
            }

            // ── 图片/视频 ──
            const hasImage = child.querySelector('img[src*="scontent"]') !== null;
            const hasVideo = child.querySelector("video") !== null;

            // ── 评论 ──
            const comments = extractComments(child);

            processedIds.add(postId);
            results.push({
                author, text: text.substring(0, 5000), date: "", post_url: postUrl, post_id: postId,
                reactions, comment_count: commentCount, share_count: shareCount,
                has_image: hasImage, has_video: hasVideo, text_length: text.length,
                comments, visible_comment_count: comments.length,
                extracted_at: new Date().toISOString(),
            });
        } catch (e) { /* skip */ }
    }

    // 保存已处理 ID 到全局变量
    window.__processedPostIds = Array.from(processedIds);
    return { posts: results, processedIds: window.__processedPostIds };
}
"""

JS_EXPAND_SEE_MORE = """
() => {
    const feed = document.querySelector('div[role="feed"]');
    if (!feed) return 0;
    let expanded = 0;
    feed.querySelectorAll('div[role="button"], span[role="button"]').forEach((el) => {
        const txt = el.textContent.trim().toLowerCase();
        if (txt === "see more" || txt === "查看更多" || txt === "顯示更多" ||
            txt === "もっと見る" || txt === "더 보기" || txt === "voir plus") {
            el.click();
            expanded++;
        }
    });
    return expanded;
}
"""

JS_CLEANUP_DOM = """
() => {
    const feed = document.querySelector('div[role="feed"]');
    if (!feed) return 0;
    let cleaned = 0;
    for (let i = 0; i < feed.children.length; i++) {
        const child = feed.children[i];
        if (child.dataset.cleaned === "1") continue;
        const rect = child.getBoundingClientRect();
        if (rect.bottom > -3000) continue;
        const h = child.offsetHeight;
        // 先移除图片/视频/iframe 释放内存
        child.querySelectorAll('img, video, iframe, source').forEach(el => el.remove());
        const placeholder = document.createElement("div");
        placeholder.style.height = h + "px";
        placeholder.dataset.cleaned = "1";
        feed.replaceChild(placeholder, child);
        cleaned++;
        i--;
    }
    return cleaned;
}
"""

JS_CHECK_LOADING = """
() => {
    const feed = document.querySelector('div[role="feed"]');
    const hasSpinner = !!(feed && feed.querySelector('[role="progressbar"]'));
    const atBottom = (window.innerHeight + window.scrollY) >= (document.body.scrollHeight - 500);
    const scrollHeight = document.body.scrollHeight;
    return { hasSpinner, atBottom, scrollHeight };
}
"""

JS_SWITCH_TO_NEW_POSTS = """
() => {
    // 点击排序下拉菜单，切换到 "New Posts" / "最新帖子"
    // Facebook 群组排序按钮通常在 feed 上方
    const sortLabels = ['most relevant', 'top posts', '最相關', '熱門貼文', 'new activity', 'recent activity'];
    const newLabels = ['new posts', 'new', '新貼文', '最新帖子', '新帖子'];

    // 方法1: 找到排序区域的按钮/链接并点击
    const allElements = document.querySelectorAll('span, a, div[role="button"]');
    for (const el of allElements) {
        const t = (el.textContent || '').trim().toLowerCase();
        // 找到当前显示的排序标签（如 "Most relevant"），点击它打开下拉
        if (sortLabels.some(s => t === s) || (t.includes('sort') && t.length < 30)) {
            el.click();
            return 'clicked_sort_menu';
        }
    }
    return 'sort_menu_not_found';
}
"""

JS_SELECT_NEW_POSTS = """
() => {
    // 在已打开的下拉菜单中选择 "New posts"
    const menuItems = document.querySelectorAll('div[role="menuitem"], div[role="menuitemradio"], div[role="option"], span');
    for (const item of menuItems) {
        const t = (item.textContent || '').trim().toLowerCase();
        if (t === 'new posts' || t === 'new' || t === '新貼文' || t === '最新帖子' || t === '新帖子' || t === 'newest') {
            item.click();
            return 'selected_new_posts';
        }
    }
    // 也尝试 menuitem 里的 radio 按钮
    const radios = document.querySelectorAll('input[type="radio"], div[role="radio"]');
    for (const r of radios) {
        const label = r.closest('[role="menuitem"], [role="menuitemradio"], label');
        if (label) {
            const t = (label.textContent || '').trim().toLowerCase();
            if (t.includes('new') || t.includes('最新') || t.includes('新貼文')) {
                r.click();
                return 'selected_new_posts_radio';
            }
        }
    }
    return 'new_posts_not_found';
}
"""


# ── Cookie 管理 ──────────────────────────────────────────────────

def save_cookies(context: BrowserContext, path: str):
    cookies = context.cookies()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"  Cookie 已保存 ({len(cookies)} 条)")


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


def save_checkpoint(group_id: str, posts: list, group_info: dict):
    path = _checkpoint_path(group_id)
    data = {
        "group_id": group_id,
        "group_info": group_info,
        "posts": posts,
        "saved_at": datetime.now().isoformat(),
        "total_posts": len(posts),
    }
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    print(f"  [checkpoint] 已保存: {len(posts)} 条帖子")


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


# ── 工具函数 ──────────────────────────────────────────────────────

def extract_group_id(url: str) -> str:
    url = url.rstrip("/")
    match = re.search(r"/groups/([^/?#]+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"无法从 URL 提取群组 ID: {url}")


def rand_delay(lo: float, hi: float):
    time.sleep(random.uniform(lo, hi))


# ── 核心采集逻辑 ──────────────────────────────────────────────────

def login_interactive(page: Page, context: BrowserContext):
    print("\n=== 手动登录模式 ===")
    print("浏览器已打开 Facebook 登录页面，请手动登录。")
    print("登录成功后（看到新闻动态），按 Enter 继续...")
    page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
    input()
    # 检查是否仍在登录表单页（而非 URL 包含 login 字样，因为登录成功后
    # 重定向 URL 也可能含 login_attempt 等参数）
    still_on_login = page.query_selector('input[name="email"], input[name="pass"], #loginbutton')
    if still_on_login:
        print("似乎尚未登录成功，请确认后再次运行。")
        sys.exit(1)
    save_cookies(context, COOKIE_FILE)
    print(f"登录成功！(当前 URL: {page.url})\n")


def dismiss_popups(page: Page):
    selectors = [
        'button[data-cookiebanner="accept_button"]',
        'button[title="Allow all cookies"]',
        'button[title="允许所有 Cookie"]',
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
    for sel in ['h1 a span', 'h1 span', 'div[role="main"] h1']:
        try:
            el = page.query_selector(sel)
            if el:
                name = el.inner_text().strip()
                if name:
                    return name
        except Exception:
            pass
    return "Unknown Group"


def _try_recovery(page: Page, no_new_count: int, group_url: str,
                   all_posts: list, existing_ids: set) -> list:
    """多轮多策略恢复尝试，返回新帖子列表（空列表表示确认到底）。"""
    for recovery_round in range(1, MAX_RECOVERY_ROUNDS + 1):
        print(f"  连续 {no_new_count} 次无新内容，恢复尝试 第{recovery_round}轮...")

        # 策略1: 大幅滚动
        page.evaluate("window.scrollBy({top: 5000, behavior: 'instant'})")
        rand_delay(5.0, 8.0)
        result = page.evaluate(JS_EXTRACT_POSTS)
        recovered = result.get("posts", [])
        if recovered:
            return recovered

        # 策略2: 滚到底部
        print(f"  策略2: 滚到页面底部...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        rand_delay(6.0, 10.0)
        result = page.evaluate(JS_EXTRACT_POSTS)
        recovered = result.get("posts", [])
        if recovered:
            return recovered

        # 策略3: 回顶部再下来
        print(f"  策略3: 滚回顶部再下来...")
        current_pos = page.evaluate("window.scrollY")
        page.evaluate("window.scrollTo(0, 0)")
        rand_delay(2.0, 4.0)
        page.evaluate(f"window.scrollTo(0, {current_pos})")
        rand_delay(5.0, 8.0)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        rand_delay(6.0, 10.0)
        result = page.evaluate(JS_EXTRACT_POSTS)
        recovered = result.get("posts", [])
        if recovered:
            return recovered

        # 策略4: 点击"加载更多帖子"按钮
        print(f"  策略4: 尝试点击加载更多按钮...")
        try:
            clicked = page.evaluate("""() => {
                const btns = document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"]');
                for (const btn of btns) {
                    const t = btn.textContent.trim().toLowerCase();
                    if (t.includes('see more posts') || t.includes('more posts') ||
                        t.includes('load more') || t.includes('查看更多帖子') ||
                        t.includes('顯示更多帖子') || t.includes('更多貼文') ||
                        t.includes('show more')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")
            if clicked:
                print(f"  已点击加载更多按钮")
                rand_delay(8.0, 12.0)
                result = page.evaluate(JS_EXTRACT_POSTS)
                recovered = result.get("posts", [])
                if recovered:
                    return recovered
        except Exception:
            pass

        # 策略5: 长等待 + 缓慢滚动
        wait_time = 15 + recovery_round * 5
        print(f"  策略5: 长等待 {wait_time}s + 缓慢滚动...")
        time.sleep(wait_time)
        for _ in range(5):
            page.evaluate("window.scrollBy({top: 800, behavior: 'smooth'})")
            time.sleep(2)
        rand_delay(5.0, 8.0)
        result = page.evaluate(JS_EXTRACT_POSTS)
        recovered = result.get("posts", [])
        if recovered:
            return recovered

        # 策略6（最后一轮）: 刷新页面 + 快速滚到底部
        if recovery_round == MAX_RECOVERY_ROUNDS:
            print(f"  策略6: 刷新页面重新加载...")
            # 先保存已处理的 ID
            all_ids = list(existing_ids | {p["post_id"] for p in all_posts})
            try:
                page.reload(wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                dismiss_popups(page)
                time.sleep(2)
                # 注入已有 ID 避免重复
                page.evaluate(f"window.__processedPostIds = {json.dumps(all_ids)}")
                # 快速滚动加载新内容
                print(f"  刷新后快速滚动...")
                for i in range(30):
                    page.evaluate("window.scrollBy({top: 2000, behavior: 'instant'})")
                    time.sleep(1.5)
                    if i % 5 == 4:
                        result = page.evaluate(JS_EXTRACT_POSTS)
                        recovered = result.get("posts", [])
                        if recovered:
                            return recovered
            except Exception as e:
                print(f"  刷新失败: {e}")

    return []


def run_scraper(args):
    """主采集流程。"""
    group_id = extract_group_id(args.group_url)
    group_url = args.group_url.rstrip("/")

    # 加载 checkpoint
    existing_posts = []
    existing_ids = set()

    if args.resume:
        cp = load_checkpoint(group_id)
        if cp:
            existing_posts = cp["posts"]
            existing_ids = {p["post_id"] for p in existing_posts}
            print(f"  从 checkpoint 恢复: 已有 {len(existing_posts)} 条帖子")

    remaining = args.max_posts - len(existing_posts)
    if remaining <= 0:
        print(f"已达到目标数量 ({args.max_posts})，直接输出。")
        return existing_posts, {"group_name": "Resumed", "group_url": group_url}

    print(f"\n开始采集: {group_url}")
    print(f"  目标: {args.max_posts} 条帖子 (已有 {len(existing_posts)}，还需 {remaining})")

    with sync_playwright() as p:
        launch_opts = dict(
            headless=not args.login,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        if args.proxy:
            launch_opts["proxy"] = {"server": args.proxy}
        browser = p.chromium.launch(**launch_opts)
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

        # 登录
        if args.login:
            login_interactive(page, context)
        elif not load_cookies(context, COOKIE_FILE):
            print("未找到 Cookie 文件。请先用 --login 参数登录。")
            browser.close()
            sys.exit(1)

        # 进入群组
        print(f"正在打开群组...")
        page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        if page.query_selector('input[name="email"], input[name="pass"], #loginbutton'):
            print("Cookie 已过期，请重新使用 --login 登录。")
            browser.close()
            sys.exit(1)

        dismiss_popups(page)
        time.sleep(1)

        group_name = get_group_name(page)
        group_info = {"group_name": group_name, "group_url": group_url}
        print(f"  群组名称: {group_name}")

        # 切换到"最新帖子"排序（默认 Most Relevant 只显示部分帖子）
        print(f"  切换到最新帖子排序...")
        try:
            sort_result = page.evaluate(JS_SWITCH_TO_NEW_POSTS)
            if sort_result == 'clicked_sort_menu':
                time.sleep(2)
                select_result = page.evaluate(JS_SELECT_NEW_POSTS)
                print(f"  排序切换: {select_result}")
                time.sleep(3)  # 等待 feed 刷新
            else:
                print(f"  排序菜单未找到 ({sort_result})，使用默认排序")
        except Exception as e:
            print(f"  排序切换失败: {e}，使用默认排序")

        # 将已有 ID 注入浏览器，避免重复提取
        if existing_ids:
            page.evaluate(f"window.__processedPostIds = {json.dumps(list(existing_ids))}")

        # ── 主循环（移植篡改猴 startAutoScroll 逻辑）──
        all_posts = list(existing_posts)
        scroll_count = 0
        no_new_count = 0
        last_checkpoint_count = len(existing_posts)
        total_dom_cleaned = 0
        last_scroll_height = 0

        while len(all_posts) < args.max_posts:
            # 展开"See more"（每 10 次滚动一次）
            if scroll_count % 10 == 0:
                try:
                    page.evaluate(JS_EXPAND_SEE_MORE)
                except Exception:
                    pass

            # DOM 瘦身（每 30 次滚动一次）
            if scroll_count % DOM_CLEANUP_EVERY == 0 and len(all_posts) > 20:
                try:
                    cleaned = page.evaluate(JS_CLEANUP_DOM)
                    if cleaned > 0:
                        total_dom_cleaned += cleaned
                        print(f"  [cleanup] 清理 {cleaned} 个 DOM 元素 (累计 {total_dom_cleaned})")
                except Exception:
                    pass

            # 提取帖子（每 3 次滚动一次，与篡改猴一致）
            new_found = 0
            if scroll_count % 3 == 0:
                try:
                    result = page.evaluate(JS_EXTRACT_POSTS)
                    new_posts = result.get("posts", [])
                    if new_posts:
                        all_posts.extend(new_posts)
                        new_found = len(new_posts)
                        print(f"  +{new_found} 新帖 (总计 {len(all_posts)}/{args.max_posts})")
                except Exception as e:
                    print(f"  提取出错: {e}")

            # 滚动
            step = random.randint(SCROLL_STEP_MIN, SCROLL_STEP_MAX)
            page.evaluate(f'window.scrollBy({{top: {step}, behavior: "instant"}})')
            scroll_count += 1

            # 无新内容检测
            if new_found == 0 and scroll_count % 3 == 0:
                loading = page.evaluate(JS_CHECK_LOADING)
                current_height = loading.get("scrollHeight", 0)

                if loading.get("hasSpinner") and not loading.get("atBottom"):
                    # 页面正在加载，耐心等待
                    no_new_count += 1
                    if no_new_count % 10 == 0 and no_new_count > 0:
                        print(f"  页面加载中... 等待 ({no_new_count}次)")
                    rand_delay(1.0, 2.0)
                    if no_new_count >= 80:
                        print(f"  等待过久，尝试刺激加载...")
                        page.evaluate("window.scrollBy({top: -500, behavior: 'instant'})")
                        time.sleep(2)
                        page.evaluate("window.scrollBy({top: 1500, behavior: 'instant'})")
                        time.sleep(5)
                        no_new_count = 50
                else:
                    no_new_count += 1
                    if no_new_count >= MAX_NO_NEW_RETRIES:
                        recovered = _try_recovery(page, no_new_count, group_url, all_posts, existing_ids)
                        if recovered:
                            all_posts.extend(recovered)
                            no_new_count = 0
                            print(f"  恢复加载！+{len(recovered)} 帖子 (总计 {len(all_posts)})")
                        else:
                            print(f"  确认到底，共采集 {len(all_posts)} 条帖子")
                            break

                last_scroll_height = current_height
            elif new_found > 0:
                no_new_count = 0

            # Checkpoint
            if len(all_posts) - last_checkpoint_count >= CHECKPOINT_EVERY:
                save_checkpoint(group_id, all_posts, group_info)
                last_checkpoint_count = len(all_posts)

            # 拟人暂停
            if scroll_count % PAUSE_EVERY_N == 0:
                pause = random.uniform(PAUSE_DURATION_MIN, PAUSE_DURATION_MAX)
                print(f"  [pause] 第 {scroll_count} 次滚动，暂停 {pause:.0f}s... ({len(all_posts)} 条)")
                time.sleep(pause)

            if random.random() < MICRO_PAUSE_CHANCE:
                rand_delay(MICRO_PAUSE_MIN, MICRO_PAUSE_MAX)

            rand_delay(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX)

        # 最终保存
        save_checkpoint(group_id, all_posts, group_info)
        save_cookies(context, COOKIE_FILE)
        browser.close()

    return all_posts, group_info


# ── 输出构建（兼容 analyze.py + 保留篡改猴全部字段）────────────────

def build_output(posts: list, group_info: dict) -> dict:
    # 按 reactions 降序排序 + 添加 index（与篡改猴 buildExportData 一致）
    posts_sorted = sorted(posts, key=lambda p: p.get("reactions", 0), reverse=True)
    for i, p in enumerate(posts_sorted):
        p["index"] = i + 1

    comments_flat = []
    for p in posts_sorted:
        for ci, c in enumerate(p.get("comments", [])):
            comments_flat.append({
                **c,
                "post_url": p.get("post_url", ""),
                "post_index": p["index"],
                "comment_index": ci + 1,
            })

    return {
        "group_url": group_info.get("group_url", ""),
        "group_name": group_info.get("group_name", "Unknown"),
        "extraction_time": datetime.now().isoformat(),
        "total_posts": len(posts_sorted),
        "total_comments": len(comments_flat),
        "posts": posts_sorted,
        "comments_flat": comments_flat,
    }


# ── 数据完整性校验 ────────────────────────────────────────────────

def validate_output(data: dict) -> list:
    warnings = []
    posts = data.get("posts", [])
    if not posts:
        warnings.append("FAIL: 无帖子数据")
        return warnings

    # 空文本帖子
    empty_text = sum(1 for p in posts if not p.get("text", "").strip())
    if empty_text > 0:
        pct = empty_text / len(posts) * 100
        warnings.append(f"WARN: {empty_text} 条帖子 ({pct:.0f}%) 文本为空")

    # post_id 唯一性
    ids = [p.get("post_id", "") for p in posts]
    dupes = len(ids) - len(set(ids))
    if dupes > 0:
        warnings.append(f"WARN: 发现 {dupes} 个重复 post_id")

    # 评论采集率
    posts_with_count = sum(1 for p in posts if p.get("comment_count", 0) > 0)
    posts_with_actual = sum(1 for p in posts if len(p.get("comments", [])) > 0)
    if posts_with_count > 0:
        rate = posts_with_actual / posts_with_count * 100
        warnings.append(f"INFO: 评论采集率 {rate:.0f}% ({posts_with_actual}/{posts_with_count})")

    # 总计
    total_cmts = sum(len(p.get("comments", [])) for p in posts)
    total_reactions = sum(p.get("reactions", 0) for p in posts)
    warnings.append(f"INFO: {len(posts)} 帖子, {total_cmts} 评论, {total_reactions} 反应")

    return warnings


# ── 入口 ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Facebook 群组数据采集工具 (Playwright)")
    parser.add_argument("--group-url", help="Facebook 群组 URL")
    parser.add_argument("--max-posts", type=int, default=500, help="最多采集帖子数 (默认 500)")
    parser.add_argument("--output", "-o", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--login", action="store_true", help="打开浏览器窗口手动登录")
    parser.add_argument("--resume", action="store_true", help="从上次 checkpoint 断点续抓")
    parser.add_argument("--validate-only", default=None, help="仅验证已有 JSON 文件的完整性")
    parser.add_argument("--proxy", default=None, help="代理服务器地址 (如 http://127.0.0.1:7890 或 socks5://127.0.0.1:1080)")
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

    if not args.group_url:
        parser.error("--group-url 是必需的（除非使用 --validate-only）")

    # 采集
    posts, group_info = run_scraper(args)
    if not posts:
        print("未采集到任何帖子。")
        sys.exit(1)

    # 构建输出
    output = build_output(posts, group_info)

    # 验证
    print("\n=== 数据完整性检查 ===")
    for w in validate_output(output):
        print(f"  {w}")

    # 保存
    group_id = extract_group_id(args.group_url)
    output_path = args.output or f"facebook_data_{group_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  数据已保存: {output_path}")
    print(f"  可直接分析: python analyze.py {output_path}")

    clear_checkpoint(group_id)


if __name__ == "__main__":
    main()
