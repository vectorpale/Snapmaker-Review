"""
PowerPoint 报告生成模块

使用 python-pptx + matplotlib 生成 Snapmaker U1 产品反馈分析报告。
包含 think-cell 风格图表、原生表格、12pt+ 字体。
"""

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
from lxml import etree
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

logger = logging.getLogger(__name__)

# --- 颜色方案 ---
COLOR_PRIMARY = RGBColor(0x1A, 0x52, 0x76)
COLOR_ACCENT = RGBColor(0x29, 0x80, 0xB9)
COLOR_POSITIVE = RGBColor(0x27, 0xAE, 0x60)
COLOR_NEGATIVE = RGBColor(0xE7, 0x4C, 0x3C)
COLOR_NEUTRAL = RGBColor(0x95, 0xA5, 0xA6)
COLOR_MIXED = RGBColor(0xF3, 0x9C, 0x12)
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_DARK = RGBColor(0x33, 0x33, 0x33)
COLOR_LIGHT_BG = RGBColor(0xF0, 0xF7, 0xFF)
COLOR_ALT_ROW = RGBColor(0xF5, 0xFA, 0xFF)

# --- 图表配色 (hex, for matplotlib) ---
CHART_COLORS = {
    "positive": "#27ae60",
    "negative": "#e74c3c",
    "neutral": "#95a5a6",
    "mixed": "#f39c12",
    "primary": "#2980b9",
    "secondary": "#1a5276",
}
CHART_DPI = 150

# --- 话题显示名映射 (from pdf_report.py) ---
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


# --- 模板布局常量 (Ion Boardroom) ---
LAYOUT_TITLE = 0       # Title Slide: placeholders [0]=title, [1]=subtitle
LAYOUT_CONTENT = 1     # Title and Content: [0]=title, [1]=content body
LAYOUT_SECTION = 2     # Section Header: [0]=title, [1]=description
LAYOUT_TITLE_ONLY = 5  # Title Only: [0]=title (chart/table below)
LAYOUT_BLANK = 6       # Blank: no placeholders
SLIDE_W = 13.333       # Ion Boardroom slide width (inches)

# --- 模板路径 ---
_TEMPLATE_DIR = Path(__file__).parent / "pptx_templates"
_TEMPLATE_NAME = "Ion_Boardroom.pptx"


def _get_template_path():
    """查找 SlideDeck AI 模板文件。"""
    local = _TEMPLATE_DIR / _TEMPLATE_NAME
    if local.exists():
        return str(local)
    try:
        import slidedeckai
        pkg = Path(slidedeckai.__file__).parent / "pptx_templates" / _TEMPLATE_NAME
        if pkg.exists():
            return str(pkg)
    except ImportError:
        pass
    return None


# --- 字体设置 ---
_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
FONT_LATIN = "Calibri"
FONT_EA = "等线"


def _set_paragraph_font(p, latin=None, ea=None):
    """设置段落中所有 run 的中英文字体。"""
    latin = latin or FONT_LATIN
    ea = ea or FONT_EA
    for r_elem in p._p.findall(f"{{{_NS}}}r"):
        rPr = r_elem.find(f"{{{_NS}}}rPr")
        if rPr is None:
            rPr = etree.SubElement(r_elem, f"{{{_NS}}}rPr")
        # Latin font (Calibri)
        latin_elem = rPr.find(f"{{{_NS}}}latin")
        if latin_elem is None:
            latin_elem = etree.SubElement(rPr, f"{{{_NS}}}latin")
        latin_elem.set("typeface", latin)
        # East Asian font (等线)
        ea_elem = rPr.find(f"{{{_NS}}}ea")
        if ea_elem is None:
            ea_elem = etree.SubElement(rPr, f"{{{_NS}}}ea")
        ea_elem.set("typeface", ea)


# ============================================================
# SlideDeck AI 文本格式化工具 (adapted from slidedeckai.helpers.pptx_helper)
# ============================================================

_BOLD_ITALICS_PATTERN = re.compile(r'(\*\*(.*?)\*\*|\*(.*?)\*)')


def _format_text(paragraph, text):
    """应用 **bold** 和 *italic* markdown 格式化到段落。"""
    matches = list(_BOLD_ITALICS_PATTERN.finditer(text))
    last_index = 0
    for match in matches:
        start, end = match.span()
        if start > last_index:
            run = paragraph.add_run()
            run.text = text[last_index:start]
        if match.group(2):
            run = paragraph.add_run()
            run.text = match.group(2)
            run.font.bold = True
        elif match.group(3):
            run = paragraph.add_run()
            run.text = match.group(3)
            run.font.italic = True
        last_index = end
    if last_index < len(text):
        run = paragraph.add_run()
        run.text = text[last_index:]


def _get_flat_list(items, level=0):
    """递归展平嵌套列表为 (text, level) 元组列表。"""
    flat = []
    for item in items:
        if isinstance(item, str):
            flat.append((item, level))
        elif isinstance(item, list):
            flat.extend(_get_flat_list(item, level + 1))
    return flat


