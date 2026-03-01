"""
Sentiment analysis module for Snapmaker U1 feedback.

Uses a lexicon-based approach with:
  - Positive/negative word dictionaries (strong/moderate/mild)
  - Negation handling
  - Intensifier detection
  - Question detection
  - Weighted scoring based on reactions
"""

import json
import os
import re
from typing import Dict, Tuple


class SentimentAnalyzer:
    """Lexicon-based sentiment analyzer for English + Traditional Chinese text."""

    def __init__(self, keywords_dir: str = None):
        if keywords_dir is None:
            keywords_dir = os.path.join(os.path.dirname(__file__), "keywords")
        self.keywords_dir = keywords_dir
        self._load_lexicon()

    def _load_lexicon(self):
        """Load sentiment lexicon from JSON file."""
        filepath = os.path.join(self.keywords_dir, "sentiment.json")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.positive_strong = [w.lower() for w in data["positive_words"]["strong"]]
        self.positive_moderate = [w.lower() for w in data["positive_words"]["moderate"]]
        self.positive_mild = [w.lower() for w in data["positive_words"]["mild"]]
        self.negative_strong = [w.lower() for w in data["negative_words"]["strong"]]
        self.negative_moderate = [w.lower() for w in data["negative_words"]["moderate"]]
        self.negative_mild = [w.lower() for w in data["negative_words"]["mild"]]
        self.negation_words = [w.lower() for w in data["negation_words"]]
        self.intensifiers = [w.lower() for w in data["intensifiers"]]
        self.question_indicators = [w.lower() for w in data["question_indicators"]]

    def _count_matches(self, text_lower: str, text_original: str, word_list: list) -> int:
        """Count how many words from the list appear in the text."""
        count = 0
        for word in word_list:
            # Check both lower and original for Chinese characters
            if word in text_lower or word in text_original:
                count += 1
        return count

    def _has_negation_before(self, text_lower: str, word: str) -> bool:
        """Check if there's a negation word within 3 words before the target word."""
        idx = text_lower.find(word)
        if idx < 0:
            return False
        # Get the preceding context (up to 30 chars before)
        prefix = text_lower[max(0, idx - 30):idx]
        for neg in self.negation_words:
            if neg in prefix:
                return True
        return False

    def _is_question(self, text_lower: str) -> bool:
        """Detect if text is primarily a question."""
        question_score = 0
        if "?" in text_lower:
            question_score += 2
        for indicator in self.question_indicators:
            if indicator in text_lower:
                question_score += 1

        # Heuristic: if question score is high relative to text, it's a question
        return question_score >= 2

    def analyze(self, text: str, comments_text: str = "") -> Dict:
        """
        Analyze sentiment of a post text (optionally with comments).

        Returns:
            dict with:
              - sentiment: "positive" | "negative" | "neutral" | "mixed"
              - satisfaction_score: 1-5 integer
              - positive_score: float
              - negative_score: float
              - details: dict with match counts
        """
        combined = text
        if comments_text:
            combined = text + " " + comments_text

        text_lower = combined.lower()
        text_original = combined

        # Count positive matches
        pos_strong = self._count_matches(text_lower, text_original, self.positive_strong)
        pos_moderate = self._count_matches(text_lower, text_original, self.positive_moderate)
        pos_mild = self._count_matches(text_lower, text_original, self.positive_mild)

        # Count negative matches
        neg_strong = self._count_matches(text_lower, text_original, self.negative_strong)
        neg_moderate = self._count_matches(text_lower, text_original, self.negative_moderate)
        neg_mild = self._count_matches(text_lower, text_original, self.negative_mild)

        # Check for intensifiers
        has_intensifier = any(w in text_lower for w in self.intensifiers)
        intensifier_mult = 1.3 if has_intensifier else 1.0

        # Check for negation context (simple check)
        negated = False
        for neg in self.negation_words:
            if neg in text_lower:
                # Check if negation is near positive words
                for pw in self.positive_strong + self.positive_moderate:
                    if self._has_negation_before(text_lower, pw) and pw in text_lower:
                        negated = True
                        break
            if negated:
                break

        # Calculate weighted scores
        positive_score = (pos_strong * 3.0 + pos_moderate * 2.0 + pos_mild * 1.0) * intensifier_mult
        negative_score = (neg_strong * 3.0 + neg_moderate * 2.0 + neg_mild * 1.0) * intensifier_mult

        # Adjust for negation (flip some positive to negative)
        if negated:
            positive_score *= 0.3
            negative_score += 1.0

        # Check if it's a question
        is_question = self._is_question(text_lower)

        # Determine sentiment label
        sentiment, satisfaction = self._compute_sentiment(
            positive_score, negative_score, is_question
        )

        return {
            "sentiment": sentiment,
            "satisfaction_score": satisfaction,
            "positive_score": round(positive_score, 2),
            "negative_score": round(negative_score, 2),
            "is_question": is_question,
            "details": {
                "positive_strong": pos_strong,
                "positive_moderate": pos_moderate,
                "positive_mild": pos_mild,
                "negative_strong": neg_strong,
                "negative_moderate": neg_moderate,
                "negative_mild": neg_mild,
                "has_intensifier": has_intensifier,
                "negated": negated,
            },
        }

    def _compute_sentiment(
        self, positive_score: float, negative_score: float, is_question: bool
    ) -> Tuple[str, int]:
        """Determine sentiment label and satisfaction score."""
        diff = positive_score - negative_score
        total = positive_score + negative_score

        # Pure question with no strong sentiment
        if is_question and total < 2.0:
            return "neutral", 3

        # Both positive and negative present
        if positive_score >= 2.0 and negative_score >= 2.0:
            return "mixed", 3

        # Strong positive
        if diff > 4.0:
            return "positive", 5
        if diff > 2.0:
            return "positive", 4

        # Strong negative
        if diff < -4.0:
            return "negative", 1
        if diff < -2.0:
            return "negative", 2

        # Mild positive
        if diff > 0.5:
            return "positive", 4

        # Mild negative
        if diff < -0.5:
            return "negative", 2

        # Neutral
        return "neutral", 3

    def analyze_post(self, post: dict) -> Dict:
        """
        Analyze sentiment of a single post dict.

        Args:
            post: dict with at least 'text' field, optionally 'comments'

        Returns:
            Sentiment analysis result dict.
        """
        text = post.get("text", "") or ""

        comments_text_parts = []
        for comment in post.get("comments", []):
            ct = comment.get("text", "") or ""
            if ct:
                comments_text_parts.append(ct)
        comments_text = " ".join(comments_text_parts)

        result = self.analyze(text, comments_text)

        # Adjust satisfaction based on reactions (high reactions on negative = more weight)
        reactions = post.get("reactions", 0) or 0
        if reactions > 20 and result["sentiment"] == "negative":
            # High-reaction negative post might be slightly more impactful
            result["weight"] = min(reactions / 10, 5.0)
        elif reactions > 20 and result["sentiment"] == "positive":
            result["weight"] = min(reactions / 10, 5.0)
        else:
            result["weight"] = max(reactions / 10, 1.0)

        return result
