"""Email drafting system for composing replies, forwards, and new messages."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmailDrafter:
    """Drafts emails using context analysis, tone detection, and style matching.

    Provides methods to generate draft replies, forwards, and new compositions
    with appropriate tone and formatting.
    """

    # Tone-specific greeting and closing templates
    _TONE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
        "formal": {
            "greetings": [
                "Dear {recipient},",
                "Good {time_of_day}, {recipient},",
            ],
            "closings": [
                "Best regards,",
                "Sincerely,",
                "Kind regards,",
                "Respectfully,",
            ],
            "phrases": [
                "I hope this message finds you well.",
                "Please do not hesitate to reach out if you have any questions.",
                "I would appreciate your prompt attention to this matter.",
                "Thank you for your time and consideration.",
            ],
        },
        "professional": {
            "greetings": [
                "Hi {recipient},",
                "Hello {recipient},",
                "Good {time_of_day}, {recipient},",
            ],
            "closings": [
                "Best,",
                "Thanks,",
                "Regards,",
                "Thank you,",
            ],
            "phrases": [
                "I wanted to follow up regarding",
                "Please let me know if you need anything else.",
                "Looking forward to hearing from you.",
                "Thanks for your help with this.",
            ],
        },
        "casual": {
            "greetings": [
                "Hey {recipient},",
                "Hi there,",
                "What's up {recipient},",
            ],
            "closings": [
                "Cheers,",
                "Thanks!",
                "Talk soon,",
                "Best,",
            ],
            "phrases": [
                "Just wanted to check in about",
                "Let me know what you think!",
                "Happy to help if you need anything.",
                "Sounds good, let me know!",
            ],
        },
        "friendly": {
            "greetings": [
                "Hi {recipient}!",
                "Hey {recipient}!",
                "Hope you're doing well, {recipient}!",
            ],
            "closings": [
                "Take care,",
                "All the best,",
                "Warm wishes,",
                "Cheers,",
            ],
            "phrases": [
                "Hope you're having a great day!",
                "It's always great hearing from you.",
                "I'm excited about this!",
                "Thanks so much for reaching out.",
            ],
        },
    }

    def draft_reply(
        self,
        original_email: Dict[str, Any],
        context: str = "",
        tone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Draft a reply to an existing email.

        Args:
            original_email: The original email data (from, subject, body, etc.).
            context: Additional context or points to include in the reply.
            tone: Desired tone. Auto-detected if not provided.

        Returns:
            Dict with ``to``, ``subject``, ``body``, and ``tone`` keys.
        """
        if tone is None:
            tone = self.detect_tone(original_email)

        sender = original_email.get("from", "")
        recipient_name = self._extract_name(sender)
        subject = original_email.get("subject", "")
        body = original_email.get("body", "")

        reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

        greeting = self._get_greeting(tone, recipient_name)
        closing = self._get_closing(tone)
        filler = self._get_phrase(tone)

        reply_body = f"{greeting}\n\n"

        if context:
            reply_body += f"{context}\n\n"
        else:
            # Generate context-aware default reply
            if body:
                reply_body += f"{filler}\n\n"
                reply_body += self._generate_contextual_response(body, tone)
                reply_body += "\n\n"
            else:
                reply_body += f"{filler}\n\n"

        reply_body += f"{closing}"

        return {
            "to": sender,
            "subject": reply_subject,
            "body": reply_body,
            "tone": tone,
            "reply_to_id": original_email.get("id", ""),
            "in_reply_to": original_email.get("message_id", ""),
        }

    def draft_forward(
        self,
        original_email: Dict[str, Any],
        to: str = "",
        context: str = "",
        tone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Draft a forwarded email.

        Args:
            original_email: The original email data.
            to: Forward recipient address.
            context: Introductory text before the forwarded content.
            tone: Desired tone for the introductory text.

        Returns:
            Dict with ``to``, ``subject``, ``body``, and ``tone`` keys.
        """
        if tone is None:
            tone = self.detect_tone(original_email)

        subject = original_email.get("subject", "")
        forward_subject = subject if subject.lower().startswith("fwd:") else f"Fwd: {subject}"

        greeting = "Hi," if to else "Hi,"
        closing = self._get_closing(tone)

        body = ""
        if context:
            body += f"{greeting}\n\n{context}\n\n"
        else:
            body += f"{greeting}\n\nForwarding this for your reference.\n\n"

        body += f"{closing}\n\n"
        body += f"---------- Forwarded message ----------\n"
        body += f"From: {original_email.get('from', '')}\n"
        body += f"Date: {original_email.get('date', '')}\n"
        body += f"Subject: {subject}\n"
        body += f"To: {original_email.get('to', '')}\n\n"
        body += original_email.get("body", "")

        return {
            "to": to,
            "subject": forward_subject,
            "body": body,
            "tone": tone,
            "forward_from_id": original_email.get("id", ""),
        }

    def compose_new(
        self,
        to: str,
        context: str,
        tone: str = "professional",
        subject: str = "",
        signature: str = "",
    ) -> Dict[str, Any]:
        """Compose a new email from scratch.

        Args:
            to: Recipient email address.
            context: Description or key points for the email.
            tone: Desired tone.
            subject: Email subject (auto-generated if empty).
            signature: Custom signature to append.

        Returns:
            Dict with ``to``, ``subject``, ``body``, ``tone`` keys.
        """
        recipient_name = self._extract_name(to)
        greeting = self._get_greeting(tone, recipient_name)
        closing = self._get_closing(tone)

        if not subject:
            subject = self._generate_subject(context)

        body = f"{greeting}\n\n"
        body += f"{context}\n\n"

        if signature:
            body += f"{closing}\n\n{signature}"
        else:
            body += closing

        return {
            "to": to,
            "subject": subject,
            "body": body,
            "tone": tone,
        }

    def improve_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Improve an existing draft by fixing grammar, improving clarity,
        and ensuring consistent tone.
        """
        body = draft.get("body", "")
        tone = draft.get("tone", "professional")

        improved = body

        # Fix common grammar issues
        grammar_fixes = [
            (r"\bi\b", "I"),
            (r"\bim\b", "I'm"),
            (r"\bive\b", "I've"),
            (r"\bid\b", "I'd"),
            (r"\bwont\b", "won't"),
            (r"\bdont\b", "don't"),
            (r"\bcant\b", "can't"),
            (r"\bwould of\b", "would have"),
            (r"\bcould of\b", "could have"),
            (r"\bshould of\b", "should have"),
            (r"\s{2,}", " "),
        ]
        for pattern, replacement in grammar_fixes:
            improved = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)

        # Ensure sentence ends with proper punctuation
        sentences = improved.split("\n\n")
        polished: List[str] = []
        for sentence in sentences:
            stripped = sentence.strip()
            if stripped and not stripped.endswith((".", "!", "?", ":", '"')):
                stripped += "."
            polished.append(stripped)

        improved = "\n\n".join(polished)

        draft["body"] = improved
        draft["improved"] = True
        return draft

    def detect_tone(self, email_data: Dict[str, Any]) -> str:
        """Detect the tone of an email: formal, professional, casual, or friendly.

        Analyzes greeting style, vocabulary, punctuation, and overall formality.
        """
        body = (email_data.get("body", "") or "").lower()
        subject = (email_data.get("subject", "") or "").lower()

        score: Dict[str, float] = {
            "formal": 0.0,
            "professional": 0.0,
            "casual": 0.0,
            "friendly": 0.0,
        }

        # Formal indicators
        formal_patterns = [
            r"dear\s+\w+", r"respectfully", r"sincerely", r"pursuant to",
            r"hereby", r"thereof", r"wherein", r"regarding the matter",
            r"i hope this finds you well",
        ]
        for pattern in formal_patterns:
            if re.search(pattern, body):
                score["formal"] += 1

        # Professional indicators
        professional_patterns = [
            r"best regards", r"thank you", r"please let me know",
            r"looking forward", r"at your earliest convenience",
            r"please find attached", r"as discussed",
        ]
        for pattern in professional_patterns:
            if re.search(pattern, body):
                score["professional"] += 1

        # Casual indicators
        casual_patterns = [
            r"\bhey\b", r"\bwhat'?s up\b", r"\bgonna\b", r"\bwanna\b",
            r"\bthanks!\b", r"\bcheers\b", r"\blol\b", r"\bhaha\b",
            r"!{2,}", r"\bno worries\b",
        ]
        for pattern in casual_patterns:
            if re.search(pattern, body):
                score["casual"] += 1

        # Friendly indicators
        friendly_patterns = [
            r"hope you'?re doing well", r"hope you'?re having",
            r"great to hear", r"awesome", r"wonderful",
            r"looking forward to", r"take care",
        ]
        for pattern in friendly_patterns:
            if re.search(pattern, body):
                score["friendly"] += 1

        # Exclamation marks suggest casual/friendly
        exclamation_count = body.count("!")
        if exclamation_count > 3:
            score["casual"] += 1
            score["friendly"] += 1
        elif exclamation_count > 0:
            score["friendly"] += 0.5

        # All caps suggests formality (shouting in casual is different)
        caps_ratio = sum(1 for c in body if c.isupper()) / max(len(body), 1)
        if caps_ratio > 0.3:
            score["formal"] += 0.5

        best = max(score, key=score.get)  # type: ignore[arg-type]
        return best if score[best] > 0 else "professional"

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _extract_name(sender: str) -> str:
        """Extract a display name from an email address or 'Name <email>' format."""
        match = re.match(r'"?([^"<]+)"?\s*<', sender)
        if match:
            return match.group(1).strip().split()[0]
        return sender.split("@")[0].title()

    @staticmethod
    def _get_time_of_day() -> str:
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 12:
            return "morning"
        elif hour < 17:
            return "afternoon"
        return "evening"

    def _get_greeting(self, tone: str, recipient_name: str) -> str:
        templates = self._TONE_TEMPLATES.get(tone, self._TONE_TEMPLATES["professional"])
        greeting = templates["greetings"][0]
        return greeting.format(
            recipient=recipient_name,
            time_of_day=self._get_time_of_day(),
        )

    def _get_closing(self, tone: str) -> str:
        templates = self._TONE_TEMPLATES.get(tone, self._TONE_TEMPLATES["professional"])
        return templates["closings"][0]

    def _get_phrase(self, tone: str) -> str:
        import random
        templates = self._TONE_TEMPLATES.get(tone, self._TONE_TEMPLATES["professional"])
        return random.choice(templates["phrases"])

    def _generate_subject(self, context: str) -> str:
        """Generate an email subject from context description."""
        words = context.split()[:8]
        subject = " ".join(words)
        if not subject.endswith("."):
            subject = subject.rstrip(".")
        return subject.title() if subject else "New Message"

    def _generate_contextual_response(self, original_body: str, tone: str) -> str:
        """Generate a basic contextual response based on the original email content."""
        body_lower = original_body.lower()

        if any(w in body_lower for w in ["question", "can you", "could you", "would you"]):
            return "Thank you for your question. I'll look into this and get back to you shortly."
        elif any(w in body_lower for w in ["meeting", "schedule", "calendar", "availability"]):
            return "Thanks for reaching out about scheduling. Let me check my availability and get back to you."
        elif any(w in body_lower for w in ["update", "status", "progress"]):
            return "Thanks for the update. I'll review this and follow up if needed."
        elif any(w in body_lower for w in ["invoice", "payment", "bill"]):
            return "I've received your message regarding the invoice. I'll review it and respond shortly."
        else:
            return "Thank you for your message. I'll review this and get back to you soon."
