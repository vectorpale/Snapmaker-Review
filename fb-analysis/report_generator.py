"""
PPTX report generator for Snapmaker U1 Facebook feedback analysis.

Generates a professional ~15-20 slide report with charts and data.
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
from pptx.enum.chart import XL_CHART_TYPE

from classifier import CATEGORY_NAMES, L1_NAMES

# ── Color scheme ──────────────────────────────────────────────────
DARK_BLUE = RGBColor(0x1B, 0x3A, 0x5C)
ORANGE = RGBColor(0xE8, 0x73, 0x2A)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_DARK = RGBColor(0x33, 0x33, 0x33)
TEXT_LIGHT = RGBColor(0x66, 0x66, 0x66)
ACCENT_GREEN = RGBColor(0x27, 0xAE, 0x60)
ACCENT_RED = RGBColor(0xE7, 0x4C, 0x3C)

# Matplotlib color palette
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

SENTIMENT_COLORS = {
    "positive": MPL_GREEN,
    "negative": MPL_RED,
    "neutral": MPL_GRAY,
    "mixed": MPL_YELLOW,
}

SATISFACTION_COLORS = [MPL_RED, MPL_ORANGE, MPL_YELLOW, MPL_LIGHT_BLUE, MPL_GREEN]

# Font names
FONT_EN = "Arial"
FONT_ZH = "Microsoft YaHei"


def _try_font(name_list):
    """Return first available font from list."""
    import matplotlib.font_manager as fm
    available = set(f.name for f in fm.fontManager.ttflist)
    for name in name_list:
        if name in available:
            return name
    return name_list[0]


def _setup_matplotlib():
    """Configure matplotlib defaults."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#CCCCCC",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.color": "#CCCCCC",
        "font.size": 11,
    })
    # Try to set a font that supports CJK
    for font in ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]:
        try:
            plt.rcParams["font.sans-serif"] = [font, "Arial", "DejaVu Sans"]
            break
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False


