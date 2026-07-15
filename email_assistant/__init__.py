"""Email system sub-package for managing, categorizing, and drafting emails."""

from email_assistant.manager import EmailManager
from email_assistant.categorizer import EmailCategorizer
from email_assistant.drafter import EmailDrafter

__all__ = ["EmailManager", "EmailCategorizer", "EmailDrafter"]
