#!/usr/bin/env python3
"""
Snapmaker U1 YouTube 用户反馈提取系统 — 主入口

使用 YouTube Data API v3 + youtube-transcript-api 系统性搜集
Snapmaker U1 3D打印机量产机阶段（2025-11-15 后）的评测视频，
提取视频内容摘要、频道画像、赞助关系和用户评论，进行结构化分析。
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path

# 确保能导入同目录下的模块
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import pandas as pd

from config import (
    DATA_DIR, PER_VIDEO_DATA_DIR, REPORTS_DIR, PER_VIDEO_REPORTS_DIR,
    PUBLISHED_AFTER, SEARCH_QUERIES, KNOWN_REVIEWERS, KNOWN_CHANNEL_NAMES,
    KEY_INFO_PATTERNS,
)
from youtube_api import (
    init_youtube_client, search_videos, search_known_reviewers,
    get_video_details, get_channel_profiles,
)
from transcript import get_transcript, segment_transcript, format_timestamp
from analysis import (
    detect_sponsor_status, parse_duration, is_relevant, passes_quality,
    classify_tier, auto_select_tier_threshold, find_key_moments,
    analyze_sentiment, tag_topics,
)
from comments import get_all_comments, clean_comment
from reports import generate_per_video_report, generate_overall_report

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_checkpoint(name):
    """加载中间数据检查点"""
    path = DATA_DIR / f"{name}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"✅ 从检查点加载: {name} ({path.stat().st_size:,} bytes)")
        return data
    return None


def save_checkpoint(name, data):
    """保存中间数据检查点"""
    path = DATA_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"💾 保存检查点: {name}")


def main():
    # ===== Step 0: 环境准备 =====
    env_path = Path(__file__).parent.parent / ".env"
    # Windows PowerShell 的 echo 会生成 UTF-16 编码文件，需要自动转换
    if env_path.exists():
        try:
            raw = env_path.read_bytes()
            if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
                text = raw.decode('utf-16').strip()
                env_path.write_text(text + '\n', encoding='utf-8')
                logger.info("已将 .env 从 UTF-16 转换为 UTF-8")
        except Exception:
            pass
    load_dotenv(env_path)
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.error("❌ YOUTUBE_API_KEY 未设置。请在 .env 文件中填入 API Key。")
        sys.exit(1)

    # 创建输出目录
    for d in [DATA_DIR, PER_VIDEO_DATA_DIR, REPORTS_DIR, PER_VIDEO_REPORTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    youtube = init_youtube_client(api_key)
    logger.info("=" * 60)
    logger.info("Snapmaker U1 YouTube 用户反馈提取系统")
    logger.info(f"时间范围: {PUBLISHED_AFTER} 至今")
    logger.info("=" * 60)

    # ===== Step 1: 视频搜索与发现 =====
    logger.info("\n📡 Step 1: 视频搜索与发现")

    cached = load_checkpoint("search_results")
    if cached:
        video_search_results = cached["results"]
        all_video_ids = set(v["video_id"] for v in video_search_results)
    else:
        all_video_ids, video_search_results = search_videos(
            youtube, SEARCH_QUERIES, PUBLISHED_AFTER, max_results_per_query=20,
        )
        all_video_ids, video_search_results = search_known_reviewers(
            youtube, KNOWN_REVIEWERS, video_search_results,
            all_video_ids, PUBLISHED_AFTER,
        )
        save_checkpoint("search_results", {
            "results": video_search_results,
            "count": len(all_video_ids),
        })

    logger.info(f"共发现 {len(all_video_ids)} 个独立视频")

    # ===== Step 2: 获取视频详情 + 频道画像 =====
    logger.info("\n📋 Step 2: 获取视频详情 + 频道画像")

    cached = load_checkpoint("video_details")
    if cached:
        video_details = cached
    else:
        video_details = get_video_details(youtube, all_video_ids)
        save_checkpoint("video_details", video_details)

    # 频道画像
    cached = load_checkpoint("channel_profiles")
    if cached:
        channel_profiles = cached
    else:
        channel_ids = [v["channel_id"] for v in video_details.values()]
        channel_profiles = get_channel_profiles(youtube, channel_ids)
        save_checkpoint("channel_profiles", channel_profiles)

    # 关联频道画像到视频
    for vid, video in video_details.items():
        ch_id = video["channel_id"]
        if ch_id in channel_profiles:
            video["channel_profile"] = channel_profiles[ch_id]
        else:
            video["channel_profile"] = {"subscriber_count": 0, "channel_description": "N/A"}

    # 频道粉丝数 Top 15
    sorted_channels = sorted(
        channel_profiles.values(),
        key=lambda x: x["subscriber_count"],
        reverse=True,
    )
    logger.info(f"\n频道粉丝数 Top 15:")
    for ch in sorted_channels[:15]:
        subs = ch["subscriber_count"]
        subs_str = (f"{subs / 1_000_000:.1f}M" if subs >= 1_000_000
                    else f"{subs / 1000:.1f}K" if subs >= 1000
                    else str(subs))
        logger.info(f"  {subs_str:>8} | {ch['channel_name']} ({ch['channel_country']})")

    # ===== Step 2.3: 赞助/样机检测（第一轮：基于描述） =====
    logger.info("\n🏷️ Step 2.3: 赞助/样机检测（基于描述）")
    for vid, video in video_details.items():
        video["sponsor_status"] = detect_sponsor_status(video["description"])
        if video["sponsor_status"]["is_sponsored"]:
            logger.info(
                f"  🏷️ [{video['sponsor_status']['sponsor_type']}] "
                f"{video['channel']} - {video['title'][:50]}"
            )

    sponsored_count = sum(
        1 for v in video_details.values() if v["sponsor_status"]["is_sponsored"]
    )
    logger.info(f"赞助/样机检测: {sponsored_count} / {len(video_details)} 个视频")

    # ===== Step 2.4: 筛选与播放量分布 =====
    logger.info("\n📊 Step 2.4: 筛选与播放量分布")

    # Layer 1: 相关性
    candidates = {vid: v for vid, v in video_details.items() if is_relevant(v)}
    logger.info(f"Layer 1 相关性过滤: {len(video_details)} → {len(candidates)}")

    # Layer 2: 质量
    qualified = {vid: v for vid, v in candidates.items() if passes_quality(v)}
    for vid, v in qualified.items():
        v["duration_seconds"] = parse_duration(v["duration"])
    logger.info(f"Layer 2 质量过滤: {len(candidates)} → {len(qualified)}")

    # 播放量分布
    view_counts = sorted([v["view_count"] for v in qualified.values()], reverse=True)
    logger.info(f"\n{'=' * 60}")
    logger.info(f"📊 播放量分布（{len(qualified)} 个合格视频）")
    logger.info(f"{'=' * 60}")
    thresholds = [50000, 20000, 10000, 5000, 3000, 1000, 500, 100]
    for th in thresholds:
        count = sum(1 for vc in view_counts if vc >= th)
        logger.info(f"  ≥ {th:>6,} views:  {count:>3} 个视频")
    if view_counts:
        logger.info(f"  中位数: {view_counts[len(view_counts) // 2]:,} views")
        logger.info(f"  平均值: {sum(view_counts) // len(view_counts):,} views")

    # 自动选择 Tier A 阈值
    VIEW_THRESHOLD_TIER_A = auto_select_tier_threshold(view_counts)
    logger.info(f"\n🎯 自动选择 Tier A 阈值: {VIEW_THRESHOLD_TIER_A:,} views")

    # ===== Step 2.5: 分级 =====
    logger.info("\n📊 Step 2.5: 分级")
    for vid, video in qualified.items():
        video["tier"] = classify_tier(video, VIEW_THRESHOLD_TIER_A)

    tier_a = sorted(
        [v for v in qualified.values() if v["tier"] == "A"],
        key=lambda x: x["view_count"], reverse=True,
    )
    tier_b = sorted(
        [v for v in qualified.values() if v["tier"] == "B"],
        key=lambda x: x["view_count"], reverse=True,
    )
    all_qualified = tier_a + tier_b

    logger.info(f"  Tier A (深度分析): {len(tier_a)} 个视频")
    logger.info(f"  Tier B (标准分析): {len(tier_b)} 个视频")
    logger.info(f"  总计: {len(all_qualified)} 个视频")

    # 输出 Tier A 列表
    logger.info(f"\n{'=' * 100}")
    logger.info("TIER A 视频列表:")
    logger.info(f"{'=' * 100}")
    for i, v in enumerate(tier_a, 1):
        mins = v["duration_seconds"] // 60
        subs = v.get("channel_profile", {}).get("subscriber_count", 0)
        subs_str = f"{subs / 1000:.0f}K" if subs >= 1000 else str(subs)
        sponsor = "🏷️" if v.get("sponsor_status", {}).get("is_sponsored") else "  "
        sp_type = v.get("sponsor_status", {}).get("sponsor_type", "")
        logger.info(
            f"  {i:2d}. {sponsor} [{mins:3d}min] {v['view_count']:>10,} views | "
            f"{v['comment_count']:>4} cmt | {subs_str:>7} subs | "
            f"{v['channel'][:20]:20s} | {v['title'][:45]} | {sp_type}"
        )

    # 保存视频索引
    save_checkpoint("video_index", all_qualified)

    filter_stats = {
        "time_cutoff": PUBLISHED_AFTER,
        "view_threshold_tier_a": VIEW_THRESHOLD_TIER_A,
        "total_searched": len(video_details),
        "after_relevance_filter": len(candidates),
        "after_quality_filter": len(qualified),
        "tier_a_count": len(tier_a),
        "tier_b_count": len(tier_b),
        "total_qualified": len(all_qualified),
        "sponsored_count": sum(
            1 for v in all_qualified if v.get("sponsor_status", {}).get("is_sponsored")
        ),
    }
    save_checkpoint("filter_stats", filter_stats)

    # ===== Step 3: 视频转录提取 =====
    logger.info("\n🎙️ Step 3: 视频转录提取")

    cached = load_checkpoint("transcripts")
    if cached:
        transcript_results = cached
    else:
        transcript_results = {}

    transcript_stats = {"success": 0, "failed": 0, "reasons": {}}

    for i, video in enumerate(all_qualified):
        vid = video["video_id"]

        # 断点续跑：跳过已获取的
        if vid in transcript_results:
            tr = transcript_results[vid]
            if tr.get("status") == "success":
                transcript_stats["success"] += 1
            else:
                transcript_stats["failed"] += 1
            continue

        logger.info(
            f"[{i + 1}/{len(all_qualified)}] 转录: "
            f"{video['channel'][:20]} - {video['title'][:45]}..."
        )

        entries, source = get_transcript(vid)

        if entries is None:
            transcript_results[vid] = {
                "status": "failed", "reason": source,
                "segments": [], "full_text": "",
            }
            transcript_stats["failed"] += 1
            transcript_stats["reasons"][source] = (
                transcript_stats["reasons"].get(source, 0) + 1
            )
            logger.info(f"  ❌ 失败: {source}")
        else:
            full_text = " ".join(e.get("text", "") for e in entries)
            seg_min = 3 if video["tier"] == "A" else 5
            segments = segment_transcript(entries, segment_minutes=seg_min)

            last_start = entries[-1].get("start", 0) if entries else 0
            transcript_results[vid] = {
                "status": "success", "source": source,
                "total_entries": len(entries),
                "segments": segments,
                "full_text": full_text,
                "duration_covered": format_timestamp(last_start),
            }
            transcript_stats["success"] += 1
            logger.info(
                f"  ✅ ({source}): {len(entries)} 条字幕, {len(segments)} 段"
            )

            # 用转录文本更新赞助检测
            video["sponsor_status"] = detect_sponsor_status(
                video["description"], full_text,
            )

        time.sleep(1.0)

        # 每 10 个视频保存一次检查点
        if (i + 1) % 10 == 0:
            save_checkpoint("transcripts", transcript_results)

    save_checkpoint("transcripts", transcript_results)

    sponsored_after = sum(
        1 for v in all_qualified if v.get("sponsor_status", {}).get("is_sponsored")
    )
    logger.info(
        f"\n转录统计: 成功 {transcript_stats['success']}, "
        f"失败 {transcript_stats['failed']}"
    )
    logger.info(f"赞助检测更新（含转录分析）: {sponsored_after} 个视频标记为赞助/样机")

    # ===== Step 4: 视频内容分析 =====
    logger.info("\n🔍 Step 4: 视频内容分析")

    video_content_analysis = {}
    for video in all_qualified:
        vid = video["video_id"]
        tr = transcript_results.get(vid, {})

        analysis = {
            "video_id": vid,
            "title": video["title"],
            "channel": video["channel"],
            "tier": video["tier"],
            "duration_seconds": video.get("duration_seconds", 0),
            "view_count": video["view_count"],
            "transcript_status": tr.get("status", "not_attempted"),
            "transcript_source": tr.get("source", "N/A"),
        }

        if tr.get("status") == "success":
            segments = tr.get("segments", [])
            analysis["segment_count"] = len(segments)
            analysis["transcript_word_count"] = len(
                tr.get("full_text", "").split()
            )

            key_moments = find_key_moments(segments, video["title"])
            analysis["key_moments"] = key_moments
            analysis["key_moment_count"] = len(key_moments)

            moment_types = {}
            for m in key_moments:
                t = m["label"]
                if t not in moment_types:
                    moment_types[t] = []
                moment_types[t].append(m["timestamp"])
            analysis["key_info_summary"] = {
                k: {"count": len(v), "timestamps": v}
                for k, v in moment_types.items()
            }

            analysis["segments_overview"] = []
            for seg in segments:
                seg_info_types = set()
                seg_text_lower = seg.get("full_text", "").lower()
                for info_type, config in KEY_INFO_PATTERNS.items():
                    for pattern in config["patterns"]:
                        if re.search(pattern, seg_text_lower):
                            seg_info_types.add(config["label"])
                            break
                analysis["segments_overview"].append({
                    "time_range": (
                        f"{seg['start_timestamp']} - "
                        f"{seg.get('end_timestamp', '?')}"
                    ),
                    "preview": seg.get("full_text", "")[:200],
                    "word_count": len(seg.get("full_text", "").split()),
                    "detected_topics": list(seg_info_types),
                })
        else:
            analysis["key_moments"] = []
            analysis["key_moment_count"] = 0
            analysis["key_info_summary"] = {}
            analysis["segments_overview"] = []

        video_content_analysis[vid] = analysis

    save_checkpoint("video_content_analysis", video_content_analysis)
    logger.info(f"内容分析完成: {len(video_content_analysis)} 个视频")

    # ===== Step 5: 获取评论 =====
    logger.info("\n💬 Step 5: 获取评论")

    cached = load_checkpoint("all_comments")
    if cached:
        all_comments = cached
    else:
        all_comments = []
        for i, video in enumerate(all_qualified):
            vid = video["video_id"]
            if video["comment_count"] == 0:
                continue
            max_c = 500 if video["tier"] == "A" else 200
            logger.info(
                f"[{i + 1}/{len(all_qualified)}] 评论: "
                f"{video['channel'][:18]} - {video['title'][:40]}... (max {max_c})"
            )
            comments = get_all_comments(youtube, vid, max_comments=max_c)
            all_comments.extend(comments)
            top_level = [c for c in comments if not c["is_reply"]]
            replies = [c for c in comments if c["is_reply"]]
            logger.info(
                f"  → {len(top_level)} 顶层 + {len(replies)} 回复 = "
                f"{len(comments)} 条"
            )
            time.sleep(0.5)

        save_checkpoint("all_comments", all_comments)

    logger.info(f"评论获取完成: {len(all_comments)} 条")

    # ===== Step 6: 评论分析 =====
    logger.info("\n📊 Step 6: 评论分析")

    df = pd.DataFrame(all_comments)

    if len(df) > 0:
        df["text_clean"] = df["text"].apply(clean_comment)
        df["text_length"] = df["text_clean"].str.len()
        df_meaningful = df[df["text_length"] >= 30].copy()

        df_meaningful["topics"] = df_meaningful["text_clean"].apply(tag_topics)
        df_meaningful["sentiment"] = df_meaningful["text_clean"].apply(
            analyze_sentiment
        )
        df_meaningful["value_score"] = (
            df_meaningful["text_length"].clip(upper=500) / 100
            + df_meaningful["topics"].apply(len) * 2
            + df_meaningful["like_count"].clip(upper=50) / 5
        )

        csv_path = DATA_DIR / "comments_analyzed.csv"
        df_meaningful.to_csv(csv_path, index=False)
        logger.info(
            f"评论分析完成: {len(df_meaningful)} 条有效评论 "
            f"(总 {len(df)} 条)"
        )
    else:
        df_meaningful = pd.DataFrame()
        logger.info("无评论数据")

    # 更新 filter_stats
    filter_stats["total_comments"] = len(df)

    # ===== Step 7: 生成单视频详情报告（Tier A） =====
    logger.info("\n📝 Step 7: 生成 Tier A 视频详情报告")

    for video in tier_a:
        vid = video["video_id"]
        ca = video_content_analysis.get(vid, {})

        if len(df_meaningful) > 0:
            video_comments = df_meaningful[
                df_meaningful["video_id"] == vid
            ].copy()
        else:
            video_comments = pd.DataFrame()

        report_text = generate_per_video_report(video, ca, video_comments)

        safe_channel = re.sub(r'[^\w\-]', '_', video["channel"])[:20]
        safe_title = re.sub(r'[^\w\-]', '_', video["title"])[:30]
        filename = f"{safe_channel}_{safe_title}.md"

        filepath = PER_VIDEO_REPORTS_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_text)
        logger.info(f"✅ 生成: {filename}")

    logger.info(f"共生成 {len(tier_a)} 份 Tier A 视频详情报告")

    # ===== Step 8: 生成总体报告 =====
    logger.info("\n📊 Step 8: 生成总体报告")

    report_text = generate_overall_report(
        all_qualified=all_qualified,
        tier_a=tier_a,
        tier_b=tier_b,
        filter_stats=filter_stats,
        df_meaningful=df_meaningful,
        transcript_stats=transcript_stats,
        video_content_analysis=video_content_analysis,
        channel_profiles=channel_profiles,
    )

    report_path = REPORTS_DIR / "youtube_analysis_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    logger.info(f"✅ 总体报告已生成: {report_path}")

    # ===== 完成 =====
    logger.info("\n" + "=" * 60)
    logger.info("✅ 全部完成！")
    logger.info(f"  数据目录: {DATA_DIR}")
    logger.info(f"  报告目录: {REPORTS_DIR}")
    logger.info(f"  Tier A 报告: {PER_VIDEO_REPORTS_DIR}")
    logger.info("=" * 60)

    # 输出文件清单
    for dirpath in [DATA_DIR, REPORTS_DIR, PER_VIDEO_REPORTS_DIR]:
        for f in sorted(dirpath.iterdir()):
            if f.is_file():
                logger.info(f"  {f} ({f.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