class ReportGenerator:
    """Generates PPTX report from analysis results."""

    def __init__(self, analysis_data: Dict[str, Any]):
        """
        Args:
            analysis_data: dict containing:
              - posts: list of analyzed post dicts
              - summary: dict with aggregated statistics
              - metadata: dict with data source info
        """
        self.data = analysis_data
        self.posts = analysis_data.get("posts", [])
        self.summary = analysis_data.get("summary", {})
        self.metadata = analysis_data.get("metadata", {})
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        _setup_matplotlib()

    # ── Helpers ────────────────────────────────────────────────────

    def _add_blank_slide(self):
        """Add a blank slide and return it."""
        layout = self.prs.slide_layouts[6]  # Blank layout
        return self.prs.slides.add_slide(layout)

    def _add_title_bar(self, slide, title_text: str, page_num: int = None):
        """Add a colored title bar at the top of a slide."""
        # Dark blue bar
        from pptx.util import Emu
        left, top = Inches(0), Inches(0)
        width, height = self.prs.slide_width, Inches(0.9)
        shape = slide.shapes.add_shape(1, left, top, width, height)  # 1 = rectangle
        shape.fill.solid()
        shape.fill.fore_color.rgb = DARK_BLUE
        shape.line.fill.background()

        # Title text
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(10), Inches(0.65))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.font.name = FONT_EN

        # Page number on right side
        if page_num is not None:
            pn_box = slide.shapes.add_textbox(
                self.prs.slide_width - Inches(1.5), Inches(0.15),
                Inches(1.2), Inches(0.6)
            )
            pn_tf = pn_box.text_frame
            pn_p = pn_tf.paragraphs[0]
            pn_p.text = str(page_num)
            pn_p.alignment = PP_ALIGN.RIGHT
            pn_p.font.size = Pt(14)
            pn_p.font.color.rgb = RGBColor(0xAA, 0xBB, 0xCC)
            pn_p.font.name = FONT_EN

    def _add_text_box(self, slide, left, top, width, height, text,
                      font_size=14, bold=False, color=TEXT_DARK, alignment=PP_ALIGN.LEFT):
        """Add a text box to a slide."""
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(font_size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.font.name = FONT_EN
        p.alignment = alignment
        return txBox

    def _add_bullet_list(self, slide, left, top, width, height, items,
                         font_size=13, color=TEXT_DARK):
        """Add a bullet list text box."""
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True

        for i, item in enumerate(items):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = f"• {item}"
            p.font.size = Pt(font_size)
            p.font.color.rgb = color
            p.font.name = FONT_EN
            p.space_after = Pt(4)

        return txBox

    def _fig_to_image(self, fig) -> io.BytesIO:
        """Convert matplotlib figure to PNG bytes buffer."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        buf.seek(0)
        plt.close(fig)
        return buf

    def _add_chart_image(self, slide, fig, left, top, width, height=None):
        """Add a matplotlib figure as an image to the slide."""
        buf = self._fig_to_image(fig)
        if height is None:
            slide.shapes.add_picture(buf, left, top, width=width)
        else:
            slide.shapes.add_picture(buf, left, top, width=width, height=height)

    # ── Chart builders ─────────────────────────────────────────────

    def _make_horizontal_bar(self, labels, values, title="", color=MPL_DARK_BLUE,
                             figsize=(8, 5), value_fmt="{:.0f}"):
        """Create a horizontal bar chart."""
        fig, ax = plt.subplots(figsize=figsize)
        y_pos = range(len(labels))
        bars = ax.barh(y_pos, values, color=color, height=0.6, edgecolor="white")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=10)
        ax.invert_yaxis()
        ax.set_xlabel("Count", fontsize=11)
        if title:
            ax.set_title(title, fontsize=14, fontweight="bold", color=MPL_DARK_BLUE, pad=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                    value_fmt.format(val), va="center", fontsize=10, color=MPL_DARK_BLUE)

        fig.tight_layout()
        return fig

    def _make_pie_chart(self, labels, values, title="", colors=None, figsize=(5, 5)):
        """Create a pie chart."""
        fig, ax = plt.subplots(figsize=figsize)
        if colors is None:
            colors = CHART_COLORS[:len(labels)]

        # Filter out zero values
        filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
        if not filtered:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=14)
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
            ax.set_title(title, fontsize=14, fontweight="bold", color=MPL_DARK_BLUE, pad=12)

        fig.tight_layout()
        return fig

    def _make_bar_chart(self, labels, values, title="", colors=None, figsize=(7, 5)):
        """Create a vertical bar chart."""
        fig, ax = plt.subplots(figsize=figsize)
        if colors is None:
            colors = [MPL_DARK_BLUE] * len(labels)
        x_pos = range(len(labels))
        bars = ax.bar(x_pos, values, color=colors, width=0.6, edgecolor="white")
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=10, rotation=0)
        ax.set_ylabel("Count", fontsize=11)
        if title:
            ax.set_title(title, fontsize=14, fontweight="bold", color=MPL_DARK_BLUE, pad=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                    str(int(val)), ha="center", fontsize=10, color=MPL_DARK_BLUE)

        fig.tight_layout()
        return fig

    # ── Slide builders ─────────────────────────────────────────────

    def _build_cover_slide(self):
        """Build the cover / title slide."""
        slide = self._add_blank_slide()

        # Background gradient effect: dark blue rectangle
        shape = slide.shapes.add_shape(1, Inches(0), Inches(0),
                                       self.prs.slide_width, self.prs.slide_height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = DARK_BLUE
        shape.line.fill.background()

        # Orange accent bar
        shape2 = slide.shapes.add_shape(1, Inches(0.8), Inches(3.2),
                                        Inches(4), Inches(0.06))
        shape2.fill.solid()
        shape2.fill.fore_color.rgb = ORANGE
        shape2.line.fill.background()

        # Title
        self._add_text_box(slide, Inches(0.8), Inches(1.2), Inches(11), Inches(1.5),
                           "Snapmaker U1", font_size=44, bold=True, color=WHITE)
        self._add_text_box(slide, Inches(0.8), Inches(2.2), Inches(11), Inches(1),
                           "Facebook User Feedback Analysis Report",
                           font_size=28, bold=False, color=RGBColor(0xCC, 0xDD, 0xEE))

        # Subtitle info
        total_posts = self.metadata.get("total_posts", 0)
        total_comments = self.metadata.get("total_comments", 0)
        group_name = self.metadata.get("group_name", "Snapmaker U1 Official Group")
        extraction_time = self.metadata.get("extraction_time", "")

        subtitle = f"Data source: {group_name}\n"
        subtitle += f"Total posts: {total_posts} | Total comments: {total_comments}\n"
        if extraction_time:
            date_part = extraction_time[:10] if len(extraction_time) >= 10 else extraction_time
            subtitle += f"Data extracted: {date_part}"

        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(3.6), Inches(10), Inches(2))
        tf = txBox.text_frame
        tf.word_wrap = True
        for i, line in enumerate(subtitle.split("\n")):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = line
            p.font.size = Pt(16)
            p.font.color.rgb = RGBColor(0xAA, 0xBB, 0xCC)
            p.font.name = FONT_EN
            p.space_after = Pt(4)

    def _build_executive_summary(self, page_num: int):
        """Build Executive Summary slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 1: Executive Summary", page_num)

        summary = self.summary

        # Key findings
        key_findings = summary.get("key_findings", [
            "Analysis pending - run with actual data for findings.",
        ])

        self._add_text_box(slide, Inches(0.5), Inches(1.1), Inches(6), Inches(0.5),
                           "Key Findings", font_size=18, bold=True, color=DARK_BLUE)
        self._add_bullet_list(slide, Inches(0.5), Inches(1.7), Inches(6), Inches(3),
                              key_findings[:5], font_size=13)

        # Satisfaction distribution pie chart
        sat_dist = summary.get("satisfaction_distribution", {})
        if sat_dist:
            labels = [f"Score {i}" for i in range(1, 6)]
            values = [sat_dist.get(str(i), 0) for i in range(1, 6)]
            fig = self._make_pie_chart(labels, values,
                                       title="Overall Satisfaction Distribution",
                                       colors=SATISFACTION_COLORS, figsize=(4.5, 4.5))
            self._add_chart_image(slide, fig, Inches(7), Inches(1.2), Inches(5.5), Inches(5.5))

        # Top issues and top positives
        top_issues = summary.get("top_issues", [])
        top_positives = summary.get("top_positives", [])

        if top_issues:
            self._add_text_box(slide, Inches(0.5), Inches(4.5), Inches(5.5), Inches(0.4),
                               "Top 3 Issues", font_size=15, bold=True, color=ACCENT_RED)
            issue_items = [f"{item['name']} ({item['count']} posts)" for item in top_issues[:3]]
            self._add_bullet_list(slide, Inches(0.5), Inches(5.0), Inches(5.5), Inches(2),
                                  issue_items, font_size=12, color=TEXT_DARK)

    def _build_executive_summary_2(self, page_num: int):
        """Build second Executive Summary slide if needed."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 1: Executive Summary (cont.)", page_num)

        summary = self.summary
        top_positives = summary.get("top_positives", [])
        avg_satisfaction = summary.get("avg_satisfaction", 0)

        # Sentiment distribution pie
        sent_dist = summary.get("sentiment_distribution", {})
        if sent_dist:
            labels = list(sent_dist.keys())
            values = list(sent_dist.values())
            colors = [SENTIMENT_COLORS.get(l, MPL_GRAY) for l in labels]
            fig = self._make_pie_chart(labels, values,
                                       title="Sentiment Distribution",
                                       colors=colors, figsize=(4.5, 4.5))
            self._add_chart_image(slide, fig, Inches(0.5), Inches(1.2), Inches(5.5), Inches(5.5))

        # Top positives
        if top_positives:
            self._add_text_box(slide, Inches(7), Inches(1.1), Inches(5.5), Inches(0.4),
                               "Top 3 Most Appreciated Aspects", font_size=15, bold=True,
                               color=ACCENT_GREEN)
            pos_items = [f"{item['name']} ({item['count']} posts)" for item in top_positives[:3]]
            self._add_bullet_list(slide, Inches(7), Inches(1.7), Inches(5.5), Inches(2),
                                  pos_items, font_size=12)

        # Average satisfaction score
        self._add_text_box(slide, Inches(7), Inches(3.5), Inches(5), Inches(0.4),
                           f"Average Satisfaction Score: {avg_satisfaction:.1f} / 5.0",
                           font_size=16, bold=True, color=DARK_BLUE)

    def _build_data_overview(self, page_num: int):
        """Build Data Overview slides."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 2: Data Overview", page_num)

        stats = self.summary.get("basic_stats", {})
        total_posts = stats.get("total_posts", 0)
        total_comments = stats.get("total_comments", 0)
        unique_authors = stats.get("unique_authors", 0)
        avg_reactions = stats.get("avg_reactions", 0)
        avg_comments = stats.get("avg_comment_count", 0)
        posts_with_images = stats.get("posts_with_images", 0)
        posts_with_videos = stats.get("posts_with_videos", 0)
        posts_text_only = stats.get("posts_text_only", 0)

        # Stats cards
        cards = [
            ("Total Posts", str(total_posts)),
            ("Total Comments", str(total_comments)),
            ("Unique Authors", str(unique_authors)),
            ("Avg Reactions/Post", f"{avg_reactions:.1f}"),
            ("Avg Comments/Post", f"{avg_comments:.1f}"),
        ]

        for i, (label, value) in enumerate(cards):
            col = i % 5
            left = Inches(0.5 + col * 2.5)
            top = Inches(1.3)

            # Card background
            card = slide.shapes.add_shape(1, left, top, Inches(2.2), Inches(1.3))
            card.fill.solid()
            card.fill.fore_color.rgb = RGBColor(0xEC, 0xF0, 0xF1)
            card.line.fill.background()

            # Value
            self._add_text_box(slide, left + Inches(0.15), top + Inches(0.1),
                               Inches(1.9), Inches(0.7),
                               value, font_size=28, bold=True, color=DARK_BLUE,
                               alignment=PP_ALIGN.CENTER)
            # Label
            self._add_text_box(slide, left + Inches(0.15), top + Inches(0.75),
                               Inches(1.9), Inches(0.4),
                               label, font_size=11, color=TEXT_LIGHT,
                               alignment=PP_ALIGN.CENTER)

        # Post type distribution pie
        type_labels = ["Text Only", "With Images", "With Videos"]
        type_values = [posts_text_only, posts_with_images, posts_with_videos]
        fig = self._make_pie_chart(type_labels, type_values,
                                   title="Post Type Distribution",
                                   colors=[MPL_GRAY, MPL_LIGHT_BLUE, MPL_ORANGE],
                                   figsize=(4.5, 4.5))
        self._add_chart_image(slide, fig, Inches(0.5), Inches(3.0), Inches(5), Inches(4))

        # Top 10 high-engagement posts
        top_posts = self.summary.get("top_engagement_posts", [])
        if top_posts:
            self._add_text_box(slide, Inches(6), Inches(3.0), Inches(6.5), Inches(0.4),
                               "Top 10 High-Engagement Posts (by reactions)",
                               font_size=14, bold=True, color=DARK_BLUE)

            items = []
            for i, tp in enumerate(top_posts[:10]):
                truncated = tp.get("text", "")[:80]
                if len(tp.get("text", "")) > 80:
                    truncated += "..."
                items.append(f"[{tp.get('reactions', 0)} reactions] {truncated}")

            self._add_bullet_list(slide, Inches(6), Inches(3.5), Inches(6.8), Inches(3.8),
                                  items, font_size=10, color=TEXT_DARK)

    def _build_category_overview(self, page_num: int):
        """Build top-level category distribution slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 3: Issue Classification Overview", page_num)

        top_dist = self.summary.get("top_category_distribution", {})
        if top_dist:
            labels = [f"{code} - {CATEGORY_NAMES.get(code, code)}" for code in top_dist]
            values = list(top_dist.values())
            colors = [MPL_RED, MPL_ORANGE, MPL_PURPLE, MPL_TEAL, MPL_GREEN, MPL_GRAY]

            fig = self._make_horizontal_bar(labels, values,
                                            title="Top-Level Category Distribution",
                                            color=MPL_DARK_BLUE,
                                            figsize=(9, 4.5))
            # Color each bar differently
            ax = fig.axes[0]
            for bar, c in zip(ax.patches, colors[:len(values)]):
                bar.set_color(c)

            self._add_chart_image(slide, fig, Inches(0.5), Inches(1.2), Inches(8), Inches(5.5))

        # Summary text on the right
        total_classified = sum(top_dist.values()) if top_dist else 0
        self._add_text_box(slide, Inches(8.8), Inches(1.5), Inches(4), Inches(0.5),
                           f"Total Classifications: {total_classified}",
                           font_size=14, bold=True, color=DARK_BLUE)
        self._add_text_box(slide, Inches(8.8), Inches(2.1), Inches(4), Inches(1),
                           "Note: One post can be classified\ninto multiple categories.",
                           font_size=11, color=TEXT_LIGHT)

    def _build_subcategory_top15(self, page_num: int):
        """Build Top 15 subcategory issues slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 3: Top 15 Specific Issues", page_num)

        l2_dist = self.summary.get("l2_category_distribution", {})
        if l2_dist:
            # Sort and take top 15
            sorted_items = sorted(l2_dist.items(), key=lambda x: x[1], reverse=True)[:15]
            labels = []
            values = []
            for code, count in sorted_items:
                name = L1_NAMES.get(code, code)
                labels.append(f"{code}: {name}")
                values.append(count)

            labels.reverse()
            values.reverse()

            fig = self._make_horizontal_bar(labels, values,
                                            title="Top 15 Specific Issue Categories",
                                            color=MPL_ORANGE,
                                            figsize=(10, 7))
            self._add_chart_image(slide, fig, Inches(0.5), Inches(1.1), Inches(12), Inches(6))

    def _build_category_detail(self, cat_code: str, cat_name: str, page_num: int):
        """Build detail slide for a specific top-level category."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, f"Chapter 3: {cat_name} Issues Detail", page_num)

        l1_dist = self.summary.get("l1_category_distribution", {})
        # Filter to subcategories of this top-level
        sub_items = {k: v for k, v in l1_dist.items() if k.startswith(cat_code)}

        if sub_items:
            labels = [f"{code}: {L1_NAMES.get(code, code)}" for code in sub_items]
            values = list(sub_items.values())

            fig = self._make_horizontal_bar(labels, values,
                                            title=f"{cat_name} Sub-category Breakdown",
                                            color=MPL_DARK_BLUE,
                                            figsize=(7, max(3, len(labels) * 0.6)))
            self._add_chart_image(slide, fig, Inches(0.3), Inches(1.2), Inches(7), Inches(5.5))

        # Representative posts
        examples = self.summary.get("category_examples", {}).get(cat_code, [])
        if examples:
            self._add_text_box(slide, Inches(7.5), Inches(1.2), Inches(5.5), Inches(0.4),
                               "Representative Posts:", font_size=14, bold=True, color=DARK_BLUE)

            ex_items = []
            for ex in examples[:5]:
                text = ex.get("text", "")[:120]
                if len(ex.get("text", "")) > 120:
                    text += "..."
                author = ex.get("author", "Unknown")
                reactions = ex.get("reactions", 0)
                ex_items.append(f'"{text}" — {author} ({reactions} reactions)')

            self._add_bullet_list(slide, Inches(7.5), Inches(1.8), Inches(5.5), Inches(5),
                                  ex_items, font_size=10, color=TEXT_DARK)

    def _build_common_issues(self, page_num: int):
        """Build common issues analysis slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 3: Common Issues (3+ reporters)", page_num)

        common = self.summary.get("common_issues", [])
        if common:
            items = []
            for issue in common[:15]:
                items.append(
                    f"{issue['code']}: {issue['name']} — {issue['count']} posts, "
                    f"{issue.get('unique_authors', 'N/A')} unique reporters, "
                    f"avg reactions: {issue.get('avg_reactions', 0):.1f}"
                )
            self._add_bullet_list(slide, Inches(0.5), Inches(1.3), Inches(12), Inches(5.5),
                                  items, font_size=12)
        else:
            self._add_text_box(slide, Inches(0.5), Inches(2), Inches(10), Inches(1),
                               "No common issues found with 3+ unique reporters.",
                               font_size=14, color=TEXT_LIGHT)

    def _build_satisfaction_slides(self, page_num: int):
        """Build user satisfaction analysis slides."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 4: User Satisfaction Analysis", page_num)

        # Satisfaction score distribution bar chart
        sat_dist = self.summary.get("satisfaction_distribution", {})
        if sat_dist:
            labels = [f"Score {i}" for i in range(1, 6)]
            values = [sat_dist.get(str(i), 0) for i in range(1, 6)]

            fig = self._make_bar_chart(labels, values,
                                       title="Satisfaction Score Distribution (1-5)",
                                       colors=SATISFACTION_COLORS,
                                       figsize=(6, 4))
            self._add_chart_image(slide, fig, Inches(0.3), Inches(1.2), Inches(6), Inches(4.5))

        # Sentiment pie chart
        sent_dist = self.summary.get("sentiment_distribution", {})
        if sent_dist:
            labels = list(sent_dist.keys())
            values = list(sent_dist.values())
            colors = [SENTIMENT_COLORS.get(l, MPL_GRAY) for l in labels]
            fig = self._make_pie_chart(labels, values,
                                       title="Sentiment Distribution",
                                       colors=colors, figsize=(4.5, 4.5))
            self._add_chart_image(slide, fig, Inches(6.5), Inches(1.2), Inches(5), Inches(5))

    def _build_keyword_analysis(self, page_num: int):
        """Build positive/negative keyword analysis slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 4: Keyword Analysis", page_num)

        pos_kw = self.summary.get("positive_keywords", [])
        neg_kw = self.summary.get("negative_keywords", [])

        # Positive keywords
        self._add_text_box(slide, Inches(0.5), Inches(1.2), Inches(5.5), Inches(0.4),
                           "Top Positive Keywords", font_size=16, bold=True, color=ACCENT_GREEN)
        if pos_kw:
            items = [f"{kw} ({count})" for kw, count in pos_kw[:15]]
            self._add_bullet_list(slide, Inches(0.5), Inches(1.8), Inches(5.5), Inches(5),
                                  items, font_size=12, color=TEXT_DARK)

        # Negative keywords
        self._add_text_box(slide, Inches(7), Inches(1.2), Inches(5.5), Inches(0.4),
                           "Top Negative Keywords", font_size=16, bold=True, color=ACCENT_RED)
        if neg_kw:
            items = [f"{kw} ({count})" for kw, count in neg_kw[:15]]
            self._add_bullet_list(slide, Inches(7), Inches(1.8), Inches(5.5), Inches(5),
                                  items, font_size=12, color=TEXT_DARK)

    def _build_competitor_slide(self, page_num: int):
        """Build competitor comparison mentions slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 5: Competitor Mentions", page_num)

        competitors = self.summary.get("competitor_mentions", {})
        if competitors:
            labels = list(competitors.keys())
            values = list(competitors.values())

            fig = self._make_horizontal_bar(labels, values,
                                            title="Competitor Brand Mentions",
                                            color=MPL_ORANGE,
                                            figsize=(7, max(3, len(labels) * 0.6)))
            self._add_chart_image(slide, fig, Inches(0.5), Inches(1.2), Inches(7), Inches(5))

        # Comparison dimensions
        comp_dims = self.summary.get("comparison_dimensions", [])
        if comp_dims:
            self._add_text_box(slide, Inches(8), Inches(1.2), Inches(4.5), Inches(0.4),
                               "Comparison Dimensions:", font_size=14, bold=True, color=DARK_BLUE)
            self._add_bullet_list(slide, Inches(8), Inches(1.8), Inches(4.5), Inches(4),
                                  comp_dims, font_size=12)

    def _build_feature_requests(self, page_num: int):
        """Build feature requests slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Chapter 6: Feature Requests & Improvement Suggestions", page_num)

        features = self.summary.get("feature_requests", [])
        if features:
            labels = [f['name'] for f in features[:10]]
            values = [f['count'] for f in features[:10]]

            fig = self._make_horizontal_bar(labels, values,
                                            title="Most Requested Features",
                                            color=MPL_TEAL,
                                            figsize=(8, max(3, len(labels) * 0.55)))
            self._add_chart_image(slide, fig, Inches(0.3), Inches(1.2), Inches(8), Inches(5.5))

        # Feature list on the right
        if features:
            self._add_text_box(slide, Inches(8.5), Inches(1.2), Inches(4.5), Inches(0.4),
                               "Feature Details:", font_size=14, bold=True, color=DARK_BLUE)
            items = [f"{f['name']}: {f['count']} mentions" for f in features[:10]]
            self._add_bullet_list(slide, Inches(8.5), Inches(1.8), Inches(4.5), Inches(5),
                                  items, font_size=11)

    def _build_quotes_slide(self, title: str, quotes: list, page_num: int,
                            title_color=DARK_BLUE):
        """Build a slide with user feedback quotes."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, title, page_num)

        if not quotes:
            self._add_text_box(slide, Inches(0.5), Inches(2), Inches(10), Inches(1),
                               "No representative feedback found.",
                               font_size=14, color=TEXT_LIGHT)
            return

        y = Inches(1.2)
        for i, quote in enumerate(quotes[:5]):
            text = quote.get("text", "")[:200]
            if len(quote.get("text", "")) > 200:
                text += "..."
            author = quote.get("author", "Anonymous")
            reactions = quote.get("reactions", 0)

            # Quote box
            box = slide.shapes.add_shape(1, Inches(0.5), y, Inches(12), Inches(1.1))
            box.fill.solid()
            box.fill.fore_color.rgb = LIGHT_GRAY
            box.line.fill.background()

            self._add_text_box(slide, Inches(0.7), y + Inches(0.05), Inches(11.5), Inches(0.7),
                               f'"{text}"', font_size=11, color=TEXT_DARK)
            self._add_text_box(slide, Inches(0.7), y + Inches(0.7), Inches(11.5), Inches(0.3),
                               f"— {author} | {reactions} reactions",
                               font_size=10, bold=False, color=TEXT_LIGHT)

            y += Inches(1.2)

    def _build_appendix(self, page_num: int):
        """Build appendix slide."""
        slide = self._add_blank_slide()
        self._add_title_bar(slide, "Appendix: Methodology & Full Statistics", page_num)

        method_text = [
            "Classification Method: Keyword + regex pattern matching",
            "Each post is analyzed using English and Traditional Chinese keyword dictionaries",
            "Multi-label classification: a single post can belong to multiple categories",
            "Sentiment analysis uses a weighted lexicon approach (strong/moderate/mild)",
            "Satisfaction scored 1-5 based on sentiment intensity and context",
            "Post weight adjusted by reaction count (higher reactions = higher influence)",
            "Comments are included in analysis as supporting context for their parent post",
        ]
        self._add_bullet_list(slide, Inches(0.5), Inches(1.3), Inches(12), Inches(3),
                              method_text, font_size=12)

        # Full category stats table (simplified as text)
        l2_dist = self.summary.get("l2_category_distribution", {})
        if l2_dist:
            self._add_text_box(slide, Inches(0.5), Inches(4.2), Inches(12), Inches(0.4),
                               "Full Category Statistics:", font_size=14, bold=True, color=DARK_BLUE)

            sorted_items = sorted(l2_dist.items(), key=lambda x: x[1], reverse=True)
            col1_items = sorted_items[:len(sorted_items)//2]
            col2_items = sorted_items[len(sorted_items)//2:]

            if col1_items:
                items1 = [f"{code}: {L1_NAMES.get(code, code)} = {count}" for code, count in col1_items]
                self._add_bullet_list(slide, Inches(0.5), Inches(4.7), Inches(6), Inches(2.5),
                                      items1, font_size=10)
            if col2_items:
                items2 = [f"{code}: {L1_NAMES.get(code, code)} = {count}" for code, count in col2_items]
                self._add_bullet_list(slide, Inches(6.5), Inches(4.7), Inches(6), Inches(2.5),
                                      items2, font_size=10)

    # ── Main generation method ─────────────────────────────────────

    def generate(self, output_path: str):
        """
        Generate the complete PPTX report.

        Args:
            output_path: path to save the .pptx file
        """
        page = 1

        # Cover
        self._build_cover_slide()

        # Chapter 1: Executive Summary
        self._build_executive_summary(page)
        page += 1
        self._build_executive_summary_2(page)
        page += 1

        # Chapter 2: Data Overview
        self._build_data_overview(page)
        page += 1

        # Chapter 3: Classification Analysis
        self._build_category_overview(page)
        page += 1
        self._build_subcategory_top15(page)
        page += 1

        # Category detail slides
        for cat_code, cat_name in [("H", "Hardware"), ("S", "Software"),
                                    ("M", "Material"), ("U", "User Experience")]:
            l1_dist = self.summary.get("l1_category_distribution", {})
            has_data = any(k.startswith(cat_code) for k in l1_dist)
            if has_data:
                self._build_category_detail(cat_code, cat_name, page)
                page += 1

        self._build_common_issues(page)
        page += 1

        # Chapter 4: Satisfaction
        self._build_satisfaction_slides(page)
        page += 1
        self._build_keyword_analysis(page)
        page += 1

        # Chapter 5: Competitors
        self._build_competitor_slide(page)
        page += 1

        # Chapter 6: Feature Requests
        self._build_feature_requests(page)
        page += 1

        # Chapter 7: Quotes
        positive_quotes = self.summary.get("positive_quotes", [])
        negative_quotes = self.summary.get("negative_quotes", [])
        constructive_quotes = self.summary.get("constructive_quotes", [])

        self._build_quotes_slide("Chapter 7: Most Positive Feedback",
                                 positive_quotes, page, title_color=ACCENT_GREEN)
        page += 1
        self._build_quotes_slide("Chapter 7: Most Negative Feedback",
                                 negative_quotes, page, title_color=ACCENT_RED)
        page += 1
        self._build_quotes_slide("Chapter 7: Most Constructive Feedback",
                                 constructive_quotes, page)
        page += 1

        # Appendix
        self._build_appendix(page)

        # Save
        self.prs.save(output_path)
        print(f"Report saved to: {output_path}")
