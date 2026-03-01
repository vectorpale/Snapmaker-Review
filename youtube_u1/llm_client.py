"""
LLM 深度分析模块

使用阿里云 Qwen（OpenAI 兼容接口）对视频字幕和评论进行深度语义分析。
"""

import json
import logging
import time

from openai import OpenAI

from config import (
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_RATE_LIMIT_DELAY,
    LLM_MAX_RETRIES,
    LLM_RETRY_BASE_DELAY,
    PROMPT_TRANSCRIPT_ANALYSIS,
    PROMPT_COMMENT_ANALYSIS,
    PROMPT_OVERALL_REPORT,
)

logger = logging.getLogger(__name__)


def init_llm_client(api_key):
    """创建 OpenAI 兼容客户端（qwen3.5-plus 含思考模式，需要较长超时）"""
    return OpenAI(api_key=api_key, base_url=LLM_BASE_URL, timeout=600.0)


def preflight_check_llm(client):
    """
    启动时预检 LLM 连通性和 API Key 有效性。

    发送一个极简请求（max_tokens=1），快速验证:
    - API Key 是否正确
    - Base URL 是否可达
    - 模型名是否有效

    返回: (ok: bool, error_msg: str | None)
    """
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        _ = response.choices[0].message.content
        return True, None
    except Exception as e:
        return False, str(e)


def _call_llm(client, prompt, max_tokens=None):
    """
    调用 LLM，带指数退避重试。

    返回: str (生成文本) 或 None (失败)
    """
    if max_tokens is None:
        max_tokens = LLM_MAX_TOKENS

    last_error = None
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=max_tokens,
                temperature=LLM_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.choices[0].message.content
            time.sleep(LLM_RATE_LIMIT_DELAY)
            return result
        except Exception as e:
            last_error = e
            if attempt < LLM_MAX_RETRIES:
                delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"LLM 调用失败, {delay}s 后重试 "
                    f"({attempt + 1}/{LLM_MAX_RETRIES}): {e}"
                )
                time.sleep(delay)

    logger.error(f"LLM 调用最终失败: {last_error}")
    return None


def analyze_transcript_with_llm(client, video, transcript_text):
    """
    使用 LLM 深度分析单个视频的字幕内容。

    参数:
        client: OpenAI 客户端
        video: 视频详情 dict
        transcript_text: 完整字幕文本

    返回: dict with status, analysis_text, error
    """
    sponsor_desc = video.get("sponsor_status", {}).get("sponsor_type", "unknown")

    # 截断过长的字幕（Qwen-plus 支持 128K，留出 prompt + 输出空间）
    max_chars = 300_000
    truncated = False
    if len(transcript_text) > max_chars:
        transcript_text = transcript_text[:max_chars]
        truncated = True

    prompt = PROMPT_TRANSCRIPT_ANALYSIS.format(
        title=video["title"],
        channel=video["channel"],
        view_count=video["view_count"],
        sponsor_status=sponsor_desc,
        transcript=transcript_text,
    )
    if truncated:
        prompt += "\n\n[注意：字幕文本过长，已截断至前部分]"

    logger.info(
        f"  调用 LLM ({LLM_MODEL}) 分析字幕 "
        f"({len(transcript_text):,} chars)..."
    )

    result = _call_llm(client, prompt)
    if result:
        return {"status": "success", "analysis_text": result, "error": None}
    return {
        "status": "failed",
        "analysis_text": "",
        "error": "LLM 调用失败",
    }


def analyze_comments_with_llm(client, video, comments_df):
    """
    使用 LLM 分析单个视频的评论。

    参数:
        client: OpenAI 客户端
        video: 视频详情 dict
        comments_df: 该视频的已分析评论 DataFrame

    返回: dict with status, analysis_text, comment_count, error
    """
    if comments_df is None or len(comments_df) == 0:
        return {
            "status": "no_comments",
            "analysis_text": "",
            "comment_count": 0,
            "error": None,
        }

    # 取 Top 100 高赞评论
    top_n = min(100, len(comments_df))
    top_comments = comments_df.nlargest(top_n, "like_count")

    parts = []
    for _, row in top_comments.iterrows():
        likes = row.get("like_count", 0)
        author = row.get("author", "Anonymous")
        text = row.get("text_clean", "")[:500]
        parts.append(f"[{likes} likes] {author}: {text}")

    comments_text = "\n\n".join(parts)

    # 截断
    if len(comments_text) > 80_000:
        comments_text = comments_text[:80_000] + "\n\n[...评论已截断...]"

    prompt = PROMPT_COMMENT_ANALYSIS.format(
        title=video["title"],
        channel=video["channel"],
        comment_count=len(comments_df),
        comments=comments_text,
    )

    logger.info(
        f"  调用 LLM ({LLM_MODEL}) 分析评论 "
        f"({len(comments_df)} 条, {len(comments_text):,} chars)..."
    )

    result = _call_llm(client, prompt)
    if result:
        return {
            "status": "success",
            "analysis_text": result,
            "comment_count": len(comments_df),
            "error": None,
        }
    return {
        "status": "failed",
        "analysis_text": "",
        "comment_count": len(comments_df),
        "error": "LLM 调用失败",
    }


def generate_overall_with_llm(client, llm_results, videos):
    """
    使用 LLM 生成跨视频综合分析报告。

    参数:
        client: OpenAI 客户端
        llm_results: {video_id: {"transcript": {...}, "comments": {...}}}
        videos: 视频列表

    返回: dict with status, analysis_text, error
    """
    video_parts = []
    comment_parts = []

    for video in videos:
        vid = video["video_id"]
        result = llm_results.get(vid, {})

        # 字幕分析摘要（截取前 2000 字符）
        ta = result.get("transcript", {})
        ta_text = ta.get("analysis_text", "分析不可用")
        ta_excerpt = ta_text[:2000] + ("..." if len(ta_text) > 2000 else "")

        video_parts.append(
            f"### {video['channel']} - {video['title']}\n"
            f"观看量: {video['view_count']:,} | "
            f"赞助: {video.get('sponsor_status', {}).get('sponsor_type', 'unknown')}\n\n"
            f"{ta_excerpt}\n"
        )

        # 评论分析摘要
        ca = result.get("comments", {})
        ca_text = ca.get("analysis_text", "")
        if ca_text:
            ca_excerpt = ca_text[:1000] + ("..." if len(ca_text) > 1000 else "")
            comment_parts.append(
                f"### {video['channel']} - {video['title']}\n{ca_excerpt}\n"
            )

    video_summaries = "\n---\n".join(video_parts)
    comment_summaries = "\n---\n".join(comment_parts) or "无评论分析数据"

    # 截断总长度
    max_total = 200_000
    total_len = len(video_summaries) + len(comment_summaries)
    if total_len > max_total:
        ratio = max_total / total_len
        video_summaries = video_summaries[:int(len(video_summaries) * ratio)]
        comment_summaries = comment_summaries[:int(len(comment_summaries) * ratio)]

    prompt = PROMPT_OVERALL_REPORT.format(
        video_count=len(videos),
        video_summaries=video_summaries,
        comment_summaries=comment_summaries,
    )

    logger.info(
        f"调用 LLM ({LLM_MODEL}) 生成综合报告 "
        f"(prompt: {len(prompt):,} chars)..."
    )

    result = _call_llm(client, prompt, max_tokens=8192)
    if result:
        return {"status": "success", "analysis_text": result, "error": None}
    return {
        "status": "failed",
        "analysis_text": "",
        "error": "LLM 调用失败",
    }
