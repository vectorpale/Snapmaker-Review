"""
Excel 报告生成模块

使用 pandas + openpyxl 生成 Snapmaker U1 产品反馈分析 Excel 报告。
每个 Sheet 对应一个分析维度，方便后续数据整理。
"""

import logging
import re
from collections import Counter
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

from pptx_report import (
    TOPIC_DISPLAY,
    _build_video_opinion_table,
    _extract_section,
    _parse_markdown_table,
)

logger = logging.getLogger(__name__)

# --- 表头样式 (与 PPTX COLOR_PRIMARY 一致) ---
_HEADER_FILL = PatternFill(start_color="1A5276", end_color="1A5276", fill_type="solid")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
_BODY_FONT = Font(size=11, name="Calibri")
_WRAP_ALIGN = Alignment(wrap_text=True, vertical="top")

# --- 赞助状态映射 ---
SPONSOR_DISPLAY = {
    "sponsored": "官方赞助",
    "review_sample": "样机评测",
    "affiliate_only": "含联盟链接",
    "self_purchased": "自购",
    "unknown": "未声明",
}

SENTIMENT_DISPLAY = {
    "positive": "正面",
    "negative": "负面",
    "neutral": "中性",
    "mixed": "混合",
}


def _style_header(ws):
    """给工作表第一行应用深蓝色表头样式。"""
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _auto_width(ws, max_width=60):
    """根据内容自动调整列宽。"""
    for col in ws.columns:
        letter = col[0].column_letter
        lengths = []
        for cell in col:
            val = str(cell.value or "")
            # 中文字符占 2 个宽度单位
            w = sum(2 if ord(c) > 127 else 1 for c in val[:100])
            lengths.append(w)
        best = min(max(lengths) + 2, max_width) if lengths else 12
        ws.column_dimensions[letter].width = max(best, 8)


def _write_overview(writer, top_videos, filter_stats, df_comments, llm_results):
    """Sheet 1: 数据概览 — 管道统计指标。"""
    total_views = sum(v.get("view_count", 0) for v in top_videos)
    total_comments = len(df_comments) if df_comments is not None else 0
    transcript_ok = sum(
        1 for v in top_videos
        if llm_results.get(v["video_id"], {})
        .get("transcript", {}).get("status") == "success"
    )
    llm_ok = sum(
        1 for v in top_videos
        if llm_results.get(v["video_id"], {})
        .get("transcript", {}).get("status") == "success"
    )
    sponsored = sum(
        1 for v in top_videos
        if v.get("sponsor_status", {}).get("is_sponsored")
    )

    rows = [
        ("搜索候选视频", filter_stats.get("total_searched", "-")),
        ("相关性过滤后", filter_stats.get("after_relevance_filter", "-")),
        ("质量过滤后", filter_stats.get("after_quality_filter", "-")),
        ("播放量过滤后", filter_stats.get("after_view_filter", "-")),
        ("最终分析视频数", len(top_videos)),
        ("赞助/样机视频", sponsored),
        ("总观看量", f"{total_views:,}"),
        ("总评论数", filter_stats.get("total_comments", "-")),
        ("有效评论数", total_comments),
        ("字幕获取成功", transcript_ok),
        ("LLM 分析成功", llm_ok),
        ("最低播放量阈值", filter_stats.get("min_view_count", "-")),
        ("时间截止", filter_stats.get("time_cutoff", "-")),
    ]

    df = pd.DataFrame(rows, columns=["指标", "值"])
    sheet = "数据概览"
    df.to_excel(writer, sheet_name=sheet, index=False)
    ws = writer.sheets[sheet]
    _style_header(ws)
    _auto_width(ws)
    ws.freeze_panes = "A2"


