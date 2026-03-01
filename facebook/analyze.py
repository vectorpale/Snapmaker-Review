#!/usr/bin/env python3
"""
Snapmaker U1 Facebook 用户反馈分析工具

使用方法:
    # 默认使用 Qwen LLM 分类（需在 .env 中配置 QWEN_API_KEY）
    python analyze.py <input.json>

    # 指定输出目录
    python analyze.py <input.json> --output ./reports/

    # 禁用 LLM，仅用关键词规则分类
    python analyze.py <input.json> --no-llm

分类体系（双维度）:
    维度一 — 内容类型 (MECE): 问题/求助、评价/反馈、产品展示、其他
    维度二 — 情感倾向: 正面、负面、中性
    子分类:
      - 情感=正面 的帖子 → 正面反馈子分类（多标签）
      - 情感=负面 的帖子 → 负面反馈子分类（多标签）
      - 内容类型=问题/求助 的帖子 → 问题子分类（MECE 单标签）
    生成含饼图/条形图的 PPTX 报告（简体中文）
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Any

from classifier import FeedbackClassifier, CATEGORY_NAMES, L1_NAMES, get_l1_from_code, get_top_from_code
from sentiment import SentimentAnalyzer


# ── 双维度分类名称 ─────────────────────────────────────────────

CONTENT_TYPES = {
    "问题/求助": "Questions / Help",
    "评价/反馈": "Reviews / Feedback",
    "产品展示": "Product Showcase",
    "其他": "Other",
}

SENTIMENT_LABELS = {
    "正面": "Positive",
    "负面": "Negative",
    "中性": "Neutral",
}

# 情感映射：将 sentiment.py 的输出映射到三分类
_SENTIMENT_MAP = {
    "positive": "正面",
    "negative": "负面",
    "neutral": "中性",
    "mixed": "中性",  # 混合情感归入中性
}

# 用于关键词回退分类的规则映射（仅判断内容类型）
_KEYWORD_CONTENT_TYPE_MAP = {
    "问题/求助": {
        "top_codes": {"H", "S", "M", "U"},
        "keywords": [
            "help", "issue", "problem", "error", "fail", "broken", "not working",
            "how to", "anyone know", "stuck", "trouble", "bug", "crash",
            "can't", "cannot", "doesn't", "won't", "unable",
            "求助", "问题", "报错", "故障",
        ],
    },
    "产品展示": {
        "l1_codes": {"P6"},
        "keywords": [
            "check this out", "just printed", "first print", "my print",
            "look at this", "look what", "show off", "printed this",
            "test print", "benchy", "here is my", "sharing my",
            "showcase", "came out great", "turned out",
            "晒", "成品", "打印了",
        ],
    },
    "评价/反馈": {
        "top_codes": {"P"},
        "keywords": [
            "love", "great", "amazing", "excellent", "fantastic", "awesome",
            "impressed", "happy with", "recommend", "best printer",
            "worth every penny", "disappointed", "frustrat", "regret",
            "waste of money", "terrible", "awful", "worst", "horrible",
            "returning", "refund", "not worth",
            "好评", "推荐", "满意", "差评", "失望",
        ],
    },
}


def load_data(filepath: str) -> dict:
    """加载并验证 Facebook JSON 数据文件。"""
    print(f"正在加载数据: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data.get("posts", [])
    comments_flat = data.get("comments_flat", [])

    print(f"  加载了 {len(posts)} 个帖子, {len(comments_flat)} 条评论")
    print(f"  群组: {data.get('group_name', '未知')}")
    print(f"  采集时间: {data.get('extraction_time', '未知')}")

    return data


def _keyword_content_type(post: dict, classification: dict) -> str:
    """基于关键词和已有分类结果判断内容类型（回退方案）。"""
    text = (post.get("text", "") or "").lower()
    top_cats = set(classification.get("top_categories", []))
    l1_cats = set(classification.get("l1_categories", []))

    scores = Counter()

    for cat_name, rules in _KEYWORD_CONTENT_TYPE_MAP.items():
        if rules.get("top_codes") and top_cats & rules["top_codes"]:
            scores[cat_name] += 2
        if rules.get("l1_codes") and l1_cats & rules["l1_codes"]:
            scores[cat_name] += 3
        for kw in rules.get("keywords", []):
            if kw in text:
                scores[cat_name] += 1.5

    # 展示帖子特征：含图片
    if post.get("has_image"):
        scores["产品展示"] += 1

    if not scores:
        return "其他"

    return scores.most_common(1)[0][0]


def _map_sentiment_label(sentiment_result: dict) -> str:
    """将 sentiment.py 输出映射到三分类情感标签。"""
    raw = sentiment_result.get("sentiment", "neutral")
    return _SENTIMENT_MAP.get(raw, "中性")


def analyze_posts(posts: list, classifier: FeedbackClassifier,
                  sentiment_analyzer: SentimentAnalyzer,
                  llm_client=None) -> list:
    """对所有帖子进行分析：细粒度分类 + 情感分析 + 双维度分类。"""
    results = []
    print(f"\n--- 第一阶段：细粒度分类与情感分析 ---")

    for i, post in enumerate(posts):
        if i > 0 and i % 50 == 0:
            print(f"  已处理 {i}/{len(posts)} 个帖子...")

        classification = classifier.classify_post(post)
        sentiment = sentiment_analyzer.analyze_post(post)

        result = {
            **post,
            "classification": classification,
            "sentiment": sentiment,
        }
        results.append(result)

    print(f"  完成 {len(results)} 个帖子的细粒度分析。")

    # 双维度分类
    print(f"\n--- 第二阶段：双维度分类（内容类型 × 情感倾向） ---")
    if llm_client:
        print("  使用 LLM 进行双维度分类...")
        try:
            llm_results = llm_client.classify_posts_batch(posts)
            for i, result in enumerate(results):
                if i < len(llm_results):
                    llm_r = llm_results[i]
                    ct = llm_r.get("content_type", "其他")
                    st = llm_r.get("sentiment", "中性")
                    result["content_type"] = ct if ct in CONTENT_TYPES else _keyword_content_type(
                        result, result["classification"]
                    )
                    result["sentiment_label"] = st if st in SENTIMENT_LABELS else _map_sentiment_label(
                        result["sentiment"]
                    )
                    result["classify_confidence"] = llm_r.get("confidence", 0.5)
                    result["classify_reason"] = llm_r.get("brief_reason", "")
                else:
                    result["content_type"] = _keyword_content_type(
                        result, result["classification"]
                    )
                    result["sentiment_label"] = _map_sentiment_label(result["sentiment"])
            print(f"  LLM 双维度分类完成。")
        except Exception as e:
            print(f"  LLM 分类失败: {e}，回退到关键词分类...")
            for result in results:
                result["content_type"] = _keyword_content_type(
                    result, result["classification"]
                )
                result["sentiment_label"] = _map_sentiment_label(result["sentiment"])
    else:
        print("  使用关键词规则 + 情感分析引擎...")
        for result in results:
            result["content_type"] = _keyword_content_type(
                result, result["classification"]
            )
            result["sentiment_label"] = _map_sentiment_label(result["sentiment"])

    # 统计分布
    ct_counter = Counter(r["content_type"] for r in results)
    st_counter = Counter(r["sentiment_label"] for r in results)
    print(f"\n  内容类型分布:")
    for ct in CONTENT_TYPES:
        count = ct_counter.get(ct, 0)
        pct = count / max(len(results), 1) * 100
        print(f"    {ct}: {count} ({pct:.1f}%)")
    print(f"\n  情感倾向分布:")
    for st in SENTIMENT_LABELS:
        count = st_counter.get(st, 0)
        pct = count / max(len(results), 1) * 100
        print(f"    {st}: {count} ({pct:.1f}%)")

    return results


def analyze_subcategories_with_llm(analyzed_posts: list, llm_client) -> dict:
    """使用 LLM 进行子分类：按情感分正面/负面，按内容类型分问题。"""
    sub_results = {"positive": [], "negative": [], "issue": []}

    # 按情感分组（正面/负面）
    positive_posts = [p for p in analyzed_posts if p.get("sentiment_label") == "正面"]
    negative_posts = [p for p in analyzed_posts if p.get("sentiment_label") == "负面"]
    # 按内容类型分组（问题/求助）
    issue_posts = [p for p in analyzed_posts if p.get("content_type") == "问题/求助"]

    if positive_posts:
        print(f"\n  正面反馈子分类 ({len(positive_posts)} 个帖子)...")
        try:
            sub_results["positive"] = llm_client.analyze_subcategories(positive_posts, "positive")
        except Exception as e:
            print(f"    失败: {e}")

    if negative_posts:
        print(f"\n  负面反馈子分类 ({len(negative_posts)} 个帖子)...")
        try:
            sub_results["negative"] = llm_client.analyze_subcategories(negative_posts, "negative")
        except Exception as e:
            print(f"    失败: {e}")

    if issue_posts:
        print(f"\n  问题/求助子分类 ({len(issue_posts)} 个帖子)...")
        try:
            sub_results["issue"] = llm_client.analyze_subcategories(issue_posts, "issue")
        except Exception as e:
            print(f"    失败: {e}")

    return sub_results


def _aggregate_subcategories(sub_results: List[Dict]) -> Dict[str, Dict]:
    """聚合子分类结果，统计各子类别数量和代表性用户原声。

    支持两种格式：
    - 多标签：subcategories 为数组（正面/负面），总数可超过帖子数
    - 单标签：subcategory 为字符串（问题/求助），总数 = 帖子数
    """
    category_data = defaultdict(lambda: {"count": 0, "quotes": []})

    for item in sub_results:
        quote = item.get("representative_quote", "")

        subcats = item.get("subcategories")
        if subcats and isinstance(subcats, list):
            for subcat in subcats:
                if subcat:
                    category_data[subcat]["count"] += 1
                    if quote and len(category_data[subcat]["quotes"]) < 3:
                        category_data[subcat]["quotes"].append(quote)
        else:
            subcat = item.get("subcategory", "未分类")
            if not subcat:
                subcat = "未分类"
            category_data[subcat]["count"] += 1
            if quote and len(category_data[subcat]["quotes"]) < 3:
                category_data[subcat]["quotes"].append(quote)

    sorted_data = dict(
        sorted(category_data.items(), key=lambda x: x[1]["count"], reverse=True)
    )

    return sorted_data


def build_summary(analyzed_posts: list, raw_data: dict,
                  classifier: FeedbackClassifier,
                  sentiment_analyzer: SentimentAnalyzer,
                  llm_subcategories: dict = None) -> dict:
    """构建综合统计摘要。"""
    total_posts = len(analyzed_posts)

    # 基本统计
    unique_authors = len(set(p.get("author", "") for p in analyzed_posts if p.get("author")))
    total_reactions = sum(p.get("reactions", 0) or 0 for p in analyzed_posts)
    total_comment_count = sum(p.get("comment_count", 0) or 0 for p in analyzed_posts)
    posts_with_images = sum(1 for p in analyzed_posts if p.get("has_image"))
    posts_with_videos = sum(1 for p in analyzed_posts if p.get("has_video"))
    posts_text_only = max(0, total_posts - len([
        p for p in analyzed_posts if p.get("has_image") or p.get("has_video")
    ]))

    basic_stats = {
        "total_posts": total_posts,
        "total_comments": raw_data.get("total_comments", 0),
        "unique_authors": unique_authors,
        "avg_reactions": total_reactions / max(total_posts, 1),
        "avg_comment_count": total_comment_count / max(total_posts, 1),
        "posts_with_images": posts_with_images,
        "posts_with_videos": posts_with_videos,
        "posts_text_only": posts_text_only,
    }

    # ── 内容类型分布 ──
    ct_counter = Counter(p.get("content_type", "其他") for p in analyzed_posts)
    content_type_distribution = {}
    for ct in CONTENT_TYPES:
        content_type_distribution[ct] = ct_counter.get(ct, 0)

    # ── 情感倾向分布 ──
    st_counter = Counter(p.get("sentiment_label", "中性") for p in analyzed_posts)
    sentiment_distribution = {}
    for st in SENTIMENT_LABELS:
        sentiment_distribution[st] = st_counter.get(st, 0)

    # ── 交叉分布 (content_type × sentiment) ──
    cross_distribution = {}
    for ct in CONTENT_TYPES:
        cross_distribution[ct] = {}
        ct_posts = [p for p in analyzed_posts if p.get("content_type") == ct]
        for st in SENTIMENT_LABELS:
            cross_distribution[ct][st] = sum(
                1 for p in ct_posts if p.get("sentiment_label") == st
            )

    # ── 按维度分组 ──
    positive_posts = [p for p in analyzed_posts if p.get("sentiment_label") == "正面"]
    negative_posts = [p for p in analyzed_posts if p.get("sentiment_label") == "负面"]
    issue_posts = [p for p in analyzed_posts if p.get("content_type") == "问题/求助"]

    # ── 代表性帖子（按反应数排序） ──
    def _get_top_quotes(posts_list, n=5):
        sorted_posts = sorted(posts_list, key=lambda p: p.get("reactions", 0) or 0, reverse=True)
        return [
            {
                "text": p.get("text", ""),
                "author": p.get("author", ""),
                "reactions": p.get("reactions", 0),
            }
            for p in sorted_posts[:n]
        ]

    positive_quotes = _get_top_quotes(positive_posts)
    negative_quotes = _get_top_quotes(negative_posts)
    issue_quotes = _get_top_quotes(issue_posts)

    # ── LLM 子分类聚合 ──
    positive_subcategories = {}
    negative_subcategories = {}
    issue_subcategories = {}

    if llm_subcategories:
        if llm_subcategories.get("positive"):
            positive_subcategories = _aggregate_subcategories(llm_subcategories["positive"])
        if llm_subcategories.get("negative"):
            negative_subcategories = _aggregate_subcategories(llm_subcategories["negative"])
        if llm_subcategories.get("issue"):
            issue_subcategories = _aggregate_subcategories(llm_subcategories["issue"])
    else:
        positive_subcategories = _fallback_subcategories(positive_posts, "P")
        negative_subcategories = _fallback_subcategories(negative_posts, "H,S,M,U")
        issue_subcategories = _fallback_subcategories(issue_posts, "H,S,M,U")

    # ── 竞品提及 ──
    competitor_mentions = _extract_competitor_mentions(analyzed_posts)

    # ── 高互动帖子 ──
    sorted_by_reactions = sorted(analyzed_posts, key=lambda p: p.get("reactions", 0) or 0, reverse=True)
    top_engagement = [
        {
            "text": p.get("text", ""),
            "author": p.get("author", ""),
            "reactions": p.get("reactions", 0),
            "comment_count": p.get("comment_count", 0),
            "content_type": p.get("content_type", ""),
            "sentiment_label": p.get("sentiment_label", ""),
        }
        for p in sorted_by_reactions[:10]
    ]

    return {
        "basic_stats": basic_stats,
        "content_type_distribution": content_type_distribution,
        "sentiment_distribution": sentiment_distribution,
        "cross_distribution": cross_distribution,
        "positive_subcategories": positive_subcategories,
        "negative_subcategories": negative_subcategories,
        "issue_subcategories": issue_subcategories,
        "positive_quotes": positive_quotes,
        "negative_quotes": negative_quotes,
        "issue_quotes": issue_quotes,
        "positive_count": len(positive_posts),
        "negative_count": len(negative_posts),
        "issue_count": len(issue_posts),
        "competitor_mentions": competitor_mentions,
        "top_engagement_posts": top_engagement,
    }


def _fallback_subcategories(posts: list, prefix_filter: str) -> Dict[str, Dict]:
    """在没有 LLM 的情况下，使用细粒度分类结果作为子分类（每帖选1个最佳匹配）。"""
    prefixes = [p.strip() for p in prefix_filter.split(",")]
    category_data = defaultdict(lambda: {"count": 0, "quotes": []})

    for post in posts:
        cls = post.get("classification", {})
        text = (post.get("text", "") or "")[:200]

        best_cat = None
        best_confidence = -1
        for cat in cls.get("categories", []):
            code = cat["code"]
            top_code = code[0] if code else ""
            if top_code in prefixes:
                confidence = cat.get("confidence", 0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    name = cat.get("name", code)
                    name_zh = cat.get("name_zh", "")
                    best_cat = f"{name_zh} ({name})" if name_zh else name

        if best_cat is None:
            best_cat = "其他 (Other)"

        category_data[best_cat]["count"] += 1
        if text and len(category_data[best_cat]["quotes"]) < 3:
            category_data[best_cat]["quotes"].append(text)

    return dict(sorted(category_data.items(), key=lambda x: x[1]["count"], reverse=True))


def _extract_competitor_mentions(posts: list) -> Dict[str, int]:
    """统计竞品品牌提及次数。"""
    competitors = {
        "Bambu Lab": [r"bambu\s*lab", r"bambu", r"bamboo\s*lab"],
        "Prusa": [r"prusa", r"prusa\s*xl", r"prusa\s*mk"],
        "Creality": [r"creality", r"ender", r"cr-?10", r"k1"],
        "Voron": [r"voron"],
        "Elegoo": [r"elegoo"],
        "AnkerMake": [r"anker\s*make", r"ankermake"],
        "Qidi": [r"qidi"],
        "FlashForge": [r"flash\s*forge", r"flashforge"],
    }

    counts = Counter()
    for post in posts:
        text = (post.get("text", "") or "").lower()
        for comment in post.get("comments", []):
            text += " " + (comment.get("text", "") or "").lower()

        for brand, patterns in competitors.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    counts[brand] += 1
                    break

    return dict(counts.most_common())


def save_intermediate_json(analyzed_posts: list, summary: dict,
                           metadata: dict, output_path: str):
    """保存中间分析结果为 JSON 文件。"""

    def _make_serializable(obj):
        if isinstance(obj, set):
            return sorted(list(obj))
        if isinstance(obj, Counter):
            return dict(obj)
        return obj

    output = {
        "metadata": metadata,
        "summary": summary,
        "posts": [
            {
                "post_id": p.get("post_id", ""),
                "author": p.get("author", ""),
                "text": (p.get("text", "") or "")[:500],
                "reactions": p.get("reactions", 0),
                "comment_count": p.get("comment_count", 0),
                "content_type": p.get("content_type", ""),
                "sentiment_label": p.get("sentiment_label", ""),
                "classification": {
                    "categories": p["classification"]["categories"],
                    "top_categories": p["classification"]["top_categories"],
                },
                "sentiment_detail": {
                    "sentiment": p["sentiment"]["sentiment"],
                    "satisfaction_score": p["sentiment"]["satisfaction_score"],
                },
            }
            for p in analyzed_posts
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=_make_serializable)

    print(f"中间结果已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Snapmaker U1 Facebook 用户反馈分析工具"
    )
    parser.add_argument("input_file", help="Facebook JSON 数据文件路径")
    parser.add_argument("--output", "-o", default=None,
                        help="输出目录 (默认: ./output/)")
    parser.add_argument("--no-llm", action="store_true",
                        help="禁用 LLM，仅使用关键词规则分类")
    parser.add_argument("--api-key", default=None,
                        help="Qwen API Key（也可通过 .env 文件配置）")

    args = parser.parse_args()

    # 加载 .env 配置
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

    # 输出目录
    if args.output:
        output_dir = args.output
    else:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # 加载数据
    raw_data = load_data(args.input_file)
    posts = raw_data.get("posts", [])

    if not posts:
        print("错误: 输入文件中未找到帖子数据。")
        sys.exit(1)

    # 初始化引擎
    print("\n初始化分类引擎...")
    classifier = FeedbackClassifier()
    sentiment_analyzer = SentimentAnalyzer()

    # 初始化 LLM（默认启用，--no-llm 关闭）
    llm_client = None
    if not args.no_llm:
        try:
            from llm_client import LLMClient
            api_key = args.api_key or os.environ.get("QWEN_API_KEY", "")
            llm_client = LLMClient(api_key=api_key)
            print(f"LLM 已启用: {llm_client.model}")
        except Exception as e:
            print(f"警告: LLM 初始化失败 ({e})，将回退到关键词分类。")
            print(f"  提示: 请在 .env 文件中配置 QWEN_API_KEY，或使用 --api-key 参数。")
            llm_client = None
    else:
        print("LLM 已禁用（--no-llm），使用关键词规则分类。")

    # 分析帖子
    print(f"\n开始分析 {len(posts)} 个帖子...")
    analyzed_posts = analyze_posts(posts, classifier, sentiment_analyzer, llm_client)

    # LLM 子分类
    llm_subcategories = None
    if llm_client:
        print("\n--- 第三阶段：子分类深度分析 ---")
        llm_subcategories = analyze_subcategories_with_llm(analyzed_posts, llm_client)

    # 构建统计摘要
    print("\n构建统计摘要...")
    metadata = {
        "group_url": raw_data.get("group_url", ""),
        "group_name": raw_data.get("group_name", "Snapmaker U1 Official Group"),
        "extraction_time": raw_data.get("extraction_time", ""),
        "total_posts": raw_data.get("total_posts", len(posts)),
        "total_comments": raw_data.get("total_comments", 0),
        "llm_enabled": llm_client is not None,
    }
    summary = build_summary(
        analyzed_posts, raw_data, classifier, sentiment_analyzer, llm_subcategories
    )

    # 保存中间结果
    json_path = os.path.join(output_dir, "analysis_result.json")
    save_intermediate_json(analyzed_posts, summary, metadata, json_path)

    # 生成报告
    print("\n生成 PPTX 报告...")
    from report_generator import ReportGenerator
    analysis_data = {
        "posts": analyzed_posts,
        "summary": summary,
        "metadata": metadata,
    }
    report_gen = ReportGenerator(analysis_data)
    pptx_path = os.path.join(output_dir, "report.pptx")
    report_gen.generate(pptx_path)

    print(f"\n{'='*60}")
    print("分析完成！")
    print(f"  中间结果 JSON: {json_path}")
    print(f"  PPTX 报告: {pptx_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
