"""
分析模块

包含赞助检测、内容关键时间戳提取、过滤分级、情感分析、主题标注。
"""

import re
from collections import Counter

from config import (
    SPONSOR_PATTERNS, KEY_INFO_PATTERNS, TOPIC_KEYWORDS,
    POSITIVE_KW, NEGATIVE_KW, RELEVANCE_KEYWORDS, KNOWN_CHANNEL_NAMES,
)


# ===== 赞助/样机检测 =====

def detect_sponsor_status(description, transcript_text=""):
    """
    分析视频描述和转录文本，判断赞助关系。

    返回: {
        "is_sponsored": bool,
        "confidence": str,        # high/medium/low
        "sponsor_type": str,      # sponsored/review_sample/affiliate_only/self_purchased/unknown
        "signals": list,
        "raw_matches": list,
    }
    """
    combined_text = (description + "\n" + transcript_text).lower()
    signals = []
    raw_matches = []

    for category, patterns in SPONSOR_PATTERNS.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, combined_text, re.IGNORECASE))
            if matches:
                for m in matches:
                    start = max(0, m.start() - 30)
                    end = min(len(combined_text), m.end() + 30)
                    context = combined_text[start:end].strip()
                    raw_matches.append({
                        "category": category,
                        "matched": m.group(),
                        "context": context,
                    })
                signals.append(category)
                break

    signals = list(set(signals))

    has_explicit = "explicit_sponsor" in signals
    has_sample = "review_sample" in signals
    has_affiliate = "affiliate" in signals
    has_self = "self_purchased" in signals

    if has_explicit:
        return {
            "is_sponsored": True, "confidence": "high",
            "sponsor_type": "sponsored", "signals": signals,
            "raw_matches": raw_matches,
        }
    elif has_sample:
        return {
            "is_sponsored": True, "confidence": "high",
            "sponsor_type": "review_sample", "signals": signals,
            "raw_matches": raw_matches,
        }
    elif has_self:
        return {
            "is_sponsored": False, "confidence": "high",
            "sponsor_type": "self_purchased", "signals": signals,
            "raw_matches": raw_matches,
        }
    elif has_affiliate:
        return {
            "is_sponsored": False, "confidence": "medium",
            "sponsor_type": "affiliate_only", "signals": signals,
            "raw_matches": raw_matches,
        }
    else:
        return {
            "is_sponsored": False, "confidence": "low",
            "sponsor_type": "unknown", "signals": signals,
            "raw_matches": raw_matches,
        }


# ===== ISO 时长解析 =====

def parse_duration(iso_duration):
    """将 ISO 8601 时长 (PT1H23M45S) 转为秒数"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


# ===== 相关性与质量过滤 =====

def is_relevant(video):
    """Layer 1: 标题必须含 'u1'（确保是 U1 相关视频，含对比视频）"""
    title_lower = video["title"].lower()
    return "u1" in title_lower


def passes_quality(video):
    """Layer 2: 时长 ≥ 60s 且观看量 ≥ 100"""
    duration_sec = parse_duration(video["duration"])
    if duration_sec < 60:
        return False
    if video["view_count"] < 100:
        return False
    return True


# ===== Tier 分级 =====

def classify_tier(video, view_threshold):
    """
    Tier A 条件（满足任一）:
    - 播放量 ≥ view_threshold
    - 评论数 ≥ 30
    - 来自已知评测频道
    - 时长 ≥ 10 分钟且播放量 ≥ 500
    """
    if video["view_count"] >= view_threshold:
        return "A"
    if video["comment_count"] >= 30:
        return "A"
    if any(kc in video["channel"].lower() for kc in KNOWN_CHANNEL_NAMES):
        return "A"
    if video.get("duration_seconds", 0) >= 600 and video["view_count"] >= 500:
        return "A"
    return "B"


def auto_select_tier_threshold(view_counts):
    """根据播放量分布自动选择 Tier A 阈值"""
    count_5k = sum(1 for vc in view_counts if vc >= 5000)
    count_3k = sum(1 for vc in view_counts if vc >= 3000)

    if count_5k >= 30:
        return 5000
    elif count_3k >= 25:
        return 3000
    else:
        return 1000


# ===== 内容关键信息检测 =====

def find_key_moments(segments, video_title=""):
    """从转录分段中检测关键信息时间戳"""
    key_moments = []
    for seg in segments:
        text = seg.get("full_text", "")
        if not text:
            continue
        text_lower = text.lower()
        for info_type, config in KEY_INFO_PATTERNS.items():
            for pattern in config["patterns"]:
                matches = list(re.finditer(pattern, text_lower))
                if matches:
                    for match in matches:
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end].strip()
                        key_moments.append({
                            "timestamp": seg["start_timestamp"],
                            "timestamp_seconds": seg.get("start_time", 0),
                            "type": info_type,
                            "label": config["label"],
                            "matched_text": match.group(),
                            "context": f"...{context}...",
                            "segment_text": text[:200],
                        })
                    break

    # 去重
    seen = set()
    unique = []
    for m in key_moments:
        key = (m["type"], m["timestamp"])
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return sorted(unique, key=lambda x: x["timestamp_seconds"])


# ===== 评论情感分析 =====

def analyze_sentiment(text):
    """基于关键词的简单情感分析"""
    text_lower = text.lower()
    pos = sum(1 for kw in POSITIVE_KW if kw in text_lower)
    neg = sum(1 for kw in NEGATIVE_KW if kw in text_lower)
    if pos > 0 and neg == 0:
        return "positive"
    if neg > 0 and pos == 0:
        return "negative"
    if pos > 0 and neg > 0:
        return "mixed"
    return "neutral"


# ===== 评论主题标注 =====

def tag_topics(text):
    """为评论文本标注主题"""
    text_lower = text.lower()
    return [topic for topic, kws in TOPIC_KEYWORDS.items()
            if any(kw in text_lower for kw in kws)]
