"""Email tools for JARVIS AI agent system."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_EMAIL_CACHE_DIR = Path.home() / ".jarvis" / "email_cache"
_EMAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_cache(filename: str = "emails.json") -> list[dict[str, Any]]:
    """Load email data from cache."""
    cache_path = _EMAIL_CACHE_DIR / filename
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_cache(data: list[dict[str, Any]], filename: str = "emails.json") -> None:
    """Save email data to cache."""
    cache_path = _EMAIL_CACHE_DIR / filename
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except OSError as e:
        logger.error("Failed to save email cache: %s", e)


def _get_imap_connection():
    """Get IMAP connection from environment configuration."""
    import imaplib

    host = os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com")
    port = int(os.environ.get("EMAIL_IMAP_PORT", "993"))
    user = os.environ.get("EMAIL_ADDRESS", "")
    password = os.environ.get("EMAIL_PASSWORD", "")

    if not user or not password:
        return None, "Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables."

    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        return mail, None
    except Exception as e:
        return None, f"Failed to connect to email server: {e}"


def _get_smtp_connection():
    """Get SMTP connection from environment configuration."""
    import smtplib

    host = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_ADDRESS", "")
    password = os.environ.get("EMAIL_PASSWORD", "")

    if not user or not password:
        return None, "Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables."

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(user, password)
        return server, None
    except Exception as e:
        return None, f"Failed to connect to SMTP server: {e}"


@tool
def read_emails(folder: str = "INBOX", limit: int = 10, unread_only: bool = False) -> str:
    """Read emails from the specified folder.

    Args:
        folder: Email folder to read from (e.g., 'INBOX', 'Sent', 'Drafts'). Defaults to INBOX.
        limit: Maximum number of emails to retrieve (1-50). Defaults to 10.
        unread_only: If True, only fetch unread emails. Defaults to False.

    Returns:
        A formatted string of email summaries with sender, subject, date, and preview.
    """
    limit = max(1, min(50, limit))

    mail, error = _get_imap_connection()
    if error:
        return error

    try:
        mail.select(folder)

        status, messages = mail.search(None, "UNSEEN" if unread_only else "ALL")
        if status != "OK":
            return f"Error: Could not search folder '{folder}'."

        msg_ids = messages[0].split()
        if not msg_ids:
            return f"No {'unread ' if unread_only else ''}emails in {folder}."

        recent_ids = msg_ids[-limit:]
        recent_ids.reverse()

        emails: list[str] = []
        for msg_id in recent_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822.HEADER)")
            if status != "OK":
                continue

            import email
            from email.header import decode_header

            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")

            msg = email.message_from_string(raw)

            subject_parts = decode_header(msg.get("Subject", "(no subject)"))
            subject = ""
            for part, enc in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject += part

            from_addr = msg.get("From", "Unknown")
            date_str = msg.get("Date", "Unknown date")

            body_preview = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_preview = payload.decode("utf-8", errors="replace")[:200]
                        break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_preview = payload.decode("utf-8", errors="replace")[:200]

            emails.append(
                f"- From: {from_addr}\n"
                f"  Subject: {subject}\n"
                f"  Date: {date_str}\n"
                f"  Preview: {body_preview.strip()}\n"
            )

        return f"Found {len(emails)} emails:\n\n" + "\n".join(emails)

    except Exception as e:
        return f"Error reading emails: {e}"
    finally:
        try:
            mail.logout()
        except Exception:
            pass


@tool
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
) -> str:
    """Send an email.

    Args:
        to: Recipient email address(es), comma-separated.
        subject: Email subject line.
        body: Email body text.
        cc: CC recipient(s), comma-separated. Defaults to empty.
        bcc: BCC recipient(s), comma-separated. Defaults to empty.

    Returns:
        A success or error message.
    """
    if not to or not to.strip():
        return "Error: Recipient email address is required."
    if not subject or not subject.strip():
        return "Error: Email subject is required."

    server, error = _get_smtp_connection()
    if error:
        return error

    user = os.environ.get("EMAIL_ADDRESS", "")

    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = to
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc

        msg.attach(MIMEText(body, "plain"))

        recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        if cc:
            recipients.extend([addr.strip() for addr in cc.split(",") if addr.strip()])
        if bcc:
            recipients.extend([addr.strip() for addr in bcc.split(",") if addr.strip()])

        server.sendmail(user, recipients, msg.as_string())

        sent_data = _load_cache("sent.json")
        sent_data.append({
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "date": datetime.now().isoformat(),
        })
        _save_cache(sent_data, "sent.json")

        return f"Email sent to {to}" + (f" (CC: {cc})" if cc else "")

    except Exception as e:
        return f"Error sending email: {e}"
    finally:
        try:
            server.quit()
        except Exception:
            pass


@tool
def reply_to_email(email_id: str, body: str) -> str:
    """Reply to an email by its ID.

    Args:
        email_id: The email identifier (sender + subject combination for lookup).
        body: The reply body text.

    Returns:
        A success or error message.
    """
    if not email_id or not email_id.strip():
        return "Error: Email ID is required."
    if not body or not body.strip():
        return "Error: Reply body cannot be empty."

    sent_data = _load_cache("sent.json")
    found = None
    for entry in sent_data:
        if email_id.lower() in str(entry).lower():
            found = entry
            break

    if found:
        to_addr = found.get("to", "")
        original_subject = found.get("subject", "")
        subject = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
        return send_email(to=to_addr, subject=subject, body=body)

    return (
        f"Could not find email with ID '{email_id}' in cached emails.\n"
        "Please use the full email address to reply."
    )


@tool
def search_emails(query: str, folder: str = "INBOX", limit: int = 20) -> str:
    """Search emails by keyword in subject or body.

    Args:
        query: Search keyword or phrase.
        folder: Folder to search in. Defaults to INBOX.
        limit: Maximum results (1-50). Defaults to 20.

    Returns:
        A formatted list of matching emails.
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    limit = max(1, min(50, limit))

    mail, error = _get_imap_connection()
    if error:
        return error

    try:
        mail.select(folder)

        status, messages = mail.search(None, f'(OR SUBJECT "{query}" BODY "{query}")')
        if status != "OK":
            return f"Error searching emails in {folder}."

        msg_ids = messages[0].split()
        if not msg_ids:
            return f"No emails matching '{query}' found in {folder}."

        recent_ids = msg_ids[-limit:]
        recent_ids.reverse()

        results: list[str] = []
        for msg_id in recent_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822.HEADER)")
            if status != "OK":
                continue

            import email
            from email.header import decode_header

            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")

            msg = email.message_from_string(raw)

            subject_parts = decode_header(msg.get("Subject", "(no subject)"))
            subject = ""
            for part, enc in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject += part

            results.append(
                f"- From: {msg.get('From', 'Unknown')}\n"
                f"  Subject: {subject}\n"
                f"  Date: {msg.get('Date', 'Unknown')}\n"
            )

        return f"Found {len(results)} emails matching '{query}':\n\n" + "\n".join(results)

    except Exception as e:
        return f"Error searching emails: {e}"
    finally:
        try:
            mail.logout()
        except Exception:
            pass


