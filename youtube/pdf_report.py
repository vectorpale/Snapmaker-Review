"""
PDF 报告生成模块

使用 Jinja2 + Matplotlib + WeasyPrint 生成专业 PDF 产品分析报告。
"""

import base64
import io
import logging
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

logger = logging.getLogger(__name__)

# --- 配置 ---
TEMPLATES_DIR = Path(__file__).parent / "templates"
CHART_DPI = 150
COLORS = {
    "positive": "#27ae60",
    "negative": "#e74c3c",
    "neutral": "#95a5a6",
    "mixed": "#f39c12",
    "primary": "#2980b9",
    "secondary": "#1a5276",
}

# 话题显示名映射
TOPIC_DISPLAY = {
    "print_quality": "打印质量",
    "tool_change": "换头/SnapSwap",
    "speed": "打印速度",
    "noise": "噪音",
    "waste_filament": "废料/耗材浪费",
    "enclosure": "外罩/箱体",
    "calibration": "校准",
    "firmware_software": "固件/软件",
    "camera": "摄像头",
    "wifi_connectivity": "WiFi/网络",
    "materials": "耗材兼容",
    "nozzle": "喷嘴/热端",
    "build_volume": "打印尺寸",
    "price_value": "价格/性价比",
    "vs_bambu": "vs Bambu Lab",
    "vs_prusa": "vs Prusa",
    "vs_creality": "vs Creality",
    "setup_unboxing": "开箱/安装",
    "reliability": "可靠性",
    "support_service": "售后服务",
    "shipping_kickstarter": "物流/众筹",
    "multi_color": "多色打印",
    "open_source": "开源",
    "quality_control": "品控",
}


# ============================================================
# Font setup
# ============================================================

def _setup_chinese_font():
    """配置 Matplotlib 中文字体。"""
    candidates = [
        "WenQuanYi Zen Hei",
        "Noto Sans CJK SC",
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
    ]
    for name in candidates:
        try:
            path = fm.findfont(name, fallback_to_default=False)
            if path and "LastResort" not in path:
                plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
                logger.info(f"Matplotlib 中文字体: {name}")
                return
        except Exception:
            continue

    # Fallback: use whatever is available
    plt.rcParams["axes.unicode_minus"] = False
    logger.warning("未找到中文字体, 图表中文可能显示为方块")


# ============================================================
# Chart helpers
# ============================================================

