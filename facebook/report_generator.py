"""
Snapmaker U1 Facebook 用户反馈分析 PPTX 报告生成器

输出语言：简体中文（用户原文以括号标注英文原文）
中文字体：等线 (DengXian)
英文字体：Calibri
"""

import io
import os
from collections import Counter
from typing import Dict, List, Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ── 颜色方案 ─────────────────────────────────────────────────────
DARK_BLUE = RGBColor(0x1B, 0x3A, 0x5C)
ORANGE = RGBColor(0xE8, 0x73, 0x2A)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_DARK = RGBColor(0x33, 0x33, 0x33)
TEXT_LIGHT = RGBColor(0x66, 0x66, 0x66)
ACCENT_GREEN = RGBColor(0x27, 0xAE, 0x60)
ACCENT_RED = RGBColor(0xE7, 0x4C, 0x3C)
ACCENT_YELLOW = RGBColor(0xF3, 0x9C, 0x12)

# Matplotlib 颜色
MPL_DARK_BLUE = "#1B3A5C"
MPL_ORANGE = "#E8732A"
MPL_LIGHT_BLUE = "#3498DB"
MPL_GREEN = "#27AE60"
MPL_RED = "#E74C3C"
MPL_PURPLE = "#9B59B6"
MPL_TEAL = "#1ABC9C"
MPL_YELLOW = "#F39C12"
MPL_GRAY = "#95A5A6"
MPL_PINK = "#E91E63"

CHART_COLORS = [
    MPL_DARK_BLUE, MPL_ORANGE, MPL_LIGHT_BLUE, MPL_GREEN,
    MPL_RED, MPL_PURPLE, MPL_TEAL, MPL_YELLOW,
    MPL_GRAY, MPL_PINK,
]

# 主贴五分类颜色
PRIMARY_CAT_COLORS = {
    "问题/求助": MPL_ORANGE,
    "打印结果展示/晒作品": MPL_LIGHT_BLUE,
    "正面反馈": MPL_GREEN,
    "负面反馈": MPL_RED,
    "其他内容": MPL_GRAY,
}

PRIMARY_CAT_EN = {
    "问题/求助": "Questions / Help",
    "打印结果展示/晒作品": "Print Showcase",
    "正面反馈": "Positive Feedback",
    "负面反馈": "Negative Feedback",
    "其他内容": "Other Content",
}

SENTIMENT_COLORS = {
    "positive": MPL_GREEN,
    "negative": MPL_RED,
    "neutral": MPL_GRAY,
    "mixed": MPL_YELLOW,
}

# 字体名称
FONT_ZH = "DengXian"  # 等线
FONT_EN = "Calibri"


