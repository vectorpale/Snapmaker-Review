#!/usr/bin/env python3
"""
Snapmaker U1 Facebook Feedback Analysis Tool.

Usage:
    python analyze.py <input.json> [--output <dir>]

Reads Facebook group export JSON, classifies posts, performs sentiment analysis,
and generates a PPTX report.
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
from report_generator import ReportGenerator


def load_data(filepath: str) -> dict:
    """Load and validate the Facebook JSON data file."""
    print(f"Loading data from: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data.get("posts", [])
    comments_flat = data.get("comments_flat", [])

    print(f"  Loaded {len(posts)} posts, {len(comments_flat)} flat comments")
    print(f"  Group: {data.get('group_name', 'Unknown')}")
    print(f"  Extraction time: {data.get('extraction_time', 'Unknown')}")

    return data


def analyze_posts(posts: list, classifier: FeedbackClassifier,
                  sentiment_analyzer: SentimentAnalyzer) -> list:
    """Run classification and sentiment analysis on all posts."""
    results = []
    for i, post in enumerate(posts):
        if i > 0 and i % 50 == 0:
            print(f"  Processed {i}/{len(posts)} posts...")

        # Classification
        classification = classifier.classify_post(post)

        # Sentiment
        sentiment = sentiment_analyzer.analyze_post(post)

        result = {
            **post,
            "classification": classification,
            "sentiment": sentiment,
        }
        results.append(result)

    print(f"  Completed analysis of {len(results)} posts.")
    return results


def extract_competitor_mentions(posts: list) -> Dict[str, int]:
    """Count mentions of competitor brands."""
    competitors = {
        "Bambu Lab": [r"bambu\s*lab", r"bambu", r"bamboo\s*lab"],
        "Prusa": [r"prusa", r"prusa\s*xl", r"prusa\s*mk"],
        "Creality": [r"creality", r"ender", r"cr-?10", r"k1"],
        "Voron": [r"voron"],
        "Elegoo": [r"elegoo"],
        "AnkerMake": [r"anker\s*make", r"ankermake"],
        "Qidi": [r"qidi"],
        "FlashForge": [r"flash\s*forge", r"flashforge"],
        "Raise3D": [r"raise\s*3d", r"raise3d"],
    }

    counts = Counter()
    for post in posts:
        text = (post.get("text", "") or "").lower()
        # Include comment text
        for comment in post.get("comments", []):
            text += " " + (comment.get("text", "") or "").lower()

        for brand, patterns in competitors.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    counts[brand] += 1
                    break  # Count each brand once per post

    return dict(counts.most_common())


def extract_comparison_dimensions(posts: list) -> list:
    """Identify what dimensions users compare on."""
    dimensions = {
        "Price / Value": [r"price", r"cost", r"cheaper", r"expensive", r"value", r"worth"],
        "Print Quality": [r"quality", r"print quality", r"detail", r"resolution"],
        "Multi-color Capability": [r"multi.?color", r"tool.?change", r"ams", r"multi.?material"],
        "Software Ecosystem": [r"software", r"slicer", r"orca", r"bambu studio", r"firmware"],
        "Reliability": [r"reliable", r"reliability", r"uptime", r"fail rate"],
        "Speed": [r"speed", r"fast", r"slow", r"print speed"],
        "Build Volume": [r"build volume", r"bed size", r"print size", r"larger"],
        "Noise": [r"noise", r"loud", r"quiet", r"silent", r"sound"],
        "Community / Support": [r"community", r"support", r"customer service", r"warranty"],
    }

    found = []
    for dim, patterns in dimensions.items():
        for post in posts:
            text = (post.get("text", "") or "").lower()
            for pat in patterns:
                if re.search(pat, text):
                    found.append(dim)
                    break
            else:
                continue
            break

    return list(dict.fromkeys(found))  # deduplicate preserving order


def extract_keywords_frequency(posts: list, sentiment_type: str,
                               sentiment_analyzer: SentimentAnalyzer) -> list:
    """Extract most frequent positive or negative keywords from posts."""
    if sentiment_type == "positive":
        word_lists = (sentiment_analyzer.positive_strong +
                      sentiment_analyzer.positive_moderate)
    else:
        word_lists = (sentiment_analyzer.negative_strong +
                      sentiment_analyzer.negative_moderate)

    counter = Counter()
    for post in posts:
        text_lower = (post.get("text", "") or "").lower()
        for word in word_lists:
            if word in text_lower:
                counter[word] += 1

    return counter.most_common(20)


def build_summary(analyzed_posts: list, raw_data: dict,
                  classifier: FeedbackClassifier,
                  sentiment_analyzer: SentimentAnalyzer) -> dict:
    """Build comprehensive summary statistics from analyzed posts."""
    total_posts = len(analyzed_posts)

    # Basic stats
    unique_authors = len(set(p.get("author", "") for p in analyzed_posts if p.get("author")))
    total_reactions = sum(p.get("reactions", 0) or 0 for p in analyzed_posts)
    total_comment_count = sum(p.get("comment_count", 0) or 0 for p in analyzed_posts)
    posts_with_images = sum(1 for p in analyzed_posts if p.get("has_image"))
    posts_with_videos = sum(1 for p in analyzed_posts if p.get("has_video"))
    posts_text_only = total_posts - posts_with_images - posts_with_videos
    # Some posts might have both image and video; adjust
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

    # Top engagement posts
    sorted_by_reactions = sorted(analyzed_posts, key=lambda p: p.get("reactions", 0) or 0,
                                 reverse=True)
    top_engagement = [
        {
            "text": p.get("text", ""),
            "author": p.get("author", ""),
            "reactions": p.get("reactions", 0),
            "comment_count": p.get("comment_count", 0),
        }
        for p in sorted_by_reactions[:10]
    ]

    # Category distributions
    top_cat_counter = Counter()
    l1_cat_counter = Counter()
    l2_cat_counter = Counter()
    category_posts = defaultdict(list)  # top_code -> list of posts

    for post in analyzed_posts:
        cls = post.get("classification", {})
        for cat in cls.get("categories", []):
            code = cat["code"]
            top_code = get_top_from_code(code)
            l1_code = get_l1_from_code(code)

            top_cat_counter[top_code] += 1
            l1_cat_counter[l1_code] += 1
            if "." in code:
                l2_cat_counter[code] += 1

            category_posts[top_code].append(post)

    # Order top categories
    top_order = ["H", "S", "M", "U", "P", "O"]
    top_category_distribution = {}
    for code in top_order:
        if code in top_cat_counter:
            top_category_distribution[code] = top_cat_counter[code]

    # Sentiment distribution
    sentiment_counter = Counter()
    satisfaction_counter = Counter()
    for post in analyzed_posts:
        sent = post.get("sentiment", {})
        sentiment_counter[sent.get("sentiment", "neutral")] += 1
        satisfaction_counter[str(sent.get("satisfaction_score", 3))] += 1

    avg_satisfaction = sum(
        int(k) * v for k, v in satisfaction_counter.items()
    ) / max(total_posts, 1)

    # Common issues (3+ unique authors)
    issue_authors = defaultdict(set)
    issue_reactions = defaultdict(list)
    for post in analyzed_posts:
        cls = post.get("classification", {})
        author = post.get("author", "")
        reactions = post.get("reactions", 0) or 0
        for cat in cls.get("categories", []):
            code = cat["code"]
            if code.startswith(("H", "S", "M", "U")) and "." in code:
                l1 = get_l1_from_code(code)
                issue_authors[l1].add(author)
                issue_reactions[l1].append(reactions)

    common_issues = []
    for code, authors in issue_authors.items():
        if len(authors) >= 3:
            avg_react = sum(issue_reactions[code]) / max(len(issue_reactions[code]), 1)
            common_issues.append({
                "code": code,
                "name": L1_NAMES.get(code, code),
                "count": l1_cat_counter.get(code, 0),
                "unique_authors": len(authors),
                "avg_reactions": avg_react,
            })
    common_issues.sort(key=lambda x: x["count"], reverse=True)

    # Category examples (representative posts per top-level category)
    category_examples = {}
    for top_code in ["H", "S", "M", "U"]:
        posts_in_cat = category_posts.get(top_code, [])
        # Sort by reactions, pick top examples
        sorted_posts = sorted(posts_in_cat,
                              key=lambda p: p.get("reactions", 0) or 0,
                              reverse=True)
        category_examples[top_code] = [
            {
                "text": p.get("text", ""),
                "author": p.get("author", ""),
                "reactions": p.get("reactions", 0),
            }
            for p in sorted_posts[:5]
        ]

    # Competitor mentions
    competitor_mentions = extract_competitor_mentions(analyzed_posts)
    comparison_dimensions = extract_comparison_dimensions(analyzed_posts)

    # Feature requests
    feature_cats = {k: v for k, v in l1_cat_counter.items() if k.startswith("S4")}
    # Also include general feature request subcategories
    feature_l2 = {k: v for k, v in l2_cat_counter.items() if k.startswith("S4")}
    feature_requests = []
    for code, count in sorted(feature_l2.items(), key=lambda x: x[1], reverse=True):
        feature_requests.append({
            "code": code,
            "name": L1_NAMES.get(code, code),
            "count": count,
        })
    # Add any L1-level feature mentions not covered
    if not feature_requests and feature_cats:
        for code, count in sorted(feature_cats.items(), key=lambda x: x[1], reverse=True):
            feature_requests.append({
                "code": code,
                "name": L1_NAMES.get(code, code),
                "count": count,
            })

    # Keywords
    positive_keywords = extract_keywords_frequency(analyzed_posts, "positive", sentiment_analyzer)
    negative_keywords = extract_keywords_frequency(analyzed_posts, "negative", sentiment_analyzer)

    # Representative quotes
    positive_posts = [p for p in analyzed_posts
                      if p.get("sentiment", {}).get("sentiment") == "positive"]
    negative_posts = [p for p in analyzed_posts
                      if p.get("sentiment", {}).get("sentiment") == "negative"]

    positive_posts.sort(key=lambda p: p.get("sentiment", {}).get("positive_score", 0), reverse=True)
    negative_posts.sort(key=lambda p: p.get("sentiment", {}).get("negative_score", 0), reverse=True)

    positive_quotes = [
        {"text": p.get("text", ""), "author": p.get("author", ""),
         "reactions": p.get("reactions", 0)}
        for p in positive_posts[:5]
    ]
    negative_quotes = [
        {"text": p.get("text", ""), "author": p.get("author", ""),
         "reactions": p.get("reactions", 0)}
        for p in negative_posts[:5]
    ]

    # Constructive quotes: mixed sentiment or those with feature requests
    constructive_posts = [p for p in analyzed_posts
                          if p.get("sentiment", {}).get("sentiment") == "mixed"
                          or "S4" in str(p.get("classification", {}).get("l1_categories", []))]
    constructive_posts.sort(key=lambda p: p.get("reactions", 0) or 0, reverse=True)
    constructive_quotes = [
        {"text": p.get("text", ""), "author": p.get("author", ""),
         "reactions": p.get("reactions", 0)}
        for p in constructive_posts[:5]
    ]

    # Key findings (auto-generated)
    key_findings = _generate_key_findings(
        total_posts, top_cat_counter, l1_cat_counter,
        sentiment_counter, avg_satisfaction, common_issues
    )

    # Top issues and positives
    issue_l1 = [(k, v) for k, v in l1_cat_counter.items()
                if k[0] in ("H", "S", "M", "U")]
    issue_l1.sort(key=lambda x: x[1], reverse=True)
    top_issues = [{"code": k, "name": L1_NAMES.get(k, k), "count": v}
                  for k, v in issue_l1[:3]]

    positive_l1 = [(k, v) for k, v in l1_cat_counter.items() if k.startswith("P")]
    positive_l1.sort(key=lambda x: x[1], reverse=True)
    top_positives = [{"code": k, "name": L1_NAMES.get(k, k), "count": v}
                     for k, v in positive_l1[:3]]

    return {
        "basic_stats": basic_stats,
        "top_engagement_posts": top_engagement,
        "top_category_distribution": top_category_distribution,
        "l1_category_distribution": dict(l1_cat_counter.most_common()),
        "l2_category_distribution": dict(l2_cat_counter.most_common()),
        "sentiment_distribution": dict(sentiment_counter),
        "satisfaction_distribution": dict(satisfaction_counter),
        "avg_satisfaction": avg_satisfaction,
        "common_issues": common_issues,
        "category_examples": category_examples,
        "competitor_mentions": competitor_mentions,
        "comparison_dimensions": comparison_dimensions,
        "feature_requests": feature_requests,
        "positive_keywords": positive_keywords,
        "negative_keywords": negative_keywords,
        "positive_quotes": positive_quotes,
        "negative_quotes": negative_quotes,
        "constructive_quotes": constructive_quotes,
        "key_findings": key_findings,
        "top_issues": top_issues,
        "top_positives": top_positives,
    }


def _generate_key_findings(total_posts, top_cat_counter, l1_cat_counter,
                           sentiment_counter, avg_satisfaction, common_issues):
    """Auto-generate key findings text."""
    findings = []

    # Overall sentiment
    total_sent = sum(sentiment_counter.values())
    if total_sent > 0:
        pos_pct = sentiment_counter.get("positive", 0) / total_sent * 100
        neg_pct = sentiment_counter.get("negative", 0) / total_sent * 100
        findings.append(
            f"Overall sentiment: {pos_pct:.0f}% positive, {neg_pct:.0f}% negative, "
            f"average satisfaction {avg_satisfaction:.1f}/5.0"
        )

    # Top problem area
    issue_cats = [(k, v) for k, v in top_cat_counter.items() if k in ("H", "S", "M", "U")]
    if issue_cats:
        issue_cats.sort(key=lambda x: x[1], reverse=True)
        top_issue = issue_cats[0]
        findings.append(
            f"Most reported issue area: {CATEGORY_NAMES.get(top_issue[0], top_issue[0])} "
            f"({top_issue[1]} mentions across {total_posts} posts)"
        )

    # Most common specific issue
    if common_issues:
        top_common = common_issues[0]
        findings.append(
            f"Most widespread issue: {top_common['name']} "
            f"(reported by {top_common['unique_authors']} unique users)"
        )

    # Positive aspects
    pos_count = top_cat_counter.get("P", 0)
    if pos_count:
        findings.append(
            f"Positive feedback: {pos_count} posts with positive mentions "
            f"({pos_count / max(total_posts, 1) * 100:.0f}% of all posts)"
        )

    # Total analyzed
    findings.append(f"Analyzed {total_posts} posts from the Snapmaker U1 Official Group")

    return findings


def save_intermediate_json(analyzed_posts: list, summary: dict,
                           metadata: dict, output_path: str):
    """Save intermediate analysis results to JSON."""

    def _make_serializable(obj):
        """Convert sets and other non-serializable types."""
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
                "classification": {
                    "categories": p["classification"]["categories"],
                    "l1_categories": p["classification"]["l1_categories"],
                    "top_categories": p["classification"]["top_categories"],
                },
                "sentiment": {
                    "sentiment": p["sentiment"]["sentiment"],
                    "satisfaction_score": p["sentiment"]["satisfaction_score"],
                    "positive_score": p["sentiment"]["positive_score"],
                    "negative_score": p["sentiment"]["negative_score"],
                },
            }
            for p in analyzed_posts
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=_make_serializable)

    print(f"Intermediate results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Snapmaker U1 Facebook Feedback Analyzer"
    )
    parser.add_argument("input_file", help="Path to Facebook JSON data file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output directory (default: ./output/)")
    parser.add_argument("--llm", default=None,
                        help="LLM provider for enhanced classification (claude/openai/qwen)")
    parser.add_argument("--api-key", default=None,
                        help="API key for LLM provider")

    args = parser.parse_args()

    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    raw_data = load_data(args.input_file)
    posts = raw_data.get("posts", [])

    if not posts:
        print("ERROR: No posts found in input file.")
        sys.exit(1)

    # Initialize engines
    print("\nInitializing classification engine...")
    classifier = FeedbackClassifier()
    sentiment_analyzer = SentimentAnalyzer()

    if args.llm:
        print(f"NOTE: LLM enhancement ({args.llm}) requested but not yet implemented.")
        print("Falling back to keyword-based classification.\n")

    # Analyze
    print(f"\nAnalyzing {len(posts)} posts...")
    analyzed_posts = analyze_posts(posts, classifier, sentiment_analyzer)

    # Build summary
    print("\nBuilding summary statistics...")
    metadata = {
        "group_url": raw_data.get("group_url", ""),
        "group_name": raw_data.get("group_name", "Snapmaker U1 Official Group"),
        "extraction_time": raw_data.get("extraction_time", ""),
        "total_posts": raw_data.get("total_posts", len(posts)),
        "total_comments": raw_data.get("total_comments", 0),
    }
    summary = build_summary(analyzed_posts, raw_data, classifier, sentiment_analyzer)

    # Save intermediate JSON
    json_path = os.path.join(output_dir, "analysis_result.json")
    save_intermediate_json(analyzed_posts, summary, metadata, json_path)

    # Generate report
    print("\nGenerating PPTX report...")
    analysis_data = {
        "posts": analyzed_posts,
        "summary": summary,
        "metadata": metadata,
    }
    report_gen = ReportGenerator(analysis_data)
    pptx_path = os.path.join(output_dir, "report.pptx")
    report_gen.generate(pptx_path)

    print(f"\n{'='*60}")
    print("Analysis complete!")
    print(f"  Intermediate JSON: {json_path}")
    print(f"  PPTX Report: {pptx_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