def _write_video_index(writer, top_videos, llm_results):
    """Sheet 2: 视频索引 — 完整视频列表。"""
    rows = []
    for i, v in enumerate(top_videos, 1):
        vid = v["video_id"]
        sp = v.get("sponsor_status", {})
        lr = llm_results.get(vid, {})
        t_status = lr.get("transcript", {}).get("status", "-")
        subs = v.get("channel_profile", {}).get("subscriber_count", 0)

        rows.append({
            "#": i,
            "频道": v["channel"],
            "标题": v["title"],
            "发布日期": v.get("published_at", "")[:10],
            "播放量": v.get("view_count", 0),
            "点赞数": v.get("like_count", 0),
            "评论数": v.get("comment_count", 0),
            "时长(分)": v.get("duration_seconds", 0) // 60,
            "粉丝数": subs,
            "赞助状态": SPONSOR_DISPLAY.get(sp.get("sponsor_type", "unknown"), "-"),
            "字幕状态": t_status,
            "YouTube链接": f"https://youtube.com/watch?v={vid}",
        })

    df = pd.DataFrame(rows)
    sheet = "视频索引"
    df.to_excel(writer, sheet_name=sheet, index=False)
    ws = writer.sheets[sheet]
    _style_header(ws)
    _auto_width(ws)
    ws.freeze_panes = "A2"


def _write_opinion(writer, top_videos, llm_results):
    """Sheet 3: 各频道评价 — 频道对 U1 的推荐态度。"""
    table = _build_video_opinion_table(top_videos, llm_results)
    df = pd.DataFrame(table["rows"], columns=table["headers"])
    sheet = "各频道评价"
    df.to_excel(writer, sheet_name=sheet, index=False)
    ws = writer.sheets[sheet]
    _style_header(ws)
    _auto_width(ws)
    ws.freeze_panes = "A2"


def _write_sentiment(writer, top_videos, df_comments):
    """Sheet 4: 情感统计 — 整体 + 按视频拆分。"""
    if df_comments is None or len(df_comments) == 0:
        df = pd.DataFrame([["无评论数据"]], columns=["备注"])
        df.to_excel(writer, sheet_name="情感统计", index=False)
        return

    total = len(df_comments)

    # Part A: 整体情感
    counts = df_comments["sentiment"].value_counts()
    overall_rows = []
    for s in ["positive", "neutral", "negative", "mixed"]:
        c = counts.get(s, 0)
        pct = round(c / total * 100, 1) if total else 0
        overall_rows.append({
            "情感": SENTIMENT_DISPLAY.get(s, s),
            "评论数": c,
            "占比(%)": pct,
        })
    df_overall = pd.DataFrame(overall_rows)

    # Part B: 按视频拆分
    vid_map = {v["video_id"]: v["channel"][:25] for v in top_videos}
    per_video_rows = []
    for v in top_videos:
        vid = v["video_id"]
        vc = df_comments[df_comments["video_id"] == vid]
        if len(vc) == 0:
            continue
        vc_counts = vc["sentiment"].value_counts()
        row = {
            "频道": v["channel"][:25],
            "视频标题": v["title"][:50],
        }
        for s in ["positive", "neutral", "negative", "mixed"]:
            row[SENTIMENT_DISPLAY.get(s, s)] = vc_counts.get(s, 0)
        row["合计"] = len(vc)
        per_video_rows.append(row)
    df_per = pd.DataFrame(per_video_rows)

    sheet = "情感统计"
    # 写入整体统计
    df_overall.to_excel(writer, sheet_name=sheet, index=False, startrow=0)
    # 空两行后写入按视频统计
    start = len(df_overall) + 3
    df_per.to_excel(writer, sheet_name=sheet, index=False, startrow=start)

    ws = writer.sheets[sheet]
    # 样式：两段表头
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
    if len(df_per) > 0:
        for cell in ws[start + 1]:
            if cell.value:
                cell.fill = _HEADER_FILL
                cell.font = _HEADER_FONT
    _auto_width(ws)
    ws.freeze_panes = "A2"