@tool
def categorize_emails() -> str:
    """Categorize recent emails into groups (work, personal, promotions, notifications).

    Returns:
        A categorized summary of recent emails.
    """
    mail, error = _get_imap_connection()
    if error:
        return error

    try:
        mail.select("INBOX")
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            return "Error accessing inbox."

        msg_ids = messages[0].split()
        if not msg_ids:
            return "No emails to categorize."

        recent_ids = msg_ids[-50:]

        categories: dict[str, list[str]] = {
            "Work": [],
            "Personal": [],
            "Promotions": [],
            "Notifications": [],
            "Other": [],
        }

        work_keywords = {"meeting", "project", "deadline", "report", "team", "office", "standup", "sprint"}
        promo_keywords = {"sale", "discount", "offer", "deal", "subscribe", "unsubscribe", "newsletter", "promo"}
        notif_keywords = {"notification", "alert", "verify", "confirm", "password", "security", "update"}

        for msg_id in recent_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822.HEADER)")
            if status != "OK":
                continue

            import email
            from email.header import decode_header

            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")

            msg = email.message_from_string(raw)

            subject_parts = decode_header(msg.get("Subject", ""))
            subject = ""
            for part, enc in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject += part

            subject_lower = subject.lower()
            from_addr = msg.get("From", "Unknown")

            categorized = False
            for kw in work_keywords:
                if kw in subject_lower:
                    categories["Work"].append(f"  - {subject} (from {from_addr})")
                    categorized = True
                    break
            if not categorized:
                for kw in promo_keywords:
                    if kw in subject_lower:
                        categories["Promotions"].append(f"  - {subject} (from {from_addr})")
                        categorized = True
                        break
            if not categorized:
                for kw in notif_keywords:
                    if kw in subject_lower:
                        categories["Notifications"].append(f"  - {subject} (from {from_addr})")
                        categorized = True
                        break
            if not categorized:
                categories["Other"].append(f"  - {subject} (from {from_addr})")

        parts: list[str] = ["Email Categories:\n"]
        for cat, emails_list in categories.items():
            if emails_list:
                parts.append(f"{cat} ({len(emails_list)}):")
                parts.extend(emails_list[:5])
                if len(emails_list) > 5:
                    parts.append(f"  ... and {len(emails_list) - 5} more")
                parts.append("")

        return "\n".join(parts)

    except Exception as e:
        return f"Error categorizing emails: {e}"
    finally:
        try:
            mail.logout()
        except Exception:
            pass


email_tools = [read_emails, send_email, reply_to_email, search_emails, categorize_emails]