def _add_bulleted_items(text_frame, flat_items):
    """向 text_frame 添加分层 bullet points，支持 bold/italic markdown。"""
    for idx, (text, level) in enumerate(flat_items):
        if idx == 0:
            paragraph = text_frame.paragraphs[0]
        else:
            paragraph = text_frame.add_paragraph()
            paragraph.level = level
        _format_text(paragraph, text)


def _markdown_to_bullet_items(text):
    """将 markdown 文本转为嵌套 bullet items 列表。

    支持：## 标题, ### 子标题, - 列表项, 普通文本
    返回可被 _get_flat_list() 展平的嵌套列表。
    """
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("## "):
            items.append("**" + line[3:] + "**")
        elif line.startswith("### "):
            items.append(["**" + line[4:] + "**"])
        elif line.startswith("- "):
            items.append([line[2:]])
        elif line.startswith("  - "):
            items.append([[line[4:]]])
        else:
            items.append(line)
    return items


# ============================================================
# Matplotlib font & style helpers
# ============================================================

def _setup_chinese_font():
    """配置 Matplotlib 中文字体。"""
    candidates = [
        "WenQuanYi Zen Hei", "Noto Sans CJK SC",
        "Microsoft YaHei", "SimHei", "PingFang SC",
    ]
    for name in candidates:
        try:
            path = fm.findfont(name, fallback_to_default=False)
            if path and "LastResort" not in path:
                plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
                return
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False


