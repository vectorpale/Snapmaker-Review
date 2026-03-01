"""
Keyword + rule-based multi-label classifier for Snapmaker U1 feedback.

Classifies posts/comments into the hierarchical category system:
  H (Hardware), S (Software), M (Material), U (User Experience),
  P (Positive), O (Other)
"""

import json
import re
import os
from typing import Dict, List, Set, Tuple


# Category display names for reports
CATEGORY_NAMES = {
    "H": "Hardware",
    "S": "Software",
    "M": "Material",
    "U": "User Experience",
    "P": "Positive",
    "O": "Other",
}

# Subcategory level-1 names
L1_NAMES = {
    "H1": "Toolhead Issues",
    "H2": "Print Quality Issues",
    "H3": "Mechanical Structure",
    "H4": "Electrical/Connection",
    "S1": "Snapmaker Orca (Slicer)",
    "S2": "Firmware",
    "S3": "App / Remote Control",
    "S4": "Feature Requests",
    "M1": "Material Compatibility",
    "M2": "Filament Path / Feeding",
    "U1": "Purchase / Shipping",
    "U2": "Unboxing / Setup",
    "U3": "Usage Experience",
    "U4": "After-sales / Support",
    "P1": "Good print quality",
    "P2": "Multi-color impressive",
    "P3": "Fast tool change / less waste",
    "P4": "Good value for money",
    "P5": "Easy setup",
    "P6": "Show & tell",
    "P7": "Community support",
    "O1": "General questions",
    "O2": "MOD/modification",
    "O3": "Competitor comparison",
    "O4": "Irrelevant content",
}


