"""
报告生成模块

生成单视频详情报告和总体综合分析报告。
输出中文 Markdown，LLM 分析结果作为核心内容。
"""

import re
from collections import Counter


def generate_per_video_report(video, content_analysis, video_comments_df,
                              llm_result):
    """
    生成单个视频的详情报告（中文 Markdown，含英文原文括注）。

    参数:
        video: 视频详情 dict
        content_analysis: 关键词分析结果 dict（补充数据）
        video_comments_df: 该视频的评论 DataFrame（已分析）
        llm_result: {"transcript": {...}, "comments": {...}}

    返回: str (Markdown 文本)
    """
    vid = video["video_id"]
    ca = content_analysis or {}
    sp = video.get("sponsor_status", {})
    ch = video.get("channel_profile", {})
    ta = llm_result.get("transcript", {})
    ca_llm = llm_result.get("comments", {})

    r = []
    r.append(f"# {video['title']}")
    r.append("")

    # --- 视频元数据 ---
    r.append("## 视频信息\n")
    r.append("| 项目 | 数据 |")
    r.append("|---|---|")
    r.append(f"| **频道** | {video['channel']} |")

    subs = ch.get('subscriber_count', 0)
    subs_str = _format_subs(subs)
    r.append(f"| **频道粉丝** | {subs_str} |")
    r.append(f"| **频道国家** | {ch.get('channel_country', 'Unknown')} |")
    r.append(f"| **发布日期** | {video['published_at'][:10]} |")
    r.append(f"| **时长** | {video.get('duration_seconds', 0) // 60} 分钟 |")
    r.append(f"| **观看量** | {video['view_count']:,} |")
    r.append(f"| **点赞数** | {video['like_count']:,} |")
    r.append(f"| **评论数** | {video['comment_count']} |")
    r.append(
        f"| **YouTube 链接** | https://www.youtube.com/watch?v={vid} |"
    )
    r.append("")

    # --- 赞助/样机状态 ---
    sp_labels = {
        "sponsored": "官方赞助",
        "review_sample": "样机评测",
        "affiliate_only": "含联盟链接",
        "self_purchased": "自购",
        "unknown": "未声明",
    }
    sp_label = sp_labels.get(sp.get("sponsor_type", "unknown"), "未声明")
    r.append(f"### 赞助状态: {sp_label}\n")
    r.append(
        f"- **判定**: {'是' if sp.get('is_sponsored') else '否'} "
        f"(置信度: {sp.get('confidence', 'N/A')})"
    )
    if sp.get("raw_matches"):
        r.append("- **检测信号**:")
        for match in sp.get("raw_matches", [])[:3]:
            r.append(f'  - [{match["category"]}] "{match["context"]}"')
    r.append("")

    # --- LLM 深度内容分析 ---
    r.append("## 深度内容分析（AI 分析结果）\n")
    if ta.get("status") == "success" and ta.get("analysis_text"):
        r.append(ta["analysis_text"])
    elif ta.get("status") == "skipped":
        r.append("*字幕不可用，无法进行内容分析*\n")
    else:
        r.append(f"*内容分析失败: {ta.get('error', '未知错误')}*\n")
    r.append("")

    # --- LLM 评论深度分析 ---
    r.append("## 评论深度分析（AI 分析结果）\n")
    if ca_llm.get("status") == "success" and ca_llm.get("analysis_text"):
        r.append(ca_llm["analysis_text"])
    elif ca_llm.get("status") == "no_comments":
        r.append("*该视频无有效评论*\n")
    else:
        r.append(f"*评论分析失败: {ca_llm.get('error', '未知错误')}*\n")
    r.append("")

    # --- 补充：关键信息时间戳索引（自动检测） ---
    r.append("## 补充：关键信息时间戳索引（自动检测）\n")
    key_moments = ca.get("key_moments", [])
    if key_moments:
        r.append("| 时间 | 信息类型 | 上下文 | 跳转链接 |")
        r.append("|---|---|---|---|")
        for m in key_moments:
            ts = m["timestamp"]
            ts_sec = int(m.get("timestamp_seconds", 0))
            context = m["context"][:80].replace("|", "\\|").replace("\n", " ")
            link = f"https://www.youtube.com/watch?v={vid}&t={ts_sec}s"
            r.append(
                f"| {ts} | {m['label']} | {context} | [跳转]({link}) |"
            )
        r.append("")
    else:
        r.append("*未检测到关键信息时间戳*\n")

    # --- 补充：高赞评论原文 ---
    r.append("## 补充：高赞评论 Top 15\n")
    if video_comments_df is not None and len(video_comments_df) > 0:
        top_comments = video_comments_df.nlargest(15, "like_count")
        icons = {
            "positive": "+", "negative": "-",
            "mixed": "~", "neutral": " ",
        }
        for _, row in top_comments.iterrows():
            icon = icons.get(row["sentiment"], " ")
            r.append(
                f"**[{icon}] {row['like_count']} likes** | "
                f"**{row['author']}**"
            )
            r.append(f"> {row['text_clean'][:500]}")
            r.append("")
    else:
        r.append("*该视频无有效评论*\n")

    return "\n".join(r)


