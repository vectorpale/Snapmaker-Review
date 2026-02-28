"""
视频转录提取模块

使用 yt-dlp 获取字幕/转录文本（替代 youtube-transcript-api，解决 IP 封锁问题）。
"""

import json
import logging
import os
import tempfile
import time

import yt_dlp

logger = logging.getLogger(__name__)


def _extract_subtitles(video_id):
    """
    使用 yt-dlp 提取字幕。

    策略: 手动英文 → 自动英文 → 其他语言手动 → 其他语言自动

    返回: (entries, source) 或抛出异常
        entries: [{"text": ..., "start": ..., "duration": ...}, ...]
        source: "manual_en" / "auto_en" / "manual_XX" / "auto_XX"
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    # 第一步：提取视频信息，查看可用字幕
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    manual_subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})

    # 确定字幕来源
    sub_lang = None
    is_auto = False

    if "en" in manual_subs:
        sub_lang = "en"
        is_auto = False
    elif "en" in auto_subs:
        sub_lang = "en"
        is_auto = True
    elif manual_subs:
        sub_lang = next(iter(manual_subs))
        is_auto = False
    elif auto_subs:
        # 自动字幕中排除 "live_chat"
        for lang in auto_subs:
            if lang != "live_chat":
                sub_lang = lang
                is_auto = True
                break

    if not sub_lang:
        return None, "no_transcript"

    # 第二步：下载字幕文件（json3 格式以获取时间戳）
    with tempfile.TemporaryDirectory() as tmpdir:
        out_template = os.path.join(tmpdir, "%(id)s.%(ext)s")
        download_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": not is_auto,
            "writeautomaticsub": is_auto,
            "subtitleslangs": [sub_lang],
            "subtitlesformat": "json3",
            "outtmpl": out_template,
        }

        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([url])

        # 查找下载的字幕文件
        sub_file = None
        for fname in os.listdir(tmpdir):
            if fname.endswith(".json3"):
                sub_file = os.path.join(tmpdir, fname)
                break

        if not sub_file:
            return None, "download_failed"

        with open(sub_file, "r", encoding="utf-8") as f:
            sub_data = json.load(f)

    # 第三步：解析 json3 格式为 entries
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
        # 跳过空行和纯换行
        if not text or text == "\n":
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
