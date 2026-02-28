"""
报告生成模块

生成 Tier A 单视频详情报告和总体分析报告。
"""

import re
from collections import Counter

from config import KEY_INFO_PATTERNS


def generate_per_video_report(video, content_analysis, video_comments_df):
    """
    生成单个 Tier A 视频的详情报告（Markdown）。

    参数:
        video: 视频详情 dict
        content_analysis: 内容分析结果 dict
        video_comments_df: 该视频的评论 DataFrame（已分析）

    返回: str (Markdown 文本)
    """
    vid = video["video_id"]
    ca = content_analysis or {}
    sp = video.get("sponsor_status", {})
    ch = video.get("channel_profile", {})

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
    r.append(f"| **频道总视频** | {ch.get('total_video_count', 'N/A')} |")
    r.append(f"| **发布日期** | {video['published_at'][:10]} |")
    r.append(f"| **时长** | {video.get('duration_seconds', 0) // 60} 分钟 |")
    r.append(f"| **观看量** | {video['view_count']:,} |")
    r.append(f"| **点赞数** | {video['like_count']:,} |")
    r.append(f"| **评论数** | {video['comment_count']} |")
    r.append(f"| **YouTube 链接** | https://www.youtube.com/watch?v={vid} |")
    r.append("")

    # --- 赞助/样机状态 ---
    sp_labels = {
        "sponsored": "🔴 官方赞助",
        "review_sample": "🟠 样机评测",
        "affiliate_only": "🟡 含联盟链接",
        "self_purchased": "🟢 自购",
        "unknown": "⚪ 未声明",
    }
    sp_icon = sp_labels.get(sp.get("sponsor_type", "unknown"), "⚪ 未声明")
    r.append(f"### 赞助状态: {sp_icon}\n")
    r.append(f"- **判定**: {'是' if sp.get('is_sponsored') else '否'} "
             f"(置信度: {sp.get('confidence', 'N/A')})")
    if sp.get("raw_matches"):
        r.append("- **检测信号**:")
        for match in sp.get("raw_matches", [])[:3]:
            r.append(f'  - [{match["category"]}] "{match["context"]}"')
    r.append("")

    # --- 频道简介 ---
    ch_desc = ch.get('channel_description', '')
    if ch_desc:
        r.append("### 频道简介\n")
        r.append(f"> {ch_desc[:300]}{'...' if len(ch_desc) > 300 else ''}")
        r.append("")

    # --- 视频描述 ---
    r.append("## 视频描述\n")
    desc = video.get("description", "")[:1000]
    r.append(f"```\n{desc}\n```\n")

    # --- 视频内容分段摘要 ---
    r.append("## 视频内容分段摘要\n")
    if ca.get("transcript_status") == "success":
        r.append(f"*字幕来源: {ca.get('transcript_source', 'N/A')} | "
                 f"总字数: {ca.get('transcript_word_count', 0):,} | "
                 f"分段数: {ca.get('segment_count', 0)}*\n")
        for seg in ca.get("segments_overview", []):
            topics_str = ", ".join(seg.get("detected_topics", [])) or "（一般内容）"
            r.append(f"### ⏱️ {seg['time_range']}")
            r.append(f"**检测主题**: {topics_str}")
            r.append(f"**内容预览**: {seg['preview']}...")
            r.append("")
    else:
        r.append(f"*⚠️ 转录不可用 ({ca.get('transcript_status', 'N/A')})*\n")

    # --- 关键信息时间戳索引 ---
    r.append("## 🔑 关键信息时间戳索引\n")
    key_moments = ca.get("key_moments", [])
    if key_moments:
        r.append("| 时间 | 信息类型 | 上下文 | 跳转链接 |")
        r.append("|---|---|---|---|")
        for m in key_moments:
            ts = m["timestamp"]
            ts_sec = int(m.get("timestamp_seconds", 0))
            context = m["context"][:80].replace("|", "\\|").replace("\n", " ")
            link = f"https://www.youtube.com/watch?v={vid}&t={ts_sec}s"
            r.append(f"| {ts} | {m['label']} | {context} | [跳转]({link}) |")
        r.append("")
    else:
        r.append("*未检测到关键信息时间戳*\n")

    # --- 评论分析 ---
    r.append("## 评论分析\n")
    if video_comments_df is not None and len(video_comments_df) > 0:
        r.append(f"获取评论: {len(video_comments_df)} 条有效评论\n")

        r.append("### 情感分布\n")
        for sent, count in video_comments_df["sentiment"].value_counts().items():
            pct = count / len(video_comments_df) * 100
            r.append(f"- {sent}: {count} ({pct:.1f}%)")
        r.append("")

        topic_counter = Counter()
        for topics in video_comments_df["topics"]:
            if isinstance(topics, list):
                topic_counter.update(topics)
        if topic_counter:
            r.append("### 评论热门主题\n")
            for topic, count in topic_counter.most_common(10):
                r.append(f"- {topic}: {count}")
            r.append("")

        r.append("### 高赞评论 Top 15\n")
        top_comments = video_comments_df.nlargest(15, "like_count")
        icons = {"positive": "✅", "negative": "❌", "mixed": "⚠️", "neutral": "💬"}
        for _, row in top_comments.iterrows():
            icon = icons.get(row["sentiment"], "💬")
            r.append(f"**{icon} 👍{row['like_count']}** | **{row['author']}**")
            r.append(f"> {row['text_clean'][:500]}")
            r.append("")

        negative = video_comments_df[
            video_comments_df["sentiment"].isin(["negative", "mixed"])
        ]
        if len(negative) > 0:
            r.append("### 负面/问题反馈\n")
            for _, row in negative.nlargest(10, "value_score").iterrows():
                r.append(f"**❌ 👍{row['like_count']}** | **{row['author']}**")
                r.append(f"> {row['text_clean'][:500]}")
                r.append("")
    else:
        r.append("*该视频无有效评论*\n")

    return "\n".join(r)