def generate_overall_report(top_videos, filter_stats, df_meaningful,
                            transcript_stats, video_content_analysis,
                            channel_profiles, llm_results, overall_llm):
    """
    生成总体综合分析报告（中文 Markdown）。

    返回: str (Markdown 文本)
    """
    import pandas as pd

    report = []
    report.append("# Snapmaker U1 YouTube 评测视频综合分析报告\n")
    report.append(
        f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
    )
    report.append(
        f"**数据范围**: 2025-11-15 至今（量产机开始交付后）\n"
    )

    # 1. 数据概况
    report.append("## 1. 数据概况\n")
    report.append("| 指标 | 数值 |")
    report.append("|---|---|")
    report.append(
        f"| 搜索候选视频 | {filter_stats['total_searched']} |"
    )
    report.append(
        f"| 相关性过滤后 | {filter_stats['after_relevance_filter']} |"
    )
    report.append(
        f"| 质量过滤后 | {filter_stats['after_quality_filter']} |"
    )
    report.append(
        f"| 播放量 >= {filter_stats['min_view_count']:,} | "
        f"{filter_stats['after_view_filter']} |"
    )
    report.append(
        f"| 最终分析视频数 | {filter_stats['selected_count']} |"
    )
    report.append(
        f"| 赞助/样机视频 | {filter_stats['sponsored_count']} |"
    )
    report.append(
        f"| 总观看量 | {sum(v['view_count'] for v in top_videos):,} |"
    )
    report.append(
        f"| 获取评论数 | {filter_stats.get('total_comments', 0):,} |"
    )
    report.append(
        f"| 有效评论数 | {len(df_meaningful):,} |"
    )
    report.append(
        f"| 成功转录视频 | {transcript_stats['success']} |"
    )
    report.append("")

    # 2. AI 综合分析报告（核心内容）
    report.append("## 2. AI 综合分析报告\n")
    if overall_llm.get("status") == "success" and overall_llm.get(
            "analysis_text"):
        report.append(overall_llm["analysis_text"])
    else:
        report.append(
            f"*综合分析生成失败: {overall_llm.get('error', '未知错误')}*"
        )
    report.append("")

    # 3. 视频来源频道画像
    report.append("## 3. 视频来源频道画像\n")
    report.append("| 频道 | 粉丝数 | 国家 | 观看量 | 赞助 |")
    report.append("|---|---|---|---|---|")
    seen_channels = set()
    for v in top_videos:
        ch = v.get("channel_profile", {})
        ch_name = v["channel"]
        if ch_name in seen_channels:
            continue
        seen_channels.add(ch_name)
        subs_str = _format_subs(ch.get("subscriber_count", 0))
        country = ch.get("channel_country", "?")
        sp = "是" if v.get("sponsor_status", {}).get("is_sponsored") else ""
        report.append(
            f"| {ch_name[:25]} | {subs_str} | {country} "
            f"| {v['view_count']:,} | {sp} |"
        )
    report.append("")

    # 4. 赞助/样机状态分布
    report.append("## 4. 赞助/样机状态分布\n")
    sponsor_types = Counter(
        v.get("sponsor_status", {}).get("sponsor_type", "unknown")
        for v in top_videos
    )
    type_labels = {
        "sponsored": "官方赞助",
        "review_sample": "样机评测",
        "affiliate_only": "含联盟链接",
        "self_purchased": "自购",
        "unknown": "未声明",
    }
    for st, count in sponsor_types.most_common():
        label = type_labels.get(st, st)
        report.append(f"- {label}: {count} 个视频")
    report.append("")

    # 5. 评论情感分布（关键词分析补充）
    report.append("## 5. 评论情感分布（关键词分析）\n")
    if len(df_meaningful) > 0:
        for sent, count in df_meaningful["sentiment"].value_counts().items():
            pct = count / len(df_meaningful) * 100
            bar = "=" * int(pct / 2)
            report.append(f"- **{sent}**: {count} ({pct:.1f}%) {bar}")
    report.append("")

    # 6. 用户关注主题 Top 15（关键词分析补充）
    topic_counter = Counter()
    if len(df_meaningful) > 0:
        for topics in df_meaningful["topics"]:
            if isinstance(topics, list):
                topic_counter.update(topics)
    report.append("## 6. 用户关注主题 Top 15（关键词分析）\n")
    report.append("| 排名 | 主题 | 提及次数 | 占比 |")
    report.append("|---|---|---|---|")
    for rank, (topic, count) in enumerate(
            topic_counter.most_common(15), 1):
        pct = count / max(len(df_meaningful), 1) * 100
        report.append(f"| {rank} | {topic} | {count} | {pct:.1f}% |")
    report.append("")

    # 7. 视频索引
    report.append("## 7. 视频索引\n")
    report.append(
        "| # | 频道 | 粉丝 | 标题 | 观看量 | 赞助 | 转录 | LLM |"
    )
    report.append("|---|---|---|---|---|---|---|---|")
    for i, v in enumerate(top_videos, 1):
        ca = video_content_analysis.get(v["video_id"], {})
        tr_status = (
            "OK" if ca.get("transcript_status") == "success" else "N/A"
        )
        llm_status = (
            "OK" if llm_results.get(v["video_id"], {}).get(
                "transcript", {}).get("status") == "success"
            else "N/A"
        )
        subs_str = _format_subs(
            v.get("channel_profile", {}).get("subscriber_count", 0)
        )
        sp_icon = (
            "是" if v.get("sponsor_status", {}).get("is_sponsored") else ""
        )
        report.append(
            f"| {i} | {v['channel'][:18]} | {subs_str} | "
            f"{v['title'][:35]} | {v['view_count']:,} | {sp_icon} | "
            f"{tr_status} | {llm_status} |"
        )
    report.append("")

    return "\n".join(report)


def _format_subs(subs):
    """格式化粉丝数"""
    if subs >= 1_000_000:
        return f"{subs / 1_000_000:.1f}M"
    elif subs >= 1000:
        return f"{subs / 1000:.1f}K"
    else:
        return str(subs)
