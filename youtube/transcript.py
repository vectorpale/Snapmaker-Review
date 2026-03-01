"""
视频转录提取模块

使用 yt-dlp 获取字幕/转录文本（替代 youtube-transcript-api，解决 IP 封锁问题）。
"""

import json
import logging
import os
import shutil
import time

import yt_dlp

logger = logging.getLogger(__name__)

# yt-dlp 日志纳入统一管理
_ytdl_logger = logging.getLogger("yt_dlp")

# 检测 Node.js 路径（yt-dlp 需要 JS runtime 解析 YouTube player JS）
_node_path = shutil.which("node") or "/opt/node22/bin/node"


def _find_en_lang(subs_dict):
    """在字幕字典中查找英文语言码（支持 en, en-US, en-GB, en-orig 等变体）。"""
    if "en" in subs_dict:
        return "en"
    for lang in subs_dict:
        if lang.startswith("en"):
            return lang
    return None


def _get_json3_url(format_list):
    """从字幕格式列表中找到 json3 格式的 URL。"""
    for fmt in format_list:
        if fmt.get("ext") == "json3":
            return fmt["url"]
    return None


def _extract_subtitles(video_id):
    """
    使用 yt-dlp 提取字幕（单次 HTTP 请求）。

    策略: 手动英文 → 自动英文 → 其他语言手动 → 其他语言自动

    返回: (entries, source) 或抛出异常
        entries: [{"text": ..., "start": ..., "duration": ...}, ...]
        source: "manual_en" / "auto_en" / "manual_XX" / "auto_XX"
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    # 单次请求：提取视频信息（含字幕 URL）
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "logger": _ytdl_logger,
        # 启用 EJS challenge solver（从 GitHub 下载，需要 Node.js runtime）
        # 解决 "n challenge solving failed" 警告，优化请求避免 429 限流
        "remote_components": ["ejs:github"],
    }

    # Node.js runtime（EJS solver 和 JS challenge 都需要）
    if os.path.isfile(_node_path):
        ydl_opts["js_runtimes"] = {"node": {"path": _node_path}}

    # Cookie 支持（解决 YouTube bot 检测 / "Sign in to confirm" 错误）
    # 方式1: 指定 cookies.txt 文件路径，如 YOUTUBE_COOKIES=/path/to/cookies.txt
    # 方式2: 从浏览器自动提取，如 YOUTUBE_COOKIES_BROWSER=chrome
    cookies_file = os.environ.get("YOUTUBE_COOKIES")
    cookies_browser = os.environ.get("YOUTUBE_COOKIES_BROWSER")
    if cookies_file and os.path.isfile(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
    elif cookies_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_browser,)

    # 代理支持（从环境变量读取）
    proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy_url:
        ydl_opts["proxy"] = proxy_url
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        manual_subs = info.get("subtitles", {})
        auto_subs = info.get("automatic_captions", {})

        # 确定字幕来源（优先英文，支持 en/en-US/en-GB/en-orig 等变体）
        sub_lang = None
        is_auto = False
        sub_formats = None

        en_manual = _find_en_lang(manual_subs)
        if en_manual:
            sub_lang = en_manual
            is_auto = False
            sub_formats = manual_subs[en_manual]
        else:
            en_auto = _find_en_lang(auto_subs)
            if en_auto:
                sub_lang = en_auto
                is_auto = True
                sub_formats = auto_subs[en_auto]
            elif manual_subs:
                sub_lang = next(iter(manual_subs))
                is_auto = False
                sub_formats = manual_subs[sub_lang]
            elif auto_subs:
                for lang in auto_subs:
                    if lang != "live_chat":
                        sub_lang = lang
                        is_auto = True
                        sub_formats = auto_subs[lang]
                        break

        if not sub_lang or not sub_formats:
            return None, "no_transcript"

        # 直接从 extract_info 返回的 URL 获取 json3 数据
        # 使用 ydl.urlopen() 携带 session cookies/headers，避免 429 限流
        json3_url = _get_json3_url(sub_formats)
        if not json3_url:
            raise RuntimeError(
                f"json3 格式不可用 (video={video_id}, lang={sub_lang})"
            )

        resp = ydl.urlopen(json3_url)
        sub_data = json.loads(resp.read().decode("utf-8"))

    # 解析 json3 格式为 entries
    entries = _parse_json3(sub_data)
    if not entries:
        return None, "parse_failed"

    source = f"{'auto' if is_auto else 'manual'}_{sub_lang}"
    return entries, source


def _parse_json3(sub_data):
    """
    解析 yt-dlp json3 字幕格式。

    json3 格式:
    {"events": [{"tStartMs": 1234, "dDurationMs": 5000, "segs": [{"utf8": "text"}]}, ...]}

    返回: [{"text": ..., "start": ..., "duration": ...}, ...]
    """
    entries = []
    for event in sub_data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue

        text = "".join(seg.get("utf8", "") for seg in segs).strip()
        if not text:
            continue

        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)

        entries.append({
            "text": text,
            "start": start_ms / 1000.0,
            "duration": duration_ms / 1000.0,
        })

    return entries


def get_transcript(video_id, max_retries=3, base_delay=2.0):
    """
    获取视频字幕/转录，带指数退避重试。

    返回: (entries: list[dict] | None, source: str)
        entries: [{"text": ..., "start": ..., "duration": ...}, ...]
        source: "manual_en" / "auto_en" / "manual_XX" / "auto_XX" / 错误原因
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _extract_subtitles(video_id)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"字幕获取失败 (video={video_id}), "
                    f"{delay}s 后重试 ({attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(delay)

    logger.error(f"字幕获取最终失败 (video={video_id}): {last_error}")
    return None, "list_failed"


def format_timestamp(seconds):
    """将秒数转为 H:MM:SS 或 M:SS 格式"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def segment_transcript(entries, segment_minutes=3):
    """
    将转录条目按时间分段。

    参数:
        entries: [{"text": ..., "start": ..., "duration": ...}, ...]
        segment_minutes: 每段时长（分钟）

    返回: list[dict]，每段含 start_time, start_timestamp, end_timestamp, full_text, texts
    """
    if not entries:
        return []

    segments = []
    current_segment = {"start_time": 0, "start_timestamp": "0:00", "texts": []}
    segment_boundary = segment_minutes * 60

    for entry in entries:
        start = entry.get("start", 0)
        text = entry.get("text", "")

        if start >= segment_boundary:
            current_segment["end_time"] = segment_boundary
            current_segment["end_timestamp"] = format_timestamp(segment_boundary)
            current_segment["full_text"] = " ".join(current_segment["texts"])
            segments.append(current_segment)
            segment_boundary += segment_minutes * 60
            current_segment = {
                "start_time": start,
                "start_timestamp": format_timestamp(start),
                "texts": [],
            }

        current_segment["texts"].append(text)

    # 最后一段
    if current_segment["texts"]:
        last_start = entries[-1].get("start", 0)
        current_segment["end_timestamp"] = format_timestamp(last_start)
        current_segment["full_text"] = " ".join(current_segment["texts"])
        segments.append(current_segment)

    return segments
