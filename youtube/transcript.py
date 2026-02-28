"""
视频转录提取模块

使用 youtube-transcript-api v1.x 新 API 获取字幕/转录文本。
"""

import logging
import time
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
)

logger = logging.getLogger(__name__)

# 全局实例（v1.x 要求实例化）
_ytt_api = YouTubeTranscriptApi()


def _fetch_transcript_once(video_id):
    """
    单次尝试获取字幕，优先英文，其次其他语言。

    返回: (entries, source) 或抛出异常
    """
    # 优先尝试英文
    try:
        transcript = _ytt_api.fetch(video_id, languages=['en'])
        entries = transcript.to_raw_data()
        source = f"{'auto' if transcript.is_generated else 'manual'}_en"
        return entries, source
    except (TranscriptsDisabled, NoTranscriptFound):
        raise
    except Exception:
        pass

    # 英文不可用，尝试列出所有可用语言
    transcript_list = _ytt_api.list(video_id)
    available = list(transcript_list)
    if not available:
        return None, "no_transcript"

    first = available[0]
    lang = first.language_code
    transcript = _ytt_api.fetch(video_id, languages=[lang])
    entries = transcript.to_raw_data()
    source = f"{'auto' if transcript.is_generated else 'manual'}_{lang}"
    return entries, source


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
            return _fetch_transcript_once(video_id)
        except TranscriptsDisabled:
            return None, "disabled"
        except NoTranscriptFound:
            return None, "not_found"
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
        segment_minutes: 每段时长（分钟），Tier A 用 3，Tier B 用 5

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