def _write_topics(writer, df_comments):
    """Sheet 5: 话题热度 — 话题提及次数排名。"""
    if df_comments is None or len(df_comments) == 0:
        df = pd.DataFrame([["无评论数据"]], columns=["备注"])
        df.to_excel(writer, sheet_name="话题热度", index=False)
        return

    counter = Counter()
    for topics in df_comments["topics"]:
        if isinstance(topics, list):
            counter.update(topics)
        elif isinstance(topics, str) and topics:
            for t in topics.strip("[]").replace("'", "").split(","):
                t = t.strip()
                if t:
                    counter[t] += 1

    total_mentions = sum(counter.values())
    rows = []
    for rank, (topic, count) in enumerate(counter.most_common(), 1):
        rows.append({
            "排名": rank,
            "话题Key": topic,
            "中文名": TOPIC_DISPLAY.get(topic, topic),
            "提及次数": count,
            "占比(%)": round(count / total_mentions * 100, 1) if total_mentions else 0,
        })

    df = pd.DataFrame(rows)
    sheet = "话题热度"
    df.to_excel(writer, sheet_name=sheet, index=False)
    ws = writer.sheets[sheet]
    _style_header(ws)
    _auto_width(ws)
    ws.freeze_panes = "A2"


def _write_llm_section(writer, overall_llm, sheet_name, patterns):
    """通用：从 Overall LLM 提取某板块，解析 markdown 表格或写入文本。"""
    text = overall_llm.get("analysis_text", "") if overall_llm else ""
    section = _extract_section(text, patterns)

    if not section:
        df = pd.DataFrame([["该板块暂无内容"]], columns=["备注"])
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        _style_header(ws)
        return

    # 尝试解析 markdown 表格
    tables = _parse_markdown_table(section)
    if tables:
        row_offset = 0
        for tbl in tables:
            df = pd.DataFrame(tbl["rows"], columns=tbl["headers"])
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=row_offset)
            ws = writer.sheets[sheet_name]
            for cell in ws[row_offset + 1]:
                if cell.value:
                    cell.fill = _HEADER_FILL
                    cell.font = _HEADER_FONT
            row_offset += len(df) + 3
        _auto_width(ws)
        ws.freeze_panes = "A2"
        return

    # 无表格：将文本按行写入
    lines = [line.strip() for line in section.split("\n") if line.strip()]
    df = pd.DataFrame(lines, columns=["内容"])
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    ws = writer.sheets[sheet_name]
    _style_header(ws)
    # 长文本自动换行
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP_ALIGN
    _auto_width(ws)
    ws.freeze_panes = "A2"


def _write_competitor(writer, overall_llm):
    """Sheet 8: 竞品对比 — Bambu + 其他竞品。"""
    text = overall_llm.get("analysis_text", "") if overall_llm else ""

    bambu = _extract_section(text, [r"Bambu", r"竞品", r"Competitive"])
    other = _extract_section(text, [r"其他竞品", r"Other Competitor"])
    combined = ""
    if bambu:
        combined += "## Bambu Lab 对比\n\n" + bambu + "\n\n"
    if other:
        combined += "## 其他竞品对比\n\n" + other

    if not combined.strip():
        df = pd.DataFrame([["该板块暂无内容"]], columns=["备注"])
        df.to_excel(writer, sheet_name="竞品对比", index=False)
        ws = writer.sheets["竞品对比"]
        _style_header(ws)
        return

    # 尝试解析 markdown 表格
    tables = _parse_markdown_table(combined)
    if tables:
        row_offset = 0
        sheet_name = "竞品对比"
        for tbl in tables:
            df = pd.DataFrame(tbl["rows"], columns=tbl["headers"])
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=row_offset)
            ws = writer.sheets[sheet_name]
            for cell in ws[row_offset + 1]:
                if cell.value:
                    cell.fill = _HEADER_FILL
                    cell.font = _HEADER_FONT
            row_offset += len(df) + 3
        _auto_width(ws)
        ws.freeze_panes = "A2"
        return

    lines = [line.strip() for line in combined.split("\n") if line.strip()]
    df = pd.DataFrame(lines, columns=["内容"])
    sheet_name = "竞品对比"
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    ws = writer.sheets[sheet_name]
    _style_header(ws)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP_ALIGN
    _auto_width(ws)
    ws.freeze_panes = "A2"