def generate_overall_report(all_qualified, tier_a, tier_b, filter_stats,
                            df_meaningful, transcript_stats,
                            video_content_analysis, channel_profiles):
    """
    生成总体分析报告（Markdown）。

    返回: str (Markdown 文本)
    """
    import pandas as pd

    report = []
    report.append("# Snapmaker U1 YouTube 用户反馈分析报告（量产机阶段）\n")
    report.append(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**数据范围**: 2025-11-15 至今（量产机开始交付后）\n")

    # 1. 数据概况
    report.append("## 1. 数据概况\n")
    report.append("| 指标 | 数值 |")
    report.append("|---|---|")
    report.append(f"| 搜索候选视频 | {filter_stats['total_searched']} |")
    report.append(f"| 相关性过滤后 | {filter_stats['after_relevance_filter']} |")
    report.append(f"| 质量过滤后 | {filter_stats['after_quality_filter']} |")
    report.append(f"| Tier A 视频数 | {filter_stats['tier_a_count']} |")
    report.append(f"| Tier B 视频数 | {filter_stats['tier_b_count']} |")
    report.append(f"| 赞助/样机视频 | {filter_stats['sponsored_count']} |")
    report.append(f"| 总观看量 | {sum(v['view_count'] for v in all_qualified):,} |")
    report.append(f"| 获取评论数 | {filter_stats.get('total_comments', 0):,} |")
    report.append(f"| 有效评论数 | {len(df_meaningful):,} |")
    report.append(f"| 成功转录视频 | {transcript_stats['success']} |")
    report.append("")

    # 2. 频道画像
    report.append("## 2. 视频来源频道画像\n")
    report.append("| 频道 | 粉丝数 | 国家 | 视频数 | U1视频观看 | 赞助 |")
    report.append("|---|---|---|---|---|---|")
    seen_channels = set()
    for v in all_qualified:
        ch = v.get("channel_profile", {})
        ch_name = v["channel"]
        if ch_name in seen_channels:
            continue
        seen_channels.add(ch_name)
        subs_str = _format_subs(ch.get("subscriber_count", 0))
        country = ch.get("channel_country", "?")
        total_vids = ch.get("total_video_count", "?")
        sp = "🏷️" if v.get("sponsor_status", {}).get("is_sponsored") else ""
        report.append(
            f"| {ch_name[:25]} | {subs_str} | {country} | {total_vids} "
            f"| {v['view_count']:,} | {sp} |"
        )
    report.append("")

    # 3. 赞助分布
    report.append("## 3. 赞助/样机状态分布\n")
    sponsor_types = Counter(
        v.get("sponsor_status", {}).get("sponsor_type", "unknown")
        for v in all_qualified
    )
    type_labels = {
        "sponsored": "🔴 官方赞助",
        "review_sample": "🟠 样机评测",
        "affiliate_only": "🟡 含联盟链接",
        "self_purchased": "🟢 自购",
        "unknown": "⚪ 未声明",
    }
    for st, count in sponsor_types.most_common():
        label = type_labels.get(st, st)
        report.append(f"- {label}: {count} 个视频")
    report.append("")

    # 4. 情感分布
    report.append("## 4. 评论情感分布\n")
    if len(df_meaningful) > 0:
        for sent, count in df_meaningful["sentiment"].value_counts().items():
            pct = count / len(df_meaningful) * 100
            bar = "█" * int(pct / 2)
            report.append(f"- **{sent}**: {count} ({pct:.1f}%) {bar}")
    report.append("")

    # 5. 主题排名
    topic_counter = Counter()
    if len(df_meaningful) > 0:
        for topics in df_meaningful["topics"]:
            if isinstance(topics, list):
                topic_counter.update(topics)
    report.append("## 5. 用户关注主题 Top 15\n")
    report.append("| 排名 | 主题 | 提及次数 | 占比 |")
    report.append("|---|---|---|---|")
    for rank, (topic, count) in enumerate(topic_counter.most_common(15), 1):
        pct = count / max(len(df_meaningful), 1) * 100
        report.append(f"| {rank} | {topic} | {count} | {pct:.1f}% |")
    report.append("")

    # 6. 痛点
    report.append("## 6. 用户痛点 Top 10\n")
    if len(df_meaningful) > 0:
        negative_df = df_meaningful[
            df_meaningful["sentiment"].isin(["negative", "mixed"])
        ]
        neg_by_topic = Counter()
        for _, row in negative_df.iterrows():
            if isinstance(row["topics"], list):
                neg_by_topic.update(row["topics"])
        for rank, (topic, count) in enumerate(neg_by_topic.most_common(10), 1):
            topic_comments = negative_df[
                negative_df["topics"].apply(
                    lambda t: topic in t if isinstance(t, list) else False
                )
            ]
            top_example = topic_comments.nlargest(1, "like_count")
            report.append(f"### {rank}. {topic} ({count} 条)\n")
            if len(top_example) > 0:
                report.append(
                    f"> 👍{top_example.iloc[0]['like_count']} | "
                    f"{top_example.iloc[0]['text_clean'][:200]}...\n"
                )
    report.append("")

    # 7. 正面反馈
    report.append("## 7. 用户最赞赏特性 Top 10\n")
    if len(df_meaningful) > 0:
        positive_df = df_meaningful[df_meaningful["sentiment"] == "positive"]
        pos_by_topic = Counter()
        for _, row in positive_df.iterrows():
            if isinstance(row["topics"], list):
                pos_by_topic.update(row["topics"])
        for rank, (topic, count) in enumerate(pos_by_topic.most_common(10), 1):
            topic_comments = positive_df[
                positive_df["topics"].apply(
                    lambda t: topic in t if isinstance(t, list) else False
                )
            ]
            top_example = topic_comments.nlargest(1, "like_count")
            report.append(f"### {rank}. {topic} ({count} 条)\n")
            if len(top_example) > 0:
                report.append(
                    f"> 👍{top_example.iloc[0]['like_count']} | "
                    f"{top_example.iloc[0]['text_clean'][:200]}...\n"
                )
    report.append("")

    # 8. Tier A 视频索引
    report.append("## 8. Tier A 视频索引\n")
    report.append(
        "| # | 频道 | 粉丝 | 标题 | 观看量 | 赞助 | 转录 | 关键信息 |"
    )
    report.append("|---|---|---|---|---|---|---|---|")
    for i, v in enumerate(tier_a, 1):
        ca = video_content_analysis.get(v["video_id"], {})
        tr_status = "✅" if ca.get("transcript_status") == "success" else "❌"
        km = ca.get("key_moment_count", 0)
        subs_str = _format_subs(
            v.get("channel_profile", {}).get("subscriber_count", 0)
        )
        sp_icon = "🏷️" if v.get("sponsor_status", {}).get("is_sponsored") else ""
        report.append(
            f"| {i} | {v['channel'][:18]} | {subs_str} | "
            f"{v['title'][:35]} | {v['view_count']:,} | {sp_icon} | "
            f"{tr_status} | {km} |"
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