def _fig_to_base64(fig):
    """将 Matplotlib figure 转为 base64 PNG 数据 URI。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=CHART_DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _chart_sentiment_pie(df):
    """情感分布饼图。"""
    if df is None or len(df) == 0:
        return None
    counts = df["sentiment"].value_counts()
    labels_map = {
        "positive": "正面",
        "negative": "负面",
        "neutral": "中性",
        "mixed": "混合",
    }
    labels = [labels_map.get(s, s) for s in counts.index]
    colors = [COLORS.get(s, "#999") for s in counts.index]

    fig, ax = plt.subplots(figsize=(5, 4))
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90, textprops={"fontsize": 10},
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("评论情感分布", fontsize=13, fontweight="bold")
    return _fig_to_base64(fig)


def _chart_sentiment_by_video(df, videos):
    """各视频情感堆叠柱状图。"""
    if df is None or len(df) == 0 or not videos:
        return None

    vid_to_channel = {v["video_id"]: v["channel"][:15] for v in videos}
    # Only include videos that have comments
    df_filtered = df[df["video_id"].isin(vid_to_channel)]
    if len(df_filtered) == 0:
        return None

    cross = pd.crosstab(df_filtered["video_id"], df_filtered["sentiment"])
    # Normalize to percentages
    cross_pct = cross.div(cross.sum(axis=1), axis=0) * 100
    # Sort by video order
    vid_order = [v["video_id"] for v in videos if v["video_id"] in cross_pct.index]
    cross_pct = cross_pct.reindex(vid_order)
    channel_names = [vid_to_channel.get(v, v[:10]) for v in cross_pct.index]

    fig, ax = plt.subplots(figsize=(8, max(4, len(channel_names) * 0.35)))
    bottom = pd.Series(0.0, index=cross_pct.index)
    for sentiment in ["positive", "neutral", "mixed", "negative"]:
        if sentiment not in cross_pct.columns:
            continue
        labels_map = {"positive": "正面", "negative": "负面",
                      "neutral": "中性", "mixed": "混合"}
        vals = cross_pct[sentiment]
        ax.barh(channel_names, vals, left=bottom, height=0.6,
                color=COLORS.get(sentiment, "#999"),
                label=labels_map.get(sentiment, sentiment))
        bottom += vals

    ax.set_xlabel("评论占比 (%)")
    ax.set_title("各视频评论情感分布", fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8)
    ax.invert_yaxis()
    fig.tight_layout()
    return _fig_to_base64(fig)


def _chart_top_topics(df, top_n=15):
    """热门话题柱状图。"""
    if df is None or len(df) == 0:
        return None

    topic_counter = Counter()
    for topics in df["topics"]:
        if isinstance(topics, list):
            topic_counter.update(topics)
        elif isinstance(topics, str) and topics:
            # Handle string representation of list
            for t in topics.strip("[]").replace("'", "").split(","):
                t = t.strip()
                if t:
                    topic_counter[t] += 1

    if not topic_counter:
        return None

    top = topic_counter.most_common(top_n)
    labels = [TOPIC_DISPLAY.get(t, t) for t, _ in top]
    values = [c for _, c in top]

    fig, ax = plt.subplots(figsize=(7, max(4, len(labels) * 0.35)))
    bars = ax.barh(labels, values, color=COLORS["primary"], height=0.6)
    ax.set_xlabel("提及次数")
    ax.set_title("用户关注话题 Top 15", fontsize=13, fontweight="bold")
    ax.invert_yaxis()

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8, color="#555")

    fig.tight_layout()
    return _fig_to_base64(fig)


def _chart_reviewer_stance(llm_results):
    """
    评测者态度分布饼图。
    从各视频 LLM 分析的核心结论中推断推荐/中立/不推荐。
    """
    stance_counts = {"推荐": 0, "中性/有保留": 0, "不推荐": 0}

    positive_kw = ["推荐", "值得", "优秀", "出色", "recommend", "impressed",
                   "worth", "excellent", "great"]
    negative_kw = ["不推荐", "失望", "不值", "问题多", "disappoint",
                   "not recommend", "avoid"]

    for vid, result in llm_results.items():
        text = result.get("transcript", {}).get("analysis_text", "")
        # Take first 500 chars (usually contains the core conclusion)
        snippet = text[:500].lower()
        has_pos = any(kw in snippet for kw in positive_kw)
        has_neg = any(kw in snippet for kw in negative_kw)

        if has_pos and not has_neg:
            stance_counts["推荐"] += 1
        elif has_neg and not has_pos:
            stance_counts["不推荐"] += 1
        else:
            stance_counts["中性/有保留"] += 1

    if sum(stance_counts.values()) == 0:
        return None

    labels = list(stance_counts.keys())
    values = list(stance_counts.values())
    colors = [COLORS["positive"], COLORS["mixed"], COLORS["negative"]]

    fig, ax = plt.subplots(figsize=(5, 4))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct="%1.0f%%", startangle=90, textprops={"fontsize": 10},
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("评测者态度分布", fontsize=13, fontweight="bold")
    return _fig_to_base64(fig)


# ============================================================
# LLM text section extraction
# ============================================================

def _extract_section(text, header_patterns):
    """
    从 LLM Markdown 分析文本中按 ## 标题提取某个 section。
    header_patterns: list of regex patterns to match section header.
    Returns section body text, or empty string.
    """
    if not text:
        return ""

    for pattern in header_patterns:
        # Match "## N. <pattern>" or "## <pattern>"
        regex = (
            r"##\s*(?:\d+[\.\s]*)?" + pattern +
            r"[^\n]*\n(.*?)(?=\n##\s|\Z)"
        )
        match = re.search(regex, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""


def _extract_core_conclusion(llm_transcript_text):
    """从单视频 LLM 分析中提取核心结论（前 300 字）。"""
    if not llm_transcript_text:
        return "分析不可用"

    section = _extract_section(llm_transcript_text, [
        r"核心结论", r"Core Conclusion", r"总体评价", r"Overall",
    ])
    if section:
        # Truncate to ~300 chars at sentence boundary
        if len(section) > 300:
            # Try to cut at Chinese period
            cut = section[:300].rfind("。")
            if cut > 100:
                return section[:cut + 1]
            return section[:300] + "..."
        return section

    # Fallback: first 300 chars of the full text
    text = llm_transcript_text.strip()
    if len(text) > 300:
        return text[:300] + "..."
    return text


# ============================================================
# Comment example extraction
# ============================================================

def _get_example_comments(df, videos, sentiment, n=8):
    """获取指定情感类别的 Top N 高赞评论。"""
    if df is None or len(df) == 0:
        return []

    vid_to_channel = {v["video_id"]: v["channel"] for v in videos}
    subset = df[df["sentiment"] == sentiment].nlargest(n, "like_count")

    results = []
    for _, row in subset.iterrows():
        text = str(row.get("text_clean", ""))[:300]
        results.append({
            "author": row.get("author", "Anonymous"),
            "like_count": int(row.get("like_count", 0)),
            "text": text,
            "video_channel": vid_to_channel.get(row.get("video_id", ""), ""),
        })
    return results


def _get_question_comments(df, videos, n=8):
    """获取包含疑问的高赞评论。"""
    if df is None or len(df) == 0:
        return []

    vid_to_channel = {v["video_id"]: v["channel"] for v in videos}
    mask = df["text_clean"].str.contains(r"\?|？", regex=True, na=False)
    subset = df[mask].nlargest(n, "like_count")

    results = []
    for _, row in subset.iterrows():
        text = str(row.get("text_clean", ""))[:300]
        results.append({
            "author": row.get("author", "Anonymous"),
            "like_count": int(row.get("like_count", 0)),
            "text": text,
            "video_channel": vid_to_channel.get(row.get("video_id", ""), ""),
        })
    return results


# ============================================================
# Topic-sentiment cross table
# ============================================================

def _build_topic_table(df, top_n=15):
    """构建话题-情感交叉表数据。"""
    if df is None or len(df) == 0:
        return []

    rows = []
    topic_counter = Counter()

    for _, row in df.iterrows():
        topics = row.get("topics", [])
        if isinstance(topics, str):
            topics = [t.strip().strip("'\"")
                      for t in topics.strip("[]").split(",") if t.strip()]
        if isinstance(topics, list):
            sentiment = row.get("sentiment", "neutral")
            for t in topics:
                topic_counter[t] += 1

    # Count sentiment per topic
    topic_sentiment = {}
    for _, row in df.iterrows():
        topics = row.get("topics", [])
        if isinstance(topics, str):
            topics = [t.strip().strip("'\"")
                      for t in topics.strip("[]").split(",") if t.strip()]
        if isinstance(topics, list):
            s = row.get("sentiment", "neutral")
            for t in topics:
                if t not in topic_sentiment:
                    topic_sentiment[t] = Counter()
                topic_sentiment[t][s] += 1

    for topic, count in topic_counter.most_common(top_n):
        sc = topic_sentiment.get(topic, Counter())
        rows.append({
            "topic": TOPIC_DISPLAY.get(topic, topic),
            "count": count,
            "positive": sc.get("positive", 0),
            "negative": sc.get("negative", 0),
            "neutral": sc.get("neutral", 0) + sc.get("mixed", 0),
        })

    return rows


# ============================================================
# Helpers
# ============================================================

def _format_number(value):
    """Jinja2 filter: 格式化数字（加千分位）。"""
    if isinstance(value, (int, float)):
        return f"{int(value):,}"
    return str(value)


def _format_subs(subs):
    """Jinja2 filter: 格式化粉丝数。"""
    if not isinstance(subs, (int, float)):
        return str(subs)
    if subs >= 1_000_000:
        return f"{subs / 1_000_000:.1f}M"
    elif subs >= 1000:
        return f"{subs / 1000:.1f}K"
    return str(int(subs))


# ============================================================
# Main entry point
# ============================================================

def generate_pdf_report(
    top_videos,
    filter_stats,
    df_comments,
    llm_results,
    overall_llm,
    output_path,
):
    """
    生成 PDF 产品分析报告。

    参数:
        top_videos: 视频列表 (list[dict])
        filter_stats: 管道统计 (dict)
        df_comments: 评论 DataFrame (含 sentiment, topics)
        llm_results: {video_id: {transcript: {}, comments: {}}}
        overall_llm: 整体 LLM 分析 (dict with status, analysis_text)
        output_path: PDF 输出路径

    返回: Path to generated PDF
    """
    _setup_chinese_font()

    output_path = Path(output_path)

    # --- 1. Generate charts ---
    logger.info("  生成图表...")
    charts = {}
    charts["sentiment_pie"] = _chart_sentiment_pie(df_comments)
    charts["sentiment_by_video"] = _chart_sentiment_by_video(
        df_comments, top_videos)
    charts["topic_frequency"] = _chart_top_topics(df_comments)
    charts["reviewer_stance"] = _chart_reviewer_stance(llm_results)
    # strengths/issues bars are text-based from LLM, skip chart for now

    # --- 2. Extract LLM sections ---
    overall_text = overall_llm.get("analysis_text", "") if overall_llm else ""

    executive_summary = _extract_section(overall_text, [
        r"执行摘要", r"Executive Summary", r"摘要",
    ])
    section_reputation = _extract_section(overall_text, [
        r"整体口碑", r"Overall Reputation", r"口碑评估", r"产品口碑",
    ])
    section_strengths = _extract_section(overall_text, [
        r"优点", r"亮点", r"Strengths", r"优势",
    ])
    section_issues = _extract_section(overall_text, [
        r"缺点", r"问题", r"Issues", r"不足",
    ])
    section_improvements = _extract_section(overall_text, [
        r"改进", r"Improvement", r"优化方向",
    ])
    section_competitive = _extract_section(overall_text, [
        r"竞品", r"Competitive", r"竞争",
    ])

    # --- 3. Per-video summaries ---
    video_summaries = []
    for v in top_videos:
        vid = v["video_id"]
        lr = llm_results.get(vid, {})
        ta_text = lr.get("transcript", {}).get("analysis_text", "")
        conclusion = _extract_core_conclusion(ta_text)
        sp = v.get("sponsor_status", {})
        ch = v.get("channel_profile", {})
        video_summaries.append({
            "channel": v["channel"],
            "title": v["title"],
            "view_count": v["view_count"],
            "like_count": v.get("like_count", 0),
            "subscriber_count": ch.get("subscriber_count", 0),
            "sponsor_type": sp.get("sponsor_type", "unknown"),
            "conclusion": conclusion,
        })

    # --- 4. Sentiment data ---
    sentiment_counts = {}
    sentiment_table = []
    total_comments = len(df_comments) if df_comments is not None else 0

    if df_comments is not None and len(df_comments) > 0:
        sentiment_counts = df_comments["sentiment"].value_counts().to_dict()
        for sentiment, css_class in [
            ("positive", "positive"),
            ("neutral", "neutral"),
            ("negative", "negative"),
            ("mixed", "mixed"),
        ]:
            count = sentiment_counts.get(sentiment, 0)
            pct = round(count / total_comments * 100, 1) if total_comments else 0
            label_map = {"positive": "正面", "neutral": "中性",
                         "negative": "负面", "mixed": "混合"}
            sentiment_table.append(
                (label_map.get(sentiment, sentiment), count, pct, css_class)
            )

    # --- 5. Comment examples ---
    comment_examples = {
        "positive": _get_example_comments(df_comments, top_videos, "positive"),
        "neutral": _get_example_comments(df_comments, top_videos, "neutral"),
        "negative": _get_example_comments(df_comments, top_videos, "negative"),
        "questions": _get_question_comments(df_comments, top_videos),
    }

    # --- 6. Topic table ---
    topic_table = _build_topic_table(df_comments)

    # --- 7. Render HTML template ---
    logger.info("  渲染 HTML 模板...")
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["format_number"] = _format_number
    env.filters["format_subs"] = _format_subs
    template = env.get_template("report.html")

    html_content = template.render(
        generation_date=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        filter_stats=filter_stats or {},
        total_comments=total_comments,
        total_views=sum(v.get("view_count", 0) for v in top_videos),
        transcript_success=sum(
            1 for v in top_videos
            if llm_results.get(v["video_id"], {})
               .get("transcript", {}).get("status") == "success"
        ),
        charts=charts,
        executive_summary=executive_summary,
        overall_text_fallback=overall_text[:2000] if overall_text else "",
        section_reputation=section_reputation,
        section_strengths=section_strengths,
        section_issues=section_issues,
        section_improvements=section_improvements,
        section_competitive=section_competitive,
        video_summaries=video_summaries,
        sentiment_counts=sentiment_counts,
        sentiment_table=sentiment_table,
        comment_examples=comment_examples,
        topic_table=topic_table,
        top_videos=top_videos,
    )

    # --- 8. Convert to PDF ---
    logger.info("  生成 PDF...")
    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(
        str(output_path)
    )

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"  PDF 报告已生成: {output_path} ({size_kb:.0f} KB)")
    return output_path