class FeedbackClassifier:
    """Multi-label classifier using keyword dictionaries and regex patterns."""

    def __init__(self, keywords_dir: str = None):
        if keywords_dir is None:
            keywords_dir = os.path.join(os.path.dirname(__file__), "keywords")
        self.keywords_dir = keywords_dir
        self.rules = {}  # category_code -> {keywords_en, keywords_zh, patterns}
        self._load_all_keywords()
        self._build_other_rules()
        self._build_positive_rules()

    def _load_all_keywords(self):
        """Load keyword dictionaries from JSON files."""
        category_files = {
            "hardware": os.path.join(self.keywords_dir, "hardware.json"),
            "software": os.path.join(self.keywords_dir, "software.json"),
            "material": os.path.join(self.keywords_dir, "material.json"),
            "ux": os.path.join(self.keywords_dir, "ux.json"),
        }

        for _cat_name, filepath in category_files.items():
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            for _l1_code, l1_data in data.items():
                if "subcategories" in l1_data:
                    for l2_code, l2_data in l1_data["subcategories"].items():
                        self.rules[l2_code] = {
                            "keywords_en": [
                                kw.lower() for kw in l2_data.get("keywords_en", [])
                            ],
                            "keywords_zh": l2_data.get("keywords_zh", []),
                            "patterns": [
                                re.compile(p, re.IGNORECASE)
                                for p in l2_data.get("patterns", [])
                            ],
                            "name": l2_data.get("name", ""),
                            "name_zh": l2_data.get("name_zh", ""),
                        }

    def _build_positive_rules(self):
        """Load positive feedback keywords."""
        filepath = os.path.join(self.keywords_dir, "positive.json")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for code, cat_data in data.items():
            self.rules[code] = {
                "keywords_en": [kw.lower() for kw in cat_data.get("keywords_en", [])],
                "keywords_zh": cat_data.get("keywords_zh", []),
                "patterns": [
                    re.compile(p, re.IGNORECASE)
                    for p in cat_data.get("patterns", [])
                ],
                "name": cat_data.get("name", ""),
                "name_zh": cat_data.get("name_zh", ""),
            }

    def _build_other_rules(self):
        """Build rules for O (Other) categories inline."""
        other_rules = {
            "O1": {
                "keywords_en": [
                    "should i buy", "which one", "recommend", "advice",
                    "what do you think", "help me decide", "buying advice",
                    "purchase advice", "suggestion", "what accessories",
                    "compatible with", "best settings", "recommend settings",
                    "tips for", "any tips", "anyone know",
                ],
                "keywords_zh": [
                    "購買建議", "推薦", "配件推薦", "建議", "有人知道",
                ],
                "patterns": [
                    r"(?:should|would you)\s*(?:i|recommend|suggest)",
                    r"(?:any|some)\s*(?:tips|advice|suggestion|recommend)",
                    r"(?:best|good|recommend)\s*(?:setting|config|accessori|filament)",
                    r"(?:what|which)\s*(?:filament|nozzle|accessori|setting)",
                ],
            },
            "O2": {
                "keywords_en": [
                    "mod", "modding", "modification", "modified", "upgrade",
                    "diy", "custom", "3d printed part", "printed upgrade",
                    "aftermarket", "custom mount", "remix", "redesign",
                    "printed mod", "hack", "mod for",
                ],
                "keywords_zh": [
                    "改裝", "改造", "升級", "DIY", "自製",
                ],
                "patterns": [
                    r"(?:3d\s*)?print.*(?:mod|upgrade|mount|bracket|part|holder|adapter)",
                    r"(?:mod|modif|custom|diy|upgrade).*(?:u1|snapmaker|printer)",
                    r"(?:design|remix|make|made).*(?:mount|bracket|holder|adapter|upgrade)",
                ],
            },
            "O3": {
                "keywords_en": [
                    "bambu lab", "bambu", "bamboo", "prusa", "prusa xl",
                    "creality", "ender", "voron", "elegoo", "anker make",
                    "ankermake", "compared to", "vs ", "versus", "competitor",
                    "better than", "worse than", "switch from", "switched from",
                    "came from", "moving from",
                ],
                "keywords_zh": [
                    "Bambu", "Prusa", "比較", "對比", "競品",
                ],
                "patterns": [
                    r"(?:bambu|prusa|creality|ender|voron|elegoo|anker\s*make)",
                    r"(?:compare|vs|versus|better than|worse than)",
                    r"(?:switch|switched|came|moving|moved)\s*(?:from|to)",
                ],
            },
            "O4": {
                "keywords_en": [],
                "keywords_zh": [],
                "patterns": [],
            },
        }

        for code, rule_data in other_rules.items():
            self.rules[code] = {
                "keywords_en": [kw.lower() for kw in rule_data["keywords_en"]],
                "keywords_zh": rule_data["keywords_zh"],
                "patterns": [
                    re.compile(p, re.IGNORECASE) for p in rule_data["patterns"]
                ],
                "name": L1_NAMES.get(code, ""),
                "name_zh": "",
            }

    def _text_matches_rule(self, text_lower: str, text_original: str, rule: dict) -> Tuple[bool, float]:
        """
        Check if text matches a rule. Returns (matched, confidence_score).
        Score is between 0 and 1.
        """
        score = 0.0
        matches = 0

        # Check English keywords
        for kw in rule["keywords_en"]:
            if kw in text_lower:
                matches += 1
                score += 0.4

        # Check Chinese keywords
        for kw in rule["keywords_zh"]:
            if kw in text_original:
                matches += 1
                score += 0.4

        # Check regex patterns
        for pattern in rule["patterns"]:
            if pattern.search(text_lower) or pattern.search(text_original):
                matches += 1
                score += 0.5

        if matches == 0:
            return False, 0.0

        # Cap score at 1.0
        confidence = min(score, 1.0)
        return True, confidence

    def classify(self, text: str, comments_text: str = "") -> Dict[str, List[dict]]:
        """
        Classify a post (with optional comment text) into categories.

        Returns dict with:
          - categories: list of {code, name, confidence}
          - l1_categories: set of level-1 category codes (e.g., H1, S2)
          - top_categories: set of top-level category codes (e.g., H, S, P)
        """
        # Combine post text + comments for analysis
        combined = text
        if comments_text:
            combined = text + " " + comments_text

        text_lower = combined.lower()
        text_original = combined

        matched_categories = []

        for code, rule in self.rules.items():
            matched, confidence = self._text_matches_rule(text_lower, text_original, rule)
            if matched:
                matched_categories.append({
                    "code": code,
                    "name": rule.get("name", ""),
                    "name_zh": rule.get("name_zh", ""),
                    "confidence": round(confidence, 3),
                })

        # Derive L1 and top-level categories
        l1_codes = set()
        top_codes = set()
        for cat in matched_categories:
            code = cat["code"]
            if "." in code:
                l1 = code.split(".")[0]
            else:
                l1 = code
            l1_codes.add(l1)
            top_codes.add(l1[0])

        # If nothing matched, mark as O4 (irrelevant/unclassified)
        if not matched_categories:
            matched_categories.append({
                "code": "O4",
                "name": "Irrelevant/unclassified content",
                "name_zh": "不相关内容",
                "confidence": 0.1,
            })
            l1_codes.add("O4")
            top_codes.add("O")

        # Sort by confidence descending
        matched_categories.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "categories": matched_categories,
            "l1_categories": sorted(l1_codes),
            "top_categories": sorted(top_codes),
        }

    def classify_post(self, post: dict) -> dict:
        """
        Classify a single post dict from the Facebook JSON data.

        Args:
            post: dict with at least 'text' field, optionally 'comments'

        Returns:
            Classification result dict.
        """
        text = post.get("text", "") or ""

        # Combine visible comments text
        comments_text_parts = []
        for comment in post.get("comments", []):
            ct = comment.get("text", "") or ""
            if ct:
                comments_text_parts.append(ct)
        comments_text = " ".join(comments_text_parts)

        return self.classify(text, comments_text)


def get_l1_from_code(code: str) -> str:
    """Extract L1 category from a detailed code. E.g., 'H1.2' -> 'H1'."""
    if "." in code:
        return code.split(".")[0]
    return code


def get_top_from_code(code: str) -> str:
    """Extract top-level category from a code. E.g., 'H1.2' -> 'H'."""
    return code[0] if code else ""