def _setup_matplotlib():
    """配置 matplotlib 默认设置。"""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#CCCCCC",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.color": "#CCCCCC",
        "font.size": 11,
    })
    # 尝试设置支持中文的字体
    for font in ["DengXian", "Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]:
        try:
            plt.rcParams["font.sans-serif"] = [font, "Calibri", "DejaVu Sans"]
            break
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False


class ReportGenerator:
    """生成 PPTX 分析报告。"""

    def __init__(self, analysis_data: Dict[str, Any]):
        self.data = analysis_data
        self.posts = analysis_data.get("posts", [])
        self.summary = analysis_data.get("summary", {})
        self.metadata = analysis_data.get("metadata", {})
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        _setup_matplotlib()

    # ── 基础工具方法 ──────────────────────────────────────────────

    def _add_blank_slide(self):
        layout = self.prs.slide_layouts[6]  # Blank
        return self.prs.slides.add_slide(layout)

    def _add_title_bar(self, slide, title_text: str, page_num: int = None):
        """添加顶部深蓝色标题栏。"""
        left, top = Inches(0), Inches(0)
        width, height = self.prs.slide_width, Inches(0.9)
        shape = slide.shapes.add_shape(1, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = DARK_BLUE
        shape.line.fill.background()

        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(10), Inches(0.65))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.font.name = FONT_ZH

        if page_num is not None:
            pn_box = slide.shapes.add_textbox(
                self.prs.slide_width - Inches(1.5), Inches(0.15),
                Inches(1.2), Inches(0.6)
            )
            pn_p = pn_box.text_frame.paragraphs[0]
            pn_p.text = str(page_num)
            pn_p.alignment = PP_ALIGN.RIGHT
            pn_p.font.size = Pt(14)
            pn_p.font.color.rgb = RGBColor(0xAA, 0xBB, 0xCC)
            pn_p.font.name = FONT_EN

    def _add_text_box(self, slide, left, top, width, height, text,
                      font_size=14, bold=False, color=TEXT_DARK,
                      alignment=PP_ALIGN.LEFT, font_name=None):
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(font_size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.font.name = font_name or FONT_ZH
        p.alignment = alignment
        return txBox

    def _add_bullet_list(self, slide, left, top, width, height, items,
                         font_size=13, color=TEXT_DARK):
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True

        for i, item in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = f"• {item}"
            p.font.size = Pt(font_size)
            p.font.color.rgb = color
            p.font.name = FONT_ZH
            p.space_after = Pt(4)

        return txBox

    def _fig_to_image(self, fig) -> io.BytesIO:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        buf.seek(0)
        plt.close(fig)
        return buf

    def _add_chart_image(self, slide, fig, left, top, width, height=None):
        buf = self._fig_to_image(fig)
        if height is None:
            slide.shapes.add_picture(buf, left, top, width=width)
        else:
            slide.shapes.add_picture(buf, left, top, width=width, height=height)

    # ── 图表工具 ─────────────────────────────────────────────────

    def _make_pie_chart(self, labels, values, title="", colors=None, figsize=(5, 5)):
        fig, ax = plt.subplots(figsize=figsize)
        if colors is None:
            colors = CHART_COLORS[:len(labels)]

        filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
        if not filtered:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=14)
            return fig
        labels_f, values_f, colors_f = zip(*filtered)

        wedges, texts, autotexts = ax.pie(
            values_f, labels=labels_f, colors=colors_f,
            autopct=lambda pct: f"{pct:.1f}%" if pct > 3 else "",
            startangle=90, pctdistance=0.75,
            textprops={"fontsize": 10}
        )
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color("white")
            autotext.set_fontweight("bold")

        if title:
            ax.set_title(title, fontsize=13, fontweight="bold", color=MPL_DARK_BLUE, pad=12)

        fig.tight_layout()
        return fig

    def _make_horizontal_bar(self, labels, values, title="", colors=None,
                             figsize=(8, 5), value_fmt="{:.0f}"):
        fig, ax = plt.subplots(figsize=figsize)
        y_pos = range(len(labels))
        bar_colors = colors if colors else [MPL_DARK_BLUE] * len(labels)
        if isinstance(bar_colors, str):
            bar_colors = [bar_colors] * len(labels)

        bars = ax.barh(y_pos, values, color=bar_colors, height=0.6, edgecolor="white")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=10)
        ax.invert_yaxis()
        ax.set_xlabel("数量", fontsize=11)
        if title:
            ax.set_title(title, fontsize=13, fontweight="bold", color=MPL_DARK_BLUE, pad=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max_val * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    value_fmt.format(val), va="center", fontsize=10, color=MPL_DARK_BLUE)

        fig.tight_layout()
        return fig

    def _make_bar_chart(self, labels, values, title="", colors=None, figsize=(7, 5)):
        fig, ax = plt.subplots(figsize=figsize)
        if colors is None:
            colors = [MPL_DARK_BLUE] * len(labels)
        x_pos = range(len(labels))
        bars = ax.bar(x_pos, values, color=colors, width=0.6, edgecolor="white")
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=9, rotation=20, ha="right")
        ax.set_ylabel("数量", fontsize=11)
        if title:
            ax.set_title(title, fontsize=13, fontweight="bold", color=MPL_DARK_BLUE, pad=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max_val * 0.02,
                    str(int(val)), ha="center", fontsize=10, color=MPL_DARK_BLUE)

        fig.tight_layout()
        return fig

    # ── 幻灯片构建 ───────────────────────────────────────────────

    def _build_cover_slide(self):
        """封面页。"""
        slide = self._add_blank_slide()

        # 深蓝色背景
        shape = slide.shapes.add_shape(1, Inches(0), Inches(0),
                                       self.prs.slide_width, self.prs.slide_height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = DARK_BLUE
        shape.line.fill.background()

        # 橙色装饰线
        shape2 = slide.shapes.add_shape(1, Inches(0.8), Inches(3.4),
                                        Inches(4), Inches(0.06))
        shape2.fill.solid()
        shape2.fill.fore_color.rgb = ORANGE
        shape2.line.fill.background()

        # 标题
        self._add_text_box(slide, Inches(0.8), Inches(1.0), Inches(11), Inches(1.2),
                           "Snapmaker U1", font_size=44, bold=True, color=WHITE,
                           font_name=FONT_EN)
        self._add_text_box(slide, Inches(0.8), Inches(2.2), Inches(11), Inches(1),
                           "Facebook 用户反馈分析报告",
                           font_size=28, bold=True, color=RGBColor(0xCC, 0xDD, 0xEE))

        # 副标题
        total_posts = self.metadata.get("total_posts", 0)
        total_comments = self.metadata.get("total_comments", 0)
        group_name = self.metadata.get("group_name", "Snapmaker U1 Official Group")
        extraction_time = self.metadata.get("extraction_time", "")
        llm_tag = "  |  LLM 增强分析" if self.metadata.get("llm_enabled") else ""

        subtitle = f"数据来源 (Data Source): {group_name}\n"
        subtitle += f"帖子总数 (Total Posts): {total_posts}  |  评论总数 (Total Comments): {total_comments}{llm_tag}\n"
        if extraction_time:
            date_part = extraction_time[:10] if len(extraction_time) >= 10 else extraction_time
            subtitle += f"数据采集时间 (Extraction Date): {date_part}"

        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(3.8), Inches(10), Inches(2))
        tf = txBox.text_frame
        tf.word_wrap = True
        for i, line in enumerate(subtitle.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.size = Pt(16)
            p.font.color.rgb = RGBColor(0xAA, 0xBB, 0xCC)
            p.font.name = FONT_ZH
            p.space_after = Pt(4)

    def _build_overview(self, page_num: int):
        """第一章：数据概览。"""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "第一章：数据概览 (Data Overview)", page_num)

        stats = self.summary.get("basic_stats", {})
        cards = [
            ("帖子总数\n(Total Posts)", str(stats.get("total_posts", 0))),
            ("评论总数\n(Total Comments)", str(stats.get("total_comments", 0))),
            ("独立作者数\n(Unique Authors)", str(stats.get("unique_authors", 0))),
            ("平均反应数\n(Avg Reactions)", f"{stats.get('avg_reactions', 0):.1f}"),
            ("平均评论数\n(Avg Comments)", f"{stats.get('avg_comment_count', 0):.1f}"),
        ]

        for i, (label, value) in enumerate(cards):
            col = i % 5
            left = Inches(0.5 + col * 2.5)
            top = Inches(1.3)

            card = slide.shapes.add_shape(1, left, top, Inches(2.2), Inches(1.5))
            card.fill.solid()
            card.fill.fore_color.rgb = RGBColor(0xEC, 0xF0, 0xF1)
            card.line.fill.background()

            self._add_text_box(slide, left + Inches(0.1), top + Inches(0.1),
                               Inches(2.0), Inches(0.7),
                               value, font_size=28, bold=True, color=DARK_BLUE,
                               alignment=PP_ALIGN.CENTER, font_name=FONT_EN)
            self._add_text_box(slide, left + Inches(0.1), top + Inches(0.8),
                               Inches(2.0), Inches(0.6),
                               label, font_size=10, color=TEXT_LIGHT,
                               alignment=PP_ALIGN.CENTER)

        # 帖子类型饼图
        type_labels = ["纯文本 (Text Only)", "含图片 (With Images)", "含视频 (With Videos)"]
        type_values = [
            stats.get("posts_text_only", 0),
            stats.get("posts_with_images", 0),
            stats.get("posts_with_videos", 0),
        ]
        fig = self._make_pie_chart(type_labels, type_values,
                                   title="帖子类型分布 (Post Type Distribution)",
                                   colors=[MPL_GRAY, MPL_LIGHT_BLUE, MPL_ORANGE],
                                   figsize=(4.5, 4.5))
        self._add_chart_image(slide, fig, Inches(0.5), Inches(3.2), Inches(5), Inches(4))

        # 高互动帖子
        top_posts = self.summary.get("top_engagement_posts", [])
        if top_posts:
            self._add_text_box(slide, Inches(6), Inches(3.2), Inches(6.5), Inches(0.4),
                               "高互动帖子 TOP10 (Top Engagement Posts)",
                               font_size=14, bold=True, color=DARK_BLUE)

            items = []
            for tp in top_posts[:10]:
                truncated = (tp.get("text", "") or "")[:80]
                if len(tp.get("text", "") or "") > 80:
                    truncated += "..."
                cat = tp.get("primary_category", "")
                items.append(f"[{tp.get('reactions', 0)}反应] [{cat}] {truncated}")

            self._add_bullet_list(slide, Inches(6), Inches(3.8), Inches(6.8), Inches(3.5),
                                  items, font_size=9, color=TEXT_DARK)

    def _build_primary_classification(self, page_num: int):
        """第二章：主贴五分类总览。"""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "第二章：主贴分类总览 (Post Classification)", page_num)

        primary_dist = self.summary.get("primary_distribution", {})
        total = sum(primary_dist.values())

        # 饼图
        labels = []
        values = []
        colors = []
        for cat in PRIMARY_CAT_EN:
            count = primary_dist.get(cat, 0)
            en_name = PRIMARY_CAT_EN[cat]
            pct = count / max(total, 1) * 100
            labels.append(f"{cat}\n({en_name})\n{count}个 ({pct:.1f}%)")
            values.append(count)
            colors.append(PRIMARY_CAT_COLORS.get(cat, MPL_GRAY))

        fig = self._make_pie_chart(labels, values,
                                   title="主贴分类分布 (Post Classification Distribution)",
                                   colors=colors, figsize=(6, 6))
        self._add_chart_image(slide, fig, Inches(0.3), Inches(1.1), Inches(6.5), Inches(6))

        # 右侧统计
        self._add_text_box(slide, Inches(7.2), Inches(1.3), Inches(5.5), Inches(0.4),
                           "分类统计 (Classification Statistics)",
                           font_size=16, bold=True, color=DARK_BLUE)

        y = Inches(2.0)
        for cat in PRIMARY_CAT_EN:
            count = primary_dist.get(cat, 0)
            pct = count / max(total, 1) * 100
            en_name = PRIMARY_CAT_EN[cat]

            marker = slide.shapes.add_shape(1, Inches(7.2), y + Inches(0.05),
                                            Inches(0.3), Inches(0.3))
            marker.fill.solid()
            hex_color = PRIMARY_CAT_COLORS.get(cat, MPL_GRAY).lstrip("#")
            marker.fill.fore_color.rgb = RGBColor(
                int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            )
            marker.line.fill.background()

            self._add_text_box(slide, Inches(7.7), y, Inches(5), Inches(0.4),
                               f"{cat} ({en_name}): {count} 个帖子 ({pct:.1f}%)",
                               font_size=12, color=TEXT_DARK)
            y += Inches(0.45)

        # 分析方法说明
        self._add_text_box(slide, Inches(7.2), y + Inches(0.3), Inches(5.5), Inches(0.4),
                           "分析方法 (Methodology)", font_size=14, bold=True, color=DARK_BLUE)
        method = "LLM 增强分类 (Qwen)" if self.metadata.get("llm_enabled") else "关键词规则分类 (Keyword-based)"
        self._add_text_box(slide, Inches(7.2), y + Inches(0.8), Inches(5.5), Inches(0.6),
                           f"分类方法 (Method): {method}\n帖子总数 (Total): {total}",
                           font_size=11, color=TEXT_LIGHT)

    def _build_subcategory_analysis(self, slide_title: str, subcategories: dict,
                                    quotes: list, chart_color: str,
                                    title_color, page_num: int) -> int:
        """通用子分类分析页：条形图 + 饼图 + 用户原声。"""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, slide_title, page_num)

        if not subcategories:
            self._add_text_box(slide, Inches(0.5), Inches(2), Inches(10), Inches(1),
                               "暂无数据 (No data available)",
                               font_size=16, color=TEXT_LIGHT)
            return page_num

        # 子分类条形图
        labels = list(subcategories.keys())[:12]
        values = [subcategories[k]["count"] for k in labels]
        total = sum(values)

        colors_list = CHART_COLORS[:len(labels)]
        fig = self._make_horizontal_bar(
            labels, values,
            title="子分类分布 (Sub-category Distribution)",
            colors=colors_list,
            figsize=(7, max(3, len(labels) * 0.55))
        )
        self._add_chart_image(slide, fig, Inches(0.3), Inches(1.1),
                              Inches(6.5), Inches(5.8))

        # 饼图
        pie_labels = [f"{l}\n({v})" for l, v in zip(labels[:8], values[:8])]
        fig2 = self._make_pie_chart(
            pie_labels, values[:8],
            title="占比分布 (Proportion)",
            colors=colors_list[:8], figsize=(4, 4)
        )
        self._add_chart_image(slide, fig2, Inches(7), Inches(1.1), Inches(4.5), Inches(4.5))

        # 量化统计
        self._add_text_box(slide, Inches(7), Inches(5.8), Inches(5.5), Inches(0.4),
                           f"共 {total} 个帖子, {len(subcategories)} 个子类别",
                           font_size=11, color=TEXT_LIGHT)

        # 用户原声页
        return self._build_quotes_page(
            slide_title.split("(")[0].strip() + " - 用户原声 (User Voices)",
            subcategories, quotes, title_color, page_num + 1
        )

    def _build_quotes_page(self, slide_title: str, subcategories: dict,
                           quotes: list, title_color, page_num: int) -> int:
        """用户原声展示页。"""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, slide_title, page_num)

        y = Inches(1.2)

        # 每个子类别的代表性原声
        shown = 0
        for cat_name, cat_data in subcategories.items():
            if shown >= 4:
                break
            cat_quotes = cat_data.get("quotes", [])
            if not cat_quotes:
                continue

            self._add_text_box(slide, Inches(0.5), y, Inches(12), Inches(0.35),
                               f"■ {cat_name} ({cat_data['count']} 个帖子)",
                               font_size=13, bold=True, color=DARK_BLUE)
            y += Inches(0.4)

            for quote_text in cat_quotes[:2]:
                if y > Inches(6.5):
                    break
                truncated = (quote_text or "")[:250]
                if len(quote_text or "") > 250:
                    truncated += "..."

                box = slide.shapes.add_shape(1, Inches(0.7), y, Inches(11.8), Inches(0.85))
                box.fill.solid()
                box.fill.fore_color.rgb = LIGHT_GRAY
                box.line.fill.background()

                self._add_text_box(slide, Inches(0.9), y + Inches(0.05),
                                   Inches(11.3), Inches(0.7),
                                   f'"{truncated}"',
                                   font_size=10, color=TEXT_DARK)
                y += Inches(0.95)

            shown += 1
            y += Inches(0.1)

        # 高互动帖子原声
        if quotes and y < Inches(5.5):
            self._add_text_box(slide, Inches(0.5), y, Inches(12), Inches(0.35),
                               "■ 高互动代表性帖子 (Top Engagement Posts)",
                               font_size=13, bold=True, color=DARK_BLUE)
            y += Inches(0.4)

            for q in quotes[:3]:
                if y > Inches(6.5):
                    break
                text = (q.get("text", "") or "")[:200]
                if len(q.get("text", "") or "") > 200:
                    text += "..."
                author = q.get("author", "")
                reactions = q.get("reactions", 0)

                box = slide.shapes.add_shape(1, Inches(0.7), y, Inches(11.8), Inches(0.85))
                box.fill.solid()
                box.fill.fore_color.rgb = LIGHT_GRAY
                box.line.fill.background()

                self._add_text_box(slide, Inches(0.9), y + Inches(0.05),
                                   Inches(11.3), Inches(0.5),
                                   f'"{text}"', font_size=10, color=TEXT_DARK)
                self._add_text_box(slide, Inches(0.9), y + Inches(0.55),
                                   Inches(11.3), Inches(0.25),
                                   f"— {author} | {reactions} 个反应 (reactions)",
                                   font_size=9, color=TEXT_LIGHT)
                y += Inches(0.95)

        return page_num

    def _build_positive_analysis(self, page_num: int) -> int:
        """第三章：正面反馈分析。"""
        subcats = self.summary.get("positive_subcategories", {})
        quotes = self.summary.get("positive_quotes", [])
        return self._build_subcategory_analysis(
            "第三章：正面反馈分析 (Positive Feedback Analysis)",
            subcats, quotes, MPL_GREEN, ACCENT_GREEN, page_num
        )

    def _build_negative_analysis(self, page_num: int) -> int:
        """第四章：负面反馈分析。"""
        subcats = self.summary.get("negative_subcategories", {})
        quotes = self.summary.get("negative_quotes", [])
        return self._build_subcategory_analysis(
            "第四章：负面反馈分析 (Negative Feedback Analysis)",
            subcats, quotes, MPL_RED, ACCENT_RED, page_num
        )

    def _build_issue_analysis(self, page_num: int) -> int:
        """第五章：问题/求助分析。"""
        subcats = self.summary.get("issue_subcategories", {})
        quotes = self.summary.get("issue_quotes", [])
        return self._build_subcategory_analysis(
            "第五章：问题/求助分析 (Issues Analysis)",
            subcats, quotes, MPL_ORANGE, ACCENT_YELLOW, page_num
        )

    def _build_competitor_slide(self, page_num: int):
        """第六章：竞品提及分析。"""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "第六章：竞品提及分析 (Competitor Mentions)", page_num)

        competitors = self.summary.get("competitor_mentions", {})
        if competitors:
            labels = list(competitors.keys())
            values = list(competitors.values())

            fig = self._make_horizontal_bar(
                labels, values,
                title="竞品品牌提及次数 (Competitor Brand Mentions)",
                colors=MPL_ORANGE,
                figsize=(7, max(3, len(labels) * 0.6))
            )
            self._add_chart_image(slide, fig, Inches(0.5), Inches(1.2), Inches(7), Inches(5))

            self._add_text_box(slide, Inches(8), Inches(1.5), Inches(4.5), Inches(0.4),
                               "说明 (Notes)", font_size=14, bold=True, color=DARK_BLUE)
            notes = [
                "统计范围包含帖子正文及评论 (Posts + Comments)",
                "每个品牌在每条帖子中仅计一次 (Once per post)",
                "竞品提及可用于分析用户比较维度",
            ]
            self._add_bullet_list(slide, Inches(8), Inches(2.1), Inches(4.5), Inches(3),
                                  notes, font_size=11)
        else:
            self._add_text_box(slide, Inches(0.5), Inches(2), Inches(10), Inches(1),
                               "暂无竞品提及数据 (No competitor mention data)",
                               font_size=16, color=TEXT_LIGHT)

    def _build_sentiment_overview(self, page_num: int):
        """第七章：情感分析总览。"""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "第七章：情感分析总览 (Sentiment Overview)", page_num)

        sent_dist = self.summary.get("sentiment_distribution", {})
        if sent_dist:
            label_map = {
                "positive": "正面 (Positive)",
                "negative": "负面 (Negative)",
                "neutral": "中性 (Neutral)",
                "mixed": "混合 (Mixed)",
            }
            labels = [label_map.get(k, k) for k in sent_dist]
            values = list(sent_dist.values())
            colors = [SENTIMENT_COLORS.get(k, MPL_GRAY) for k in sent_dist]

            fig = self._make_pie_chart(labels, values,
                                       title="情感分布 (Sentiment Distribution)",
                                       colors=colors, figsize=(5, 5))
            self._add_chart_image(slide, fig, Inches(0.5), Inches(1.2), Inches(5.5), Inches(5.5))

        # 分类交叉分析
        self._add_text_box(slide, Inches(6.5), Inches(1.3), Inches(6), Inches(0.4),
                           "分类与情感交叉分析 (Cross Analysis)",
                           font_size=16, bold=True, color=DARK_BLUE)

        primary_dist = self.summary.get("primary_distribution", {})
        total = sum(primary_dist.values())
        y = Inches(2.0)
        for cat in PRIMARY_CAT_EN:
            count = primary_dist.get(cat, 0)
            pct = count / max(total, 1) * 100
            en_name = PRIMARY_CAT_EN[cat]
            self._add_text_box(slide, Inches(6.5), y, Inches(6), Inches(0.35),
                               f"{cat} ({en_name}): {count} ({pct:.1f}%)",
                               font_size=12, color=TEXT_DARK)
            y += Inches(0.4)

    def _build_appendix(self, page_num: int):
        """附录：分析方法说明。"""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "附录：分析方法说明 (Appendix: Methodology)", page_num)

        method_text = [
            "主贴分类 (Primary Classification): MECE 五分类——问题/求助、打印结果展示、正面反馈、负面反馈、其他内容",
            "主贴分类方法: 基于关键词规则 + LLM 增强（如启用），每帖仅归入1个类别",
            "正面/负面子分类 (Positive/Negative Sub-classification): 允许多标签（1-3个），总数可超过帖子数",
            "问题/求助子分类 (Issue Sub-classification): MECE 单标签，每帖仅归入1个子类别",
            "情感分析 (Sentiment Analysis): 加权词典方法（强/中/弱三级），支持中英文",
            "用户原声 (User Voices): 按互动量排序，选取各子类别代表性帖子（英文原文）",
            "字体规范 (Fonts): 中文使用等线 (DengXian)，英文使用 Calibri",
        ]
        self._add_bullet_list(slide, Inches(0.5), Inches(1.3), Inches(12), Inches(5),
                              method_text, font_size=12)

    # ── 主生成方法 ────────────────────────────────────────────────

    def generate(self, output_path: str):
        """生成完整的 PPTX 报告。"""
        page = 1

        # 封面
        self._build_cover_slide()

        # 第一章：数据概览
        self._build_overview(page)
        page += 1

        # 第二章：主贴五分类
        self._build_primary_classification(page)
        page += 1

        # 第三章：正面反馈分析（图表页 + 用户原声页）
        page = self._build_positive_analysis(page)
        page += 1

        # 第四章：负面反馈分析（图表页 + 用户原声页）
        page = self._build_negative_analysis(page)
        page += 1

        # 第五章：问题/求助分析（图表页 + 用户原声页）
        page = self._build_issue_analysis(page)
        page += 1

        # 第六章：竞品提及
        self._build_competitor_slide(page)
        page += 1

        # 第七章：情感分析
        self._build_sentiment_overview(page)
        page += 1

        # 附录
        self._build_appendix(page)

        # 保存
        self.prs.save(output_path)
        print(f"报告已保存: {output_path}")