def _fig_to_image_stream(fig):
    """将 matplotlib figure 保存为 BytesIO PNG 流。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=CHART_DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _apply_thinkcell_style(ax):
    """应用 think-cell 风格：无顶/右边框，浅灰虚线网格。"""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#E0E0E0")
    ax.spines["bottom"].set_color("#E0E0E0")
    ax.grid(axis="x", color="#E0E0E0", linestyle="--", alpha=0.5, linewidth=0.5)
    ax.grid(axis="y", visible=False)
    ax.tick_params(colors="#555", labelsize=10)
    ax.set_axisbelow(True)


# ============================================================
# Chart functions (think-cell style)
# ============================================================

def _chart_sentiment_pie(df):
    """情感分布环形图。"""
    if df is None or len(df) == 0:
        return None
    counts = df["sentiment"].value_counts()
    labels_map = {"positive": "正面", "negative": "负面",
                  "neutral": "中性", "mixed": "混合"}
    labels = [labels_map.get(s, s) for s in counts.index]
    colors = [CHART_COLORS.get(s, "#999") for s in counts.index]

    fig, ax = plt.subplots(figsize=(6, 5))
    total = sum(counts.values)
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=labels, colors=colors,
        autopct=lambda pct: f"{pct:.1f}%\n({int(round(pct / 100 * total))})",
        startangle=90, pctdistance=0.75,
        textprops={"fontsize": 11},
        wedgeprops={"width": 0.4, "edgecolor": "white", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("评论情感分布", fontsize=14, fontweight="bold", pad=20)
    ax.text(0, 0, f"{total:,}\n条评论", ha="center", va="center",
            fontsize=16, fontweight="bold", color="#333")
    return fig


def _chart_sentiment_by_video(df, videos):
    """各视频情感堆叠水平条形图。"""
    if df is None or len(df) == 0 or not videos:
        return None
    vid_to_channel = {v["video_id"]: v["channel"][:18] for v in videos}
    df_filtered = df[df["video_id"].isin(vid_to_channel)]
    if len(df_filtered) == 0:
        return None

    cross = pd.crosstab(df_filtered["video_id"], df_filtered["sentiment"])
    cross_pct = cross.div(cross.sum(axis=1), axis=0) * 100
    vid_order = [v["video_id"] for v in videos if v["video_id"] in cross_pct.index]
    cross_pct = cross_pct.reindex(vid_order)
    channel_names = [vid_to_channel.get(v, v[:10]) for v in cross_pct.index]

    fig, ax = plt.subplots(figsize=(9, max(4, len(channel_names) * 0.45)))
    bottom = pd.Series(0.0, index=cross_pct.index)
    for sentiment in ["positive", "neutral", "mixed", "negative"]:
        if sentiment not in cross_pct.columns:
            continue
        lmap = {"positive": "正面", "negative": "负面",
                "neutral": "中性", "mixed": "混合"}
        vals = cross_pct[sentiment]
        bars = ax.barh(channel_names, vals, left=bottom, height=0.6,
                       color=CHART_COLORS.get(sentiment, "#999"),
                       label=lmap.get(sentiment, sentiment),
                       edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            if val > 10:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val:.0f}%", ha="center", va="center",
                        fontsize=8, color="white", fontweight="bold")
        bottom += vals

    ax.set_xlabel("评论占比 (%)", fontsize=11)
    ax.set_title("各视频评论情感分布", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    ax.invert_yaxis()
    _apply_thinkcell_style(ax)
    ax.grid(axis="x", visible=True)
    fig.tight_layout()
    return fig


def _chart_top_topics(df, top_n=12):
    """话题热度水平条形图。"""
    if df is None or len(df) == 0:
        return None
    topic_counter = Counter()
    for topics in df["topics"]:
        if isinstance(topics, list):
            topic_counter.update(topics)
        elif isinstance(topics, str) and topics:
            for t in topics.strip("[]").replace("'", "").split(","):
                t = t.strip()
                if t:
                    topic_counter[t] += 1
    if not topic_counter:
        return None

    top = topic_counter.most_common(top_n)
    labels = [TOPIC_DISPLAY.get(t, t) for t, _ in top]
    values = [c for _, c in top]

    fig, ax = plt.subplots(figsize=(9, max(4, len(labels) * 0.4)))
    bars = ax.barh(labels, values, color=CHART_COLORS["primary"],
                   height=0.6, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("提及次数", fontsize=11)
    ax.set_title(f"用户关注话题 Top {len(top)}", fontsize=14, fontweight="bold")
    ax.invert_yaxis()
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.02,
                bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, color="#555", fontweight="bold")
    _apply_thinkcell_style(ax)
    fig.tight_layout()
    return fig


def _chart_reviewer_stance(llm_results):
    """评测者态度环形图。"""
    stance_counts = {"推荐": 0, "中性/有保留": 0, "不推荐": 0}
    positive_kw = ["推荐", "值得", "优秀", "出色", "recommend", "impressed",
                   "worth", "excellent", "great"]
    negative_kw = ["不推荐", "失望", "不值", "问题多", "disappoint",
                   "not recommend", "avoid"]
    for _vid, result in llm_results.items():
        text = result.get("transcript", {}).get("analysis_text", "")
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
    colors = [CHART_COLORS["positive"], CHART_COLORS["mixed"], CHART_COLORS["negative"]]
    total = sum(values)

    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct=lambda pct: f"{pct:.0f}%\n({int(round(pct / 100 * total))}个)",
        startangle=90, pctdistance=0.75,
        textprops={"fontsize": 11},
        wedgeprops={"width": 0.4, "edgecolor": "white", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("评测者态度分布", fontsize=14, fontweight="bold", pad=20)
    ax.text(0, 0, f"{total}\n个视频", ha="center", va="center",
            fontsize=16, fontweight="bold", color="#333")
    return fig


def _chart_view_count_bar(videos):
    """视频观看量排名条形图。"""
    if not videos:
        return None
    sorted_vids = sorted(videos, key=lambda v: v.get("view_count", 0),
                         reverse=True)[:15]
    channels = [v["channel"][:18] for v in sorted_vids]
    views = [v.get("view_count", 0) for v in sorted_vids]
    colors = []
    for v in sorted_vids:
        if v.get("sponsor_status", {}).get("is_sponsored"):
            colors.append(CHART_COLORS["mixed"])
        else:
            colors.append(CHART_COLORS["primary"])

    fig, ax = plt.subplots(figsize=(9, max(4, len(channels) * 0.4)))
    bars = ax.barh(channels, views, color=colors, height=0.6,
                   edgecolor="white", linewidth=0.5)
    ax.set_xlabel("观看量", fontsize=11)
    ax.set_title("视频观看量排名", fontsize=14, fontweight="bold")
    ax.invert_yaxis()
    for bar, val in zip(bars, views):
        ax.text(bar.get_width() + max(views) * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=9, color="#555")
    _apply_thinkcell_style(ax)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=CHART_COLORS["primary"], label="非赞助"),
        Patch(facecolor=CHART_COLORS["mixed"], label="赞助/样机"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9, frameon=False)
    fig.tight_layout()
    return fig


def _chart_exec_summary_stats(text):
    """从执行摘要提取 X/Y 统计，生成水平条形图。"""
    if not text:
        return None
    # 匹配 "26/30 (86.7%)" 及其后面的上下文标签
    pattern = r'(\d+)/(\d+)\s*\([\d.]+%\)\s*[的]?([^\n,，。]{2,30})'
    matches = re.findall(pattern, text)
    if len(matches) < 2:
        return None

    labels = []
    values = []
    totals = []
    for num, denom, context in matches:
        label = context.strip().rstrip("。，,.")
        if len(label) > 20:
            label = label[:20] + "…"
        labels.append(label)
        values.append(int(num))
        totals.append(int(denom))

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(9, max(3, len(labels) * 0.5)))
    total = totals[0] if totals else 30
    pcts = [v / total * 100 for v in values]
    colors = []
    for v, t in zip(values, totals):
        ratio = v / t if t else 0
        if ratio >= 0.6:
            colors.append(CHART_COLORS["positive"])
        elif ratio >= 0.3:
            colors.append(CHART_COLORS["primary"])
        else:
            colors.append(CHART_COLORS["mixed"])

    bars = ax.barh(labels, pcts, color=colors, height=0.5,
                   edgecolor="white", linewidth=0.5)
    ax.set_xlim(0, 105)
    ax.set_xlabel("视频占比 (%)", fontsize=11)
    ax.set_title("核心发现一览", fontsize=14, fontweight="bold")
    ax.invert_yaxis()

    for bar, val, total_val in zip(bars, values, totals):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{val}/{total_val}", va="center", fontsize=10, color="#555",
                fontweight="bold")

    _apply_thinkcell_style(ax)
    fig.tight_layout()
    return fig


def _build_video_opinion_table(top_videos, llm_results):
    """构建各频道对 U1 评价的结构化表格数据。"""
    positive_kw = ["推荐", "值得", "优秀", "出色", "recommend", "impressed",
                   "worth", "excellent", "great"]
    negative_kw = ["不推荐", "失望", "不值", "问题多", "disappoint",
                   "not recommend", "avoid"]

    rows = []
    for v in top_videos:
        vid = v["video_id"]
        lr = llm_results.get(vid, {})
        ta_text = lr.get("transcript", {}).get("analysis_text", "")
        if not ta_text:
            continue

        channel = v["channel"][:18]

        # 提取视频类型
        overview = _extract_section(ta_text, [
            r"视频概述", r"U1 相关度", r"Overview",
        ])
        video_type = "专题评测"
        if overview:
            for kw in ["多产品", "对比", "盘点", "年度", "综合"]:
                if kw in overview:
                    video_type = "多产品对比"
                    break

        # 判断态度
        snippet = ta_text[:600].lower()
        has_pos = any(kw in snippet for kw in positive_kw)
        has_neg = any(kw in snippet for kw in negative_kw)
        if has_pos and not has_neg:
            stance = "推荐"
        elif has_neg and not has_pos:
            stance = "不推荐"
        else:
            stance = "有保留"

        # 提取核心理由（取前 80 字）
        conclusion = _extract_section(ta_text, [
            r"核心结论", r"Core Conclusion", r"总体评价",
        ])
        reason = ""
        if conclusion:
            reason = conclusion[:80].replace("\n", " ").strip()
            if len(conclusion) > 80:
                reason += "…"

        rows.append([channel, video_type, stance, reason])

    return {"headers": ["频道", "视频类型", "推荐态度", "核心理由"], "rows": rows}


# ============================================================
# Markdown table parser
# ============================================================

def _parse_markdown_table(text):
    """
    从文本中解析 markdown 管道表格。
    返回 list of {"headers": [...], "rows": [[...], ...]}
    """
    tables = []
    lines = text.split("\n")
    i = 0

    def parse_row(row_line):
        cells = row_line.split("|")
        if cells and cells[0].strip() == "":
            cells = cells[1:]
        if cells and cells[-1].strip() == "":
            cells = cells[:-1]
        return [c.strip() for c in cells]

    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|") or line.count("|") < 3:
            i += 1
            continue

        table_lines = []
        while i < len(lines):
            ln = lines[i].strip()
            if ln.startswith("|") and ln.count("|") >= 2:
                table_lines.append(ln)
                i += 1
            else:
                break

        if len(table_lines) < 3:
            i += 1
            continue

        headers = parse_row(table_lines[0])
        start_row = 1
        if len(table_lines) > 1:
            sep_cells = parse_row(table_lines[1])
            if all(re.match(r'^[-:]+$', c) for c in sep_cells if c):
                start_row = 2

        rows = []
        for tl in table_lines[start_row:]:
            row = parse_row(tl)
            # 跳过全空或全 ** 的分组标题行
            if all(c.startswith("**") and c.endswith("**") or c == ""
                   for c in row):
                # 这是一个分组标题行，保留它
                pass
            while len(row) < len(headers):
                row.append("")
            rows.append(row[:len(headers)])

        if headers and rows:
            tables.append({"headers": headers, "rows": rows})

    return tables


def _split_text_and_tables(text):
    """
    将混合文本拆分为文字段和表格段。
    返回 [{"type": "text", "text": ...} | {"type": "table", "data": ...}]
    """
    lines = text.split("\n")
    segments = []
    current_text = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.count("|") >= 3:
            if current_text:
                t = "\n".join(current_text).strip()
                if t:
                    segments.append({"type": "text", "text": t})
                current_text = []

            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") \
                    and lines[i].strip().count("|") >= 2:
                table_lines.append(lines[i])
                i += 1

            table_text = "\n".join(table_lines)
            parsed = _parse_markdown_table(table_text)
            for tbl in parsed:
                segments.append({"type": "table", "data": tbl})
        else:
            current_text.append(lines[i])
            i += 1

    if current_text:
        t = "\n".join(current_text).strip()
        if t:
            segments.append({"type": "text", "text": t})

    return segments


# ============================================================
# Slide helper functions
# ============================================================

def _add_title_slide(prs, title, subtitle=""):
    """添加标题幻灯片（使用模板 Title Slide 布局）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE])
    slide.shapes.title.text = title
    for p in slide.shapes.title.text_frame.paragraphs:
        _set_paragraph_font(p)
    if subtitle and 1 in slide.placeholders:
        slide.placeholders[1].text = subtitle
        for p in slide.placeholders[1].text_frame.paragraphs:
            _set_paragraph_font(p)
    return slide


