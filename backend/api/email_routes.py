"""Email routes."""

from __future__ import annotations

import imaplib
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.core.security import decrypt_value, encrypt_value
from database.connection import get_db
from database.models import EmailAccount, User
from backend.schemas.schemas import (
    EmailAccountCreate,
    EmailAccountResponse,
    EmailResponse,
    EmailSend,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["Email"])


# ── Helpers ──────────────────────────────────────────────────────────────

async def _get_account(account_id: int, user: User, db: AsyncSession) -> EmailAccount:
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Email account not found")
    return account


def _fetch_inbox(account: EmailAccount, password: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent emails via IMAP."""
    emails: List[Dict[str, Any]] = []
    try:
        mail = imaplib.IMAP4_SSL(account.imap_server)
        mail.login(account.email, password)
        mail.select("INBOX")
        _, msg_ids = mail.search(None, "ALL")
        id_list = msg_ids[0].split()
        recent = id_list[-limit:] if len(id_list) >= limit else id_list
        for mid in reversed(recent):
            _, data = mail.fetch(mid, "(RFC822)")
            import email as email_lib
            msg = email_lib.message_from_bytes(data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")
            emails.append({
                "id": mid.decode(),
                "subject": msg.get("Subject", ""),
                "sender": msg.get("From", ""),
                "date": msg.get("Date", ""),
                "body": body[:5000],
            })
        mail.logout()
    except Exception as exc:
        logger.error("IMAP fetch failed: %s", exc)
    return emails


# ── Routes ───────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=list[EmailAccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List configured email accounts."""
    result = await db.execute(
        select(EmailAccount).where(EmailAccount.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/accounts", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
async def add_account(
    body: EmailAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an email account with encrypted password."""
    account = EmailAccount(
        user_id=current_user.id,
        email=body.email,
        imap_server=body.imap_server,
        smtp_server=body.smtp_server,
        encrypted_password=encrypt_value(body.password),
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.get("/inbox", response_model=list[Dict[str, Any]])
async def get_inbox(
    account_id: int = Query(..., description="Email account ID"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch inbox emails for an account."""
    account = await _get_account(account_id, current_user, db)
    password = decrypt_value(account.encrypted_password)
    return _fetch_inbox(account, password, limit)


@router.get("/search", response_model=list[Dict[str, Any]])
async def search_emails(
    q: str = Query(..., min_length=1),
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search emails by subject or body keyword."""
    account = await _get_account(account_id, current_user, db)
    password = decrypt_value(account.encrypted_password)
    all_emails = _fetch_inbox(account, password, limit=200)
    q_lower = q.lower()
    return [e for e in all_emails if q_lower in e.get("subject", "").lower() or q_lower in e.get("body", "").lower()]


@router.get("/{email_id}", response_model=Dict[str, Any])
async def get_email(
    email_id: int,
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific email by ID."""
    account = await _get_account(account_id, current_user, db)
    password = decrypt_value(account.encrypted_password)
    emails = _fetch_inbox(account, password, limit=200)
    for e in emails:
        if e["id"] == str(email_id):
            return e
    raise HTTPException(status_code=404, detail="Email not found")


@router.post("/send", status_code=status.HTTP_200_OK)
async def send_email(
    body: EmailSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send an email via SMTP."""
    if body.account_id:
        account = await _get_account(body.account_id, current_user, db)
    else:
        result = await db.execute(
            select(EmailAccount).where(
                EmailAccount.user_id == current_user.id, EmailAccount.is_active.is_(True)
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise HTTPException(status_code=400, detail="No active email account configured")

    password = decrypt_value(account.encrypted_password)
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = account.email
        msg["To"] = ", ".join(body.to)
        msg["Subject"] = body.subject
        if body.cc:
            msg["Cc"] = ", ".join(body.cc)
        content_type = "html" if body.html else "plain"
        msg.attach(MIMEText(body.body, content_type))

        with smtplib.SMTP(account.smtp_server, 587) as server:
            server.ehlo()
            server.starttls()
            server.login(account.email, password)
            recipients = body.to + (body.cc or []) + (body.bcc or [])
            server.sendmail(account.email, recipients, msg.as_string())
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}")


@router.post("/reply/{email_id}", status_code=status.HTTP_200_OK)
async def reply_to_email(
    email_id: int,
    body: EmailSend,
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reply to a specific email."""
    account = await _get_account(account_id, current_user, db)
    password = decrypt_value(account.encrypted_password)
    emails = _fetch_inbox(account, password, limit=200)
    original = None
    for e in emails:
        if e["id"] == str(email_id):
            original = e
            break
    if original is None:
        raise HTTPException(status_code=404, detail="Original email not found")

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = account.email
        msg["To"] = original["sender"]
        msg["Subject"] = f"Re: {original['subject']}" if not original["subject"].startswith("Re:") else original["subject"]
        msg.attach(MIMEText(body.body, "plain"))

        with smtplib.SMTP(account.smtp_server, 587) as server:
            server.ehlo()
            server.starttls()
            server.login(account.email, password)
            server.sendmail(account.email, [original["sender"]], msg.as_string())
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Email reply failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to send reply: {exc}")
