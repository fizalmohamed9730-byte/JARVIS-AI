"""Email categorization and importance scoring using rule-based heuristics."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmailCategorizer:
    """Categorizes emails and scores their importance using rule-based analysis.

    Categories: important, work, personal, spam, newsletter, social, promotional.
    Uses keyword matching, header analysis, and structural heuristics.
    """

    # Keyword sets for classification
    _IMPORTANT_KEYWORDS = frozenset({
        "urgent", "action required", "deadline", "asap", "important",
        "critical", "immediately", "time-sensitive", "expires", "expiring",
        "overdue", "final notice", "last chance", "emergency",
    })

    _SPAM_SIGNALS = frozenset({
        "unsubscribe", "click here", "limited time offer", "act now",
        "free gift", "congratulations", "you've won", "winner",
        "no obligation", "risk free", "special promotion", "buy now",
        "discount", "viagra", "casino", "lottery", "nigerian prince",
    })

    _NEWSLETTER_SIGNALS = frozenset({
        "newsletter", "weekly digest", "monthly update", "roundup",
        "digest", "subscription", "mailing list", "broadcast",
    })

    _SOCIAL_SIGNALS = frozenset({
        "notification", "friend request", "followed you", "mentioned you",
        "shared a", "tagged you", "commented on", "liked your",
        "linkedin", "facebook", "twitter", "instagram",
    })

    _WORK_SENDERS = frozenset({
        "noreply", "no-reply", "donotreply", "notifications",
        "alerts", "monitoring", "jenkins", "github", "gitlab",
        "jira", "confluence", "slack", "teams", "asana",
    })

    _PERSONAL_SENDERS = frozenset({
        "mom", "dad", "family", "friend", "buddy",
    })

    # Scoring weights
    _WEIGHTS = {
        "sender_match": 0.3,
        "subject_keywords": 0.3,
        "body_keywords": 0.2,
        "recency": 0.1,
        "engagement": 0.1,
    }

    def categorize(self, email_data: Dict[str, Any]) -> str:
        """Categorize an email into one of: important, work, personal,
        newsletter, social, promotional, spam, or general.

        Args:
            email_data: Email dict with at minimum ``from``, ``subject``,
                and optionally ``body`` keys.

        Returns:
            Category string.
        """
        sender = (email_data.get("from", "") or "").lower()
        subject = (email_data.get("subject", "") or "").lower()
        body = (email_data.get("body", "") or "").lower()

        scores: Dict[str, float] = {
            "important": 0.0,
            "spam": 0.0,
            "newsletter": 0.0,
            "social": 0.0,
            "work": 0.0,
            "personal": 0.0,
            "promotional": 0.0,
        }

        # Spam check first (high confidence)
        spam_count = sum(1 for s in self._SPAM_SIGNALS if s in subject or s in body[:500])
        if spam_count >= 3:
            return "spam"

        # Newsletter check
        newsletter_count = sum(1 for s in self._NEWSLETTER_SIGNALS if s in subject or s in body[:200])
        if newsletter_count >= 2:
            return "newsletter"

        # Social check
        social_count = sum(1 for s in self._SOCIAL_SIGNALS if s in subject or s in body[:200])
        if social_count >= 2:
            return "social"

        # Important check
        important_count = sum(1 for s in self._IMPORTANT_KEYWORDS if s in subject)
        if important_count >= 1:
            return "important"

        # Sender-based classification
        sender_lower = sender
        if any(ws in sender_lower for ws in self._WORK_SENDERS):
            scores["work"] += 0.5
        if any(ps in sender_lower for ps in self._PERSONAL_SENDERS):
            scores["personal"] += 0.5

        # Promotional signals
        promo_keywords = {"sale", "offer", "deal", "coupon", "% off", "save", "free shipping"}
        promo_count = sum(1 for s in promo_keywords if s in subject)
        if promo_count >= 1:
            scores["promotional"] += 0.6

        # Return highest scoring category
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] > 0.3:
            return best

        return "general"

    def score_importance(self, email_data: Dict[str, Any]) -> float:
        """Score email importance on a 0.0 to 1.0 scale.

        Higher scores indicate more important emails. Factors include:
        - Keyword urgency signals
        - Sender reputation (known contacts score higher)
        - Recency (newer emails score higher)
        - Engagement signals (replies, forwards)
        """
        sender = (email_data.get("from", "") or "").lower()
        subject = (email_data.get("subject", "") or "").lower()
        body = (email_data.get("body", "") or "").lower()
        date_str = email_data.get("date", "")

        score = 0.0

        # Keyword urgency (0-0.35)
        important_hits = sum(1 for s in self._IMPORTANT_KEYWORDS if s in subject or s in body[:500])
        keyword_score = min(important_hits * 0.12, 0.35)
        score += keyword_score

        # Spam reduces importance (-0.3)
        spam_hits = sum(1 for s in self._SPAM_SIGNALS if s in subject or s in body[:300])
        spam_penalty = min(spam_hits * 0.1, 0.3)
        score -= spam_penalty

        # Recency (0-0.2)
        if date_str:
            try:
                # Parse various date formats
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_str)
                hours_ago = (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600
                if hours_ago < 1:
                    score += 0.2
                elif hours_ago < 24:
                    score += 0.15
                elif hours_ago < 72:
                    score += 0.1
                elif hours_ago < 168:
                    score += 0.05
            except Exception:
                pass

        # Engagement signals (0-0.15)
        engagement = {"reply", "reply to", "forward", "fw:", "re:"}
        engagement_hits = sum(1 for s in engagement if s in subject)
        score += min(engagement_hits * 0.075, 0.15)

        # Work context bonus (0-0.1)
        if any(ws in sender for ws in self._WORK_SENDERS):
            score += 0.1

        # Attachment bonus (0-0.1)
        if email_data.get("attachments"):
            score += 0.1

        # All-caps subject penalty
        if subject and subject.isupper() and len(subject) > 5:
            score -= 0.1

        # Exclamation mark penalty for excessive use
        if subject.count("!") > 2:
            score -= 0.05

        return max(0.0, min(1.0, score))

    def extract_action_items(self, email_data: Dict[str, Any]) -> List[str]:
        """Extract potential action items from email content.

        Looks for imperative sentences, TODO markers, deadline mentions,
        and task-like patterns.
        """
        body = email_data.get("body", "") or ""
        subject = email_data.get("subject", "") or ""
        text = f"{subject}\n{body}"

        action_items: List[str] = []

        # TODO/FIXME markers
        todo_pattern = re.compile(r"(?:TODO|FIXME|ACTION|ACTION ITEM|TASK)[:\s]+(.+)", re.IGNORECASE)
        for match in todo_pattern.finditer(text):
            item = match.group(1).strip()
            if item:
                action_items.append(item)

        # Deadline mentions
        deadline_pattern = re.compile(
            r"(?:deadline|due|due date|please complete|please send|please review|"
            r"need you to|could you|can you|would you)[:\s]+(.+?)(?:\.|$)",
            re.IGNORECASE | re.MULTILINE,
        )
        for match in deadline_pattern.finditer(text):
            item = match.group(1).strip()
            if item and len(item) > 5:
                action_items.append(item)

        # Bullet-point action items
        bullet_pattern = re.compile(r"[\-\*•]\s*\[(?:\s|[xX])\]\s*(.+)")
        for match in bullet_pattern.finditer(text):
            item = match.group(1).strip()
            if item:
                action_items.append(item)

        # Numbered action items
        numbered_pattern = re.compile(r"^\d+[\.\)]\s*(.+)$", re.MULTILINE)
        for match in numbered_pattern.finditer(text):
            item = match.group(1).strip()
            if item and len(item) > 5:
                action_items.append(item)

        # Deduplicate while preserving order
        seen = set()
        unique_items: List[str] = []
        for item in action_items:
            normalized = item.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_items.append(item)

        return unique_items[:20]

    def detect_urgency(self, email_data: Dict[str, Any]) -> str:
        """Detect urgency level: critical, high, medium, low, none.

        Analyzes keywords, deadlines, caps usage, and exclamation marks.
        """
        subject = (email_data.get("subject", "") or "").lower()
        body = (email_data.get("body", "") or "").lower()

        urgency_score = 0

        # Critical indicators
        critical_words = {"emergency", "critical", "immediate", "asap", "right now", "production down", "outage"}
        if any(w in subject for w in critical_words):
            return "critical"

        # High urgency
        high_words = {"urgent", "deadline", "time-sensitive", "expires today", "overdue", "final notice"}
        if any(w in subject for w in high_words):
            urgency_score += 3

        # Medium urgency
        medium_words = {"important", "please respond", "needs attention", "action required", "by end of day", "eod"}
        if any(w in subject for w in medium_words):
            urgency_score += 2

        # Body urgency signals
        body_high = {"urgent", "asap", "immediately", "deadline", "critical"}
        body_hits = sum(1 for w in body_high if w in body[:1000])
        urgency_score += min(body_hits, 2)

        # Caps usage (excessive caps = more urgency)
        if subject and sum(1 for c in subject if c.isupper()) / max(len(subject), 1) > 0.5:
            urgency_score += 1

        # Exclamation marks
        if subject.count("!") >= 3:
            urgency_score += 1

        # Date pattern suggesting near-term deadline
        deadline_pattern = re.compile(r"(?:by|before|until|deadline)[:\s]+\w+ \d{1,2}", re.IGNORECASE)
        if deadline_pattern.search(subject):
            urgency_score += 2

        if urgency_score >= 5:
            return "critical"
        elif urgency_score >= 3:
            return "high"
        elif urgency_score >= 1:
            return "medium"
        else:
            return "low"