def _add_section_slide(prs, title):
    """添加章节分隔幻灯片（使用模板 Section Header 布局）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_SECTION])
    slide.shapes.title.text = title
    for p in slide.shapes.title.text_frame.paragraphs:
        _set_paragraph_font(p)
    return slide


def _add_metrics_slide(prs, title, metrics):
    """添加数据指标卡片幻灯片（适配宽屏模板）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_BLANK])

    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.3), Inches(11.7), Inches(0.6))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY
    _set_paragraph_font(p)

    n = len(metrics)
    usable_w = SLIDE_W - 1.6  # 左右各 0.8" 边距
    gap = 0.15
    card_width = (usable_w - gap * (n - 1)) / n
    for i, (label, value) in enumerate(metrics):
        left = Inches(0.8 + i * (card_width + gap))
        top = Inches(1.5)
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            left, top, Inches(card_width), Inches(2)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = COLOR_LIGHT_BG
        shape.line.color.rgb = COLOR_ACCENT

        tf = shape.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = str(value)
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(4)
        _set_paragraph_font(p)

        p2 = tf.add_paragraph()
        p2.text = label
        p2.font.size = Pt(12)
        p2.font.color.rgb = COLOR_NEUTRAL
        p2.alignment = PP_ALIGN.CENTER
        _set_paragraph_font(p2)

    return slide