def _write_exec_summary(writer, overall_llm):
    """Sheet 9: 执行摘要。"""
    text = overall_llm.get("analysis_text", "") if overall_llm else ""
    summary = _extract_section(text, [r"执行摘要", r"Executive Summary", r"摘要"])
    if not summary:
        summary = "执行摘要暂无内容"

    lines = [line.strip() for line in summary.split("\n") if line.strip()]
    df = pd.DataFrame(lines, columns=["执行摘要"])
    sheet = "执行摘要"
    df.to_excel(writer, sheet_name=sheet, index=False)
    ws = writer.sheets[sheet]
    _style_header(ws)
    ws.column_dimensions["A"].width = 120
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP_ALIGN
    ws.freeze_panes = "A2"


def _write_comment_analysis(writer, top_videos, llm_results, df_comments):
    """Sheet 10: 评论分析 — 每视频 LLM 评论分析摘要。"""
    rows = []
    for v in top_videos:
        vid = v["video_id"]
        ca = llm_results.get(vid, {}).get("comments", {})
        ca_text = ca.get("analysis_text", "")
        ca_status = ca.get("status", "-")
        comment_count = 0
        if df_comments is not None and len(df_comments) > 0:
            comment_count = len(df_comments[df_comments["video_id"] == vid])

        rows.append({
            "频道": v["channel"][:25],
            "视频标题": v["title"][:60],
            "有效评论数": comment_count,
            "分析状态": ca_status,
            "评论分析摘要": ca_text[:1000] if ca_text else "-",
        })

    df = pd.DataFrame(rows)
    sheet = "评论分析"
    df.to_excel(writer, sheet_name=sheet, index=False)
    ws = writer.sheets[sheet]
    _style_header(ws)
    # 摘要列自动换行
    for row in ws.iter_rows(min_row=2, min_col=5, max_col=5):
        for cell in row:
            cell.alignment = _WRAP_ALIGN
    _auto_width(ws)
    ws.freeze_panes = "A2"


# ============================================================
# Main entry point
# ============================================================

def generate_excel_report(
    top_videos,
    filter_stats,
    df_comments,
    llm_results,
    overall_llm,
    output_path,
    overall_llm_u1=None,
    overall_llm_h2c=None,
    overall_llm_comp=None,
):
    """
    生成 Excel 产品分析报告。

    参数与 generate_pptx_report 完全一致：
        top_videos: 视频列表 (list[dict])
        filter_stats: 管道统计 (dict)
        df_comments: 评论 DataFrame
        llm_results: {video_id: {transcript: {}, comments: {}}}
        overall_llm: 整体 LLM 分析 (dict)
        output_path: XLSX 输出路径
    """
    output_path = Path(output_path)

    with pd.ExcelWriter(str(output_path), engine="openpyxl") as writer:
        _write_overview(writer, top_videos, filter_stats, df_comments, llm_results)
        _write_video_index(writer, top_videos, llm_results)
        _write_opinion(writer, top_videos, llm_results)
        _write_sentiment(writer, top_videos, df_comments)
        _write_topics(writer, df_comments)
        _write_llm_section(writer, overall_llm, "优点统计",
                           [r"优点", r"亮点", r"Strengths"])
        _write_llm_section(writer, overall_llm, "缺点统计",
                           [r"缺点", r"问题", r"Issues"])
        _write_competitor(writer, overall_llm)
        _write_exec_summary(writer, overall_llm)
        _write_comment_analysis(writer, top_videos, llm_results, df_comments)

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"  Excel 报告已生成: {output_path} ({size_kb:.0f} KB)")
    return output_path