def _add_chart_slide(prs, title, fig, subtitle=""):
    """添加图表幻灯片（使用模板 Title Only 布局）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE_ONLY])
    slide.shapes.title.text = title
    for p in slide.shapes.title.text_frame.paragraphs:
        _set_paragraph_font(p)

    chart_top = Inches(1.5)
    if subtitle:
        txBox = slide.shapes.add_textbox(
            Inches(0.8), Inches(1.1), Inches(11.7), Inches(0.4))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = subtitle
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_NEUTRAL
        _set_paragraph_font(p)
        chart_top = Inches(1.8)

    # 按 fig 原始尺寸计算缩放，确保不超出幻灯片边界
    fig_w, fig_h = fig.get_size_inches()
    image_stream = _fig_to_image_stream(fig)

    max_w, max_h = 11.5, 5.5
    if subtitle:
        max_h = 5.0
    scale = min(max_w / fig_w, max_h / fig_h, 1.0)
    target_w = fig_w * scale
    target_h = fig_h * scale
    left = (SLIDE_W - target_w) / 2  # 水平居中

    slide.shapes.add_picture(image_stream, Inches(left), chart_top,
                             width=Inches(target_w), height=Inches(target_h))
    return slide


def _add_native_table_slide(prs, title, table_data):
    """将解析后的 markdown 表格渲染为原生 PPTX 表格（适配宽屏模板）。"""
    headers = table_data["headers"]
    all_rows = table_data["rows"]
    n_cols = len(headers)
    max_rows_per_page = 10
    slides = []
    table_w = SLIDE_W - 0.8  # 左右各 0.4" 边距

    for page_start in range(0, len(all_rows), max_rows_per_page):
        page_rows = all_rows[page_start:page_start + max_rows_per_page]
        slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE_ONLY])
        slides.append(slide)

        total_pages = (len(all_rows) + max_rows_per_page - 1) // max_rows_per_page
        page_num = page_start // max_rows_per_page + 1
        slide_title = title if total_pages == 1 else f"{title}（{page_num}/{total_pages}）"

        slide.shapes.title.text = slide_title
        for p in slide.shapes.title.text_frame.paragraphs:
            _set_paragraph_font(p)

        n_data = len(page_rows)
        row_height = min(0.5, 6.0 / (n_data + 1))
        table_shape = slide.shapes.add_table(
            n_data + 1, n_cols,
            Inches(0.4), Inches(1.1),
            Inches(table_w), Inches(min(6.2, (n_data + 1) * row_height))
        )
        table = table_shape.table

        per_col = table_w / n_cols
        for j in range(n_cols):
            table.columns[j].width = Inches(per_col)

        # 表头
        for j, header in enumerate(headers):
            cell = table.cell(0, j)
            cell.text = header
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_PRIMARY
            for para in cell.text_frame.paragraphs:
                para.font.size = Pt(12)
                para.font.bold = True
                para.font.color.rgb = COLOR_WHITE
                _set_paragraph_font(para)

        # 数据行
        for i, row in enumerate(page_rows):
            for j, val in enumerate(row):
                cell = table.cell(i + 1, j)
                clean_val = str(val).replace("**", "")
                cell.text = clean_val
                if i % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = COLOR_ALT_ROW
                for para in cell.text_frame.paragraphs:
                    para.font.size = Pt(12)
                    para.font.color.rgb = COLOR_DARK
                    _set_paragraph_font(para)

    return slides


def _render_text_slides(prs, title, text, max_chars=900):
    """渲染纯文本内容幻灯片（使用模板 Content 布局 + SlideDeck AI 格式化）。"""
    slides = []
    text = text.strip()
    page = 0

    while text:
        page += 1
        slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_CONTENT])
        slides.append(slide)

        page_title = title if page == 1 else f"{title}（续{page}）"
        slide.shapes.title.text = page_title
        for p in slide.shapes.title.text_frame.paragraphs:
            _set_paragraph_font(p)

        chunk = text[:max_chars]
        text = text[max_chars:]

        if text:
            last_nl = chunk.rfind("\n\n")
            if last_nl > max_chars * 0.5:
                text = chunk[last_nl:] + text
                chunk = chunk[:last_nl]
            else:
                last_nl = chunk.rfind("\n")
                if last_nl > max_chars * 0.6:
                    text = chunk[last_nl:] + text
                    chunk = chunk[:last_nl]

        # 使用模板 Content 占位符 + SlideDeck AI 格式化
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.clear()
        tf.word_wrap = True

        items = _markdown_to_bullet_items(chunk)
        flat = _get_flat_list(items, 0)
        if flat:
            _add_bulleted_items(tf, flat)
        else:
            tf.paragraphs[0].text = chunk

        for p in tf.paragraphs:
            _set_paragraph_font(p)

    return slides


def _add_content_slide(prs, title, body_text, max_chars=900):
    """添加内容幻灯片，自动检测 markdown 表格并转为原生表格。"""
    slides = []
    segments = _split_text_and_tables(body_text)

    for seg in segments:
        if seg["type"] == "table":
            table_slides = _add_native_table_slide(prs, title, seg["data"])
            slides.extend(table_slides)
        else:
            text_slides = _render_text_slides(prs, title, seg["text"], max_chars)
            slides.extend(text_slides)

    return slides


def _add_video_table_slide(prs, videos, llm_results):
    """添加视频索引表格幻灯片（适配宽屏模板）。"""
    page_size = 8
    table_w = SLIDE_W - 0.8  # 左右各 0.4" 边距
    for page_start in range(0, len(videos), page_size):
        page_videos = videos[page_start:page_start + page_size]
        slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE_ONLY])

        page_num = page_start // page_size + 1
        total_pages = (len(videos) + page_size - 1) // page_size
        title = f"视频索引（{page_num}/{total_pages}）"

        slide.shapes.title.text = title
        for p in slide.shapes.title.text_frame.paragraphs:
            _set_paragraph_font(p)

        rows = len(page_videos) + 1
        cols = 5
        table = slide.shapes.add_table(
            rows, cols,
            Inches(0.4), Inches(1.1),
            Inches(table_w), Inches(min(6.2, rows * 0.6))
        ).table

        table.columns[0].width = Inches(0.5)
        table.columns[1].width = Inches(2.8)
        table.columns[2].width = Inches(5.5)
        table.columns[3].width = Inches(1.8)
        table.columns[4].width = Inches(1.9)

        headers = ["#", "频道", "标题", "观看量", "赞助状态"]
        for j, header in enumerate(headers):
            cell = table.cell(0, j)
            cell.text = header
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_PRIMARY
            for para in cell.text_frame.paragraphs:
                para.font.size = Pt(12)
                para.font.bold = True
                para.font.color.rgb = COLOR_WHITE
                _set_paragraph_font(para)

        for i, v in enumerate(page_videos):
            idx = page_start + i + 1
            sp_type = v.get("sponsor_status", {}).get("sponsor_type", "unknown")
            sp_map = {
                "sponsored": "赞助", "review_sample": "样机",
                "self_purchased": "自购", "affiliate_only": "联盟",
                "unknown": "-",
            }
            row_data = [
                str(idx),
                v["channel"][:25],
                v["title"][:60],
                f"{v['view_count']:,}",
                sp_map.get(sp_type, sp_type),
            ]
            for j, val in enumerate(row_data):
                cell = table.cell(i + 1, j)
                cell.text = val
                if i % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = COLOR_ALT_ROW
                for para in cell.text_frame.paragraphs:
                    para.font.size = Pt(12)
                    para.font.color.rgb = COLOR_DARK
                    _set_paragraph_font(para)


def _extract_section(text, header_patterns):
    """从 LLM Markdown 文本中按标题提取某个 section。"""
    if not text:
        return ""
    for pattern in header_patterns:
        regex = (
            r"##\s*(?:\d+[\.\s]*)?[^\n]*?" + pattern +
            r"[^\n]*\n(.*?)(?=\n##\s|\Z)"
        )
        match = re.search(regex, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


# ============================================================
# Main entry point
# ============================================================

def generate_pptx_report(
    top_videos,
    filter_stats,
    df_comments,
    llm_results,
    overall_llm,
    output_path,
):
    """
    生成 PowerPoint 产品分析报告。

    参数:
        top_videos: 视频列表 (list[dict])
        filter_stats: 管道统计 (dict)
        df_comments: 评论 DataFrame
        llm_results: {video_id: {transcript: {}, comments: {}}}
        overall_llm: 整体 LLM 分析 (dict)
        output_path: PPTX 输出路径
    """
    output_path = Path(output_path)
    template_path = _get_template_path()
    if template_path:
        prs = Presentation(template_path)
        logger.info(f"  使用 SlideDeck AI 模板: {template_path}")
    else:
        prs = Presentation()
        prs.slide_width = Inches(SLIDE_W)
        prs.slide_height = Inches(7.5)
        logger.warning("  未找到模板文件，使用空白演示文稿")

    _setup_chinese_font()

    overall_text = overall_llm.get("analysis_text", "") if overall_llm else ""
    total_comments = len(df_comments) if df_comments is not None else 0
    total_views = sum(v.get("view_count", 0) for v in top_videos)

    # ===== 封面 =====
    subtitle = (
        f"基于 {len(top_videos)} 个评测视频 & "
        f"{total_comments:,} 条用户评论的深度分析\n"
        f"生成日期: {pd.Timestamp.now().strftime('%Y-%m-%d')}"
    )
    _add_title_slide(prs, "YouTube 用户反馈分析报告", subtitle)

    # ===== 数据概览 =====
    transcript_success = sum(
        1 for v in top_videos
        if llm_results.get(v["video_id"], {})
           .get("transcript", {}).get("status") == "success"
    )
    _add_metrics_slide(prs, "数据概览", [
        ("评测视频", len(top_videos)),
        ("有效评论", f"{total_comments:,}"),
        ("总观看量", f"{total_views:,}"),
        ("字幕成功", transcript_success),
    ])

    # ===== 执行摘要 =====
    exec_summary = _extract_section(overall_text, [
        r"执行摘要", r"Executive Summary", r"摘要",
    ])
    if exec_summary:
        _add_content_slide(prs, "执行摘要", exec_summary)

        # 执行摘要统计图表
        fig = _chart_exec_summary_stats(exec_summary)
        if fig:
            _add_chart_slide(prs, "核心发现一览", fig,
                             subtitle="基于评测视频的关键统计数据")

    # ================================================================
    # 第一部分：评测视频全景
    # ================================================================
    _add_section_slide(prs, "第一部分：评测视频全景")

    # 视频观看量排名图表
    fig = _chart_view_count_bar(top_videos)
    if fig:
        _add_chart_slide(prs, "视频观看量排名", fig,
                         subtitle="按观看量降序排列，橙色标注赞助/样机视频")

    # 评测者态度图表
    fig = _chart_reviewer_stance(llm_results)
    if fig:
        _add_chart_slide(prs, "评测者推荐态度", fig,
                         subtitle="基于各视频核心结论的关键词分析")

    # 整体口碑评估（含表格自动检测）
    reputation = _extract_section(overall_text, [
        r"整体口碑", r"Overall Reputation", r"口碑评估",
    ])
    if reputation:
        _add_content_slide(prs, "整体口碑评估", reputation)

    # ================================================================
    # 第二部分：优缺点分析
    # ================================================================
    _add_section_slide(prs, "第二部分：优缺点分析")

    strengths = _extract_section(overall_text, [
        r"优点", r"亮点", r"Strengths",
    ])
    if strengths:
        _add_content_slide(prs, "优点/亮点统计", strengths)

    issues = _extract_section(overall_text, [
        r"缺点", r"问题", r"Issues",
    ])
    if issues:
        _add_content_slide(prs, "缺点/问题统计", issues)

    improvements = _extract_section(overall_text, [
        r"改进", r"Improvement",
    ])
    if improvements:
        _add_content_slide(prs, "核心改进方向", improvements)

    # ================================================================
    # 第三部分：Snapmaker U1 vs Bambu Lab 深度对比
    # ================================================================
    _add_section_slide(prs, "第三部分：Snapmaker U1 vs Bambu Lab")

    bambu = _extract_section(overall_text, [
        r"Bambu", r"竞品", r"Competitive",
    ])
    if bambu:
        _add_content_slide(prs, "U1 vs Bambu Lab 深度对比", bambu)

    # 补充：从各视频提取 Bambu 对比要点
    bambu_per_video = []
    for v in top_videos:
        vid = v["video_id"]
        ta_text = llm_results.get(vid, {}).get("transcript", {}).get("analysis_text", "")
        if not ta_text:
            continue
        bambu_cmp = _extract_section(ta_text, [r"Bambu", r"竞品对比"])
        if bambu_cmp and len(bambu_cmp) > 50:
            bambu_per_video.append(
                f"### {v['channel'][:20]}\n{bambu_cmp[:400]}"
            )

    if bambu_per_video:
        for i in range(0, len(bambu_per_video), 2):
            batch = "\n\n".join(bambu_per_video[i:i + 2])
            _add_content_slide(
                prs,
                f"各视频 Bambu 对比详情（{i // 2 + 1}）",
                batch,
            )

    # ================================================================
    # 第四部分：综合测评视频中对 U1 的观点（表格形式）
    # ================================================================
    _add_section_slide(prs, "第四部分：综合测评视频对 U1 的观点")

    opinion_table = _build_video_opinion_table(top_videos, llm_results)
    if opinion_table["rows"]:
        _add_native_table_slide(prs, "各频道对 U1 的评价", opinion_table)

    # ================================================================
    # 第五部分：与其他竞品对比
    # ================================================================
    other_cmp = _extract_section(overall_text, [
        r"其他竞品", r"Other Competitor",
    ])
    if other_cmp:
        _add_section_slide(prs, "第五部分：与其他竞品对比")
        _add_content_slide(prs, "与 Prusa / Creality 等竞品对比", other_cmp)

        # 从 per-video 补充
        other_per_video = []
        for v in top_videos:
            vid = v["video_id"]
            ta_text = llm_results.get(vid, {}).get(
                "transcript", {}).get("analysis_text", "")
            if not ta_text:
                continue
            other_sec = _extract_section(ta_text, [
                r"其他竞品", r"Other Competitor",
            ])
            if other_sec and len(other_sec) > 50:
                other_per_video.append(
                    f"### {v['channel'][:20]}\n{other_sec[:400]}"
                )

        if other_per_video:
            for i in range(0, len(other_per_video), 2):
                batch = "\n\n".join(other_per_video[i:i + 2])
                _add_content_slide(
                    prs,
                    f"各视频竞品对比详情（{i // 2 + 1}）",
                    batch,
                )

    # ================================================================
    # 第六部分：观点共识与市场洞察
    # ================================================================
    consensus = _extract_section(overall_text, [
        r"一致性", r"分歧", r"Consensus", r"Disagreement",
    ])
    market = _extract_section(overall_text, [
        r"市场", r"机会", r"风险", r"Market",
    ])
    if consensus or market:
        _add_section_slide(prs, "第六部分：观点共识与市场洞察")
        if consensus:
            _add_content_slide(prs, "评测者观点一致性与分歧", consensus)
        if market:
            _add_content_slide(prs, "市场机会与风险", market)

    # ================================================================
    # 第七部分：用户评论分析
    # ================================================================
    _add_section_slide(prs, "第七部分：用户评论分析")

    # 情感饼图
    fig = _chart_sentiment_pie(df_comments)
    if fig:
        _add_chart_slide(prs, "评论情感分布", fig,
                         subtitle=f"基于 {total_comments:,} 条有效评论的关键词情感分析")

    # 各视频情感堆叠图
    fig = _chart_sentiment_by_video(df_comments, top_videos)
    if fig:
        _add_chart_slide(prs, "各视频评论情感分布", fig)

    # 话题热度图
    fig = _chart_top_topics(df_comments)
    if fig:
        _add_chart_slide(prs, "用户关注话题频率", fig)

    # 情感统计文本
    if df_comments is not None and len(df_comments) > 0:
        counts = df_comments["sentiment"].value_counts()
        sentiment_text = f"总有效评论: {total_comments} 条\n\n"
        label_map = {"positive": "正面", "negative": "负面",
                     "neutral": "中性", "mixed": "混合"}
        for s in ["positive", "neutral", "negative", "mixed"]:
            c = counts.get(s, 0)
            pct = round(c / total_comments * 100, 1) if total_comments else 0
            sentiment_text += f"- {label_map.get(s, s)}: {c} 条 ({pct}%)\n"
        _add_content_slide(prs, "评论情感统计", sentiment_text)

    # LLM 评论分析汇总
    comment_highlights = []
    for v in top_videos:
        vid = v["video_id"]
        ca = llm_results.get(vid, {}).get("comments", {})
        ca_text = ca.get("analysis_text", "")
        if ca_text and ca.get("status") == "success":
            comment_highlights.append(
                f"### {v['channel'][:20]} - {v['title'][:30]}\n"
                f"{ca_text[:500]}..."
            )

    if comment_highlights:
        for i in range(0, len(comment_highlights), 2):
            batch = "\n\n---\n\n".join(comment_highlights[i:i + 2])
            _add_content_slide(
                prs,
                f"评论分析详情（{i // 2 + 1}）",
                batch,
            )

    # ================================================================
    # 附录：视频索引
    # ================================================================
    _add_section_slide(prs, "附录：视频索引")
    _add_video_table_slide(prs, top_videos, llm_results)

    # ===== 保存 =====
    prs.save(str(output_path))
    size_kb = output_path.stat().st_size / 1024
    logger.info(f"  PowerPoint 报告已生成: {output_path} ({size_kb:.0f} KB)")
    return output_path
