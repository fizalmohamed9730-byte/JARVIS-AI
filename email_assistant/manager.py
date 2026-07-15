"""Email manager for IMAP/SMTP operations with connection pooling."""

import email as email_lib
import email.mime.text
import email.mime.multipart
import email.mime.base
import email.utils
import imaplib
import logging
import smtplib
import ssl
from datetime import datetime
from email.header import decode_header
from email.message import Message
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class EmailAccount:
    """Configuration for a single email account."""

    def __init__(
        self,
        email_address: str,
        password: str,
        imap_host: str = "",
        imap_port: int = 993,
        smtp_host: str = "",
        smtp_port: int = 587,
        use_ssl: bool = True,
        display_name: str = "",
    ) -> None:
        self.email_address = email_address
        self.password = password
        self.imap_host = imap_host or self._guess_imap_host(email_address)
        self.imap_port = imap_port
        self.smtp_host = smtp_host or self._guess_smtp_host(email_address)
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl
        self.display_name = display_name or email_address.split("@")[0]

    @staticmethod
    def _guess_imap_host(email_addr: str) -> str:
        domain = email_addr.split("@")[-1].lower()
        providers = {
            "gmail.com": "imap.gmail.com",
            "outlook.com": "outlook.office365.com",
            "hotmail.com": "outlook.office365.com",
            "live.com": "outlook.office365.com",
            "yahoo.com": "imap.mail.yahoo.com",
            "icloud.com": "imap.mail.me.com",
            "me.com": "imap.mail.me.com",
            "aol.com": "imap.aol.com",
        }
        return providers.get(domain, f"imap.{domain}")

    @staticmethod
    def _guess_smtp_host(email_addr: str) -> str:
        domain = email_addr.split("@")[-1].lower()
        providers = {
            "gmail.com": "smtp.gmail.com",
            "outlook.com": "smtp.office365.com",
            "hotmail.com": "smtp.office365.com",
            "live.com": "smtp.office365.com",
            "yahoo.com": "smtp.mail.yahoo.com",
            "icloud.com": "smtp.mail.me.com",
            "me.com": "smtp.mail.me.com",
            "aol.com": "smtp.aol.com",
        }
        return providers.get(domain, f"smtp.{domain}")


class EmailManager:
    """Manages email connections, retrieval, sending, and folder operations.

    Uses IMAP for reading and SMTP for sending. Maintains separate
    connections per account with automatic reconnection.
    """

    def __init__(self) -> None:
        self._accounts: Dict[str, EmailAccount] = {}
        self._imap_connections: Dict[str, imaplib.IMAP4_SSL] = {}
        self._smtp_connections: Dict[str, smtplib.SMTP] = {}

    # --------------------------------------------------------------------- #
    # Connection management
    # --------------------------------------------------------------------- #

    def connect_imap(self, account: EmailAccount) -> imaplib.IMAP4_SSL:
        """Establish or reuse an IMAP connection for the given account."""
        key = account.email_address
        if key in self._imap_connections:
            try:
                self._imap_connections[key].noop()
                return self._imap_connections[key]
            except Exception:
                self._imap_connections.pop(key, None)

        try:
            if account.use_ssl:
                conn = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
            else:
                conn = imaplib.IMAP4(account.imap_host, account.imap_port)
            conn.login(account.email_address, account.password)
            self._imap_connections[key] = conn
            self._accounts[key] = account
            logger.info("IMAP connected: %s", key)
            return conn
        except Exception as exc:
            logger.exception("IMAP connection failed for %s", key)
            raise ConnectionError(f"IMAP connection failed: {exc}") from exc

    def connect_smtp(self, account: EmailAccount) -> smtplib.SMTP:
        """Establish or reuse an SMTP connection for the given account."""
        key = account.email_address
        if key in self._smtp_connections:
            try:
                self._smtp_connections[key].ehlo()
                return self._smtp_connections[key]
            except Exception:
                self._smtp_connections.pop(key, None)

        try:
            context = ssl.create_default_context()
            if account.smtp_port == 587:
                server = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=30)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port, context=context, timeout=30)
            server.login(account.email_address, account.password)
            self._smtp_connections[key] = server
            logger.info("SMTP connected: %s", key)
            return server
        except Exception as exc:
            logger.exception("SMTP connection failed for %s", key)
            raise ConnectionError(f"SMTP connection failed: {exc}") from exc

    def disconnect(self, email_address: str) -> None:
        """Close IMAP and SMTP connections for an account."""
        for store, name in [(self._imap_connections, "IMAP"), (self._smtp_connections, "SMTP")]:
            conn = store.pop(email_address, None)
            if conn:
                try:
                    conn.logout()
                except Exception:
                    pass
                logger.info("%s disconnected: %s", name, email_address)

    def disconnect_all(self) -> None:
        """Close all connections."""
        for addr in list(self._imap_connections.keys()):
            self.disconnect(addr)

    # --------------------------------------------------------------------- #
    # Email retrieval
    # --------------------------------------------------------------------- #

    def get_emails(
        self,
        account_email: str,
        folder: str = "INBOX",
        limit: int = 20,
        unread_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch a list of emails from the specified folder.

        Returns summary dicts with ``id``, ``from``, ``subject``, ``date``,
        and ``unread`` keys.
        """
        conn = self._get_imap(account_email)
        try:
            conn.select(folder, readonly=True)

            criteria = "UNSEEN" if unread_only else "ALL"
            status, msg_ids = conn.search(None, criteria)
            if status != "OK":
                return []

            all_ids = msg_ids[0].split()
            # Most recent first
            all_ids = all_ids[::-1][:limit]

            emails: List[Dict[str, Any]] = []
            for msg_id in all_ids:
                status, msg_data = conn.fetch(msg_id, "(RFC822.HEADER)")
                if status != "OK":
                    continue
                raw_header = msg_data[0][1]
                if isinstance(raw_header, bytes):
                    msg = email_lib.message_from_bytes(raw_header)
                else:
                    msg = email_lib.message_from_string(raw_header)

                emails.append(self._parse_header(msg, msg_id.decode()))

            return emails
        except Exception as exc:
            logger.exception("Failed to fetch emails")
            self._reconnect(account_email)
            return []

    def get_email(self, account_email: str, email_id: str) -> Dict[str, Any]:
        """Fetch a single email with full body content."""
        conn = self._get_imap(account_email)
        try:
            conn.select("INBOX", readonly=True)
            status, msg_data = conn.fetch(email_id.encode() if isinstance(email_id, str) else email_id, "(RFC822)")
            if status != "OK":
                return {"error": "Email not found"}

            raw_email = msg_data[0][1]
            if isinstance(raw_email, bytes):
                msg = email_lib.message_from_bytes(raw_email)
            else:
                msg = email_lib.message_from_string(raw_email)

            return self._parse_full_email(msg, email_id)
        except Exception as exc:
            logger.exception("Failed to fetch email %s", email_id)
            self._reconnect(account_email)
            return {"error": str(exc)}

    def send_email(
        self,
        account_email: str,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html: bool = False,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send an email with optional attachments.

        Args:
            account_email: Sender account address.
            to: Recipient(s).
            subject: Email subject line.
            body: Message body text.
            html: If *True*, ``body`` is treated as HTML.
            attachments: List of dicts with ``filename`` and ``data`` (bytes) keys.
            cc: Optional CC recipients.
            bcc: Optional BCC recipients.
        """
        account = self._accounts.get(account_email)
        if not account:
            return {"success": False, "error": f"Account not connected: {account_email}"}

        if isinstance(to, str):
            to_list = [to]
        else:
            to_list = list(to)

        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg["From"] = f"{account.display_name} <{account.email_address}>"
        msg["To"] = ", ".join(to_list)
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain=account_email.split("@")[-1])

        if cc:
            msg["Cc"] = ", ".join(cc)

        body_part = email.mime.text.MIMEText(body, "html" if html else "plain")
        msg.attach(body_part)

        if attachments:
            for att in attachments:
                part = email.mime.base.MIMEBase("application", "octet-stream")
                part.set_payload(att["data"])
                import base64
                email_lib.encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{att["filename"]}"',
                )
                msg.attach(part)

        all_recipients = to_list + (cc or []) + (bcc or [])

        try:
            server = self.connect_smtp(account)
            server.sendmail(account.email_address, all_recipients, msg.as_string())
            logger.info("Email sent from %s to %s", account_email, all_recipients)
            return {"success": True, "message_id": msg["Message-ID"]}
        except Exception as exc:
            logger.exception("Failed to send email")
            self._reconnect_smtp(account_email)
            return {"success": False, "error": str(exc)}

    def reply_to_email(
        self,
        account_email: str,
        email_id: str,
        body: str,
        reply_all: bool = False,
    ) -> Dict[str, Any]:
        """Reply to an existing email."""
        original = self.get_email(account_email, email_id)
        if "error" in original:
            return {"success": False, "error": original["error"]}

        to_addr = original.get("from", "")
        if reply_all:
            all_recipients = original.get("to", "").split(", ") + original.get("cc", "").split(", ")
            all_recipients = [r for r in all_recipients if r and r != account_email]
        else:
            all_recipients = [to_addr]

        subject = original.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        return self.send_email(
            account_email=account_email,
            to=all_recipients,
            subject=subject,
            body=body,
        )

    def forward_email(
        self,
        account_email: str,
        email_id: str,
        to: str,
        message: str = "",
    ) -> Dict[str, Any]:
        """Forward an email to a new recipient."""
        original = self.get_email(account_email, email_id)
        if "error" in original:
            return {"success": False, "error": original["error"]}

        subject = original.get("subject", "")
        if not subject.lower().startswith("fwd:"):
            subject = f"Fwd: {subject}"

        forward_body = f"{message}\n\n---------- Forwarded message ----------\n"
        forward_body += f"From: {original.get('from', '')}\n"
        forward_body += f"Date: {original.get('date', '')}\n"
        forward_body += f"Subject: {subject}\n"
        forward_body += f"To: {original.get('to', '')}\n\n"
        forward_body += original.get("body", "")

        return self.send_email(
            account_email=account_email,
            to=to,
            subject=subject,
            body=forward_body,
        )

    def mark_read(self, account_email: str, email_id: str) -> bool:
        """Mark an email as read."""
        return self._set_flag(account_email, email_id, "\\Seen")

    def mark_unread(self, account_email: str, email_id: str) -> bool:
        """Mark an email as unread."""
        conn = self._get_imap(account_email)
        try:
            conn.select("INBOX")
            conn.store(email_id.encode(), "-FLAGS", "\\Seen")
            return True
        except Exception:
            return False

    def delete_email(self, account_email: str, email_id: str) -> Dict[str, Any]:
        """Move an email to trash, or flag for deletion if no trash folder."""
        conn = self._get_imap(account_email)
        try:
            conn.select("INBOX")
            # Try moving to Trash/Junk first
            trash_folders = ["[Gmail]/Trash", "Trash", "Deleted Messages", "Junk"]
            moved = False
            for folder in trash_folders:
                try:
                    conn.copy(email_id.encode(), folder)
                    conn.store(email_id.encode(), "+FLAGS", "\\Deleted")
                    conn.expunge()
                    moved = True
                    break
                except Exception:
                    continue

            if not moved:
                conn.store(email_id.encode(), "+FLAGS", "\\Deleted")
                conn.expunge()

            return {"success": True, "message": "Email deleted/moved to trash"}
        except Exception as exc:
            self._reconnect(account_email)
            return {"success": False, "error": str(exc)}

    def move_email(self, account_email: str, email_id: str, folder: str) -> Dict[str, Any]:
        """Move an email to a different folder."""
        conn = self._get_imap(account_email)
        try:
            conn.select("INBOX")
            conn.copy(email_id.encode(), folder)
            conn.store(email_id.encode(), "+FLAGS", "\\Deleted")
            conn.expunge()
            return {"success": True, "message": f"Email moved to {folder}"}
        except Exception as exc:
            self._reconnect(account_email)
            return {"success": False, "error": str(exc)}

    def search_emails(
        self, account_email: str, query: str, folder: str = "INBOX"
    ) -> List[Dict[str, Any]]:
        """Search for emails matching *query* using IMAP SEARCH."""
        conn = self._get_imap(account_email)
        try:
            conn.select(folder, readonly=True)
            status, msg_ids = conn.search(None, f'(OR SUBJECT "{query}" FROM "{query}")')
            if status != "OK":
                return []

            all_ids = msg_ids[0].split()
            emails: List[Dict[str, Any]] = []
            for msg_id in all_ids[:50]:
                status, msg_data = conn.fetch(msg_id, "(RFC822.HEADER)")
                if status != "OK":
                    continue
                raw_header = msg_data[0][1]
                if isinstance(raw_header, bytes):
                    msg = email_lib.message_from_bytes(raw_header)
                else:
                    msg = email_lib.message_from_string(raw_header)
                emails.append(self._parse_header(msg, msg_id.decode()))
            return emails
        except Exception as exc:
            logger.exception("Search failed")
            self._reconnect(account_email)
            return []

    def get_folders(self, account_email: str) -> List[str]:
        """List available mail folders."""
        conn = self._get_imap(account_email)
        try:
            status, folders = conn.list()
            if status != "OK":
                return []
            result: List[str] = []
            for folder in folders:
                if isinstance(folder, bytes):
                    folder = folder.decode()
                parts = folder.split(' " ')
                if len(parts) >= 2:
                    name = parts[-1].strip('"')
                    result.append(name)
            return result
        except Exception:
            return []

    def get_unread_count(self, account_email: str, folder: str = "INBOX") -> int:
        """Return count of unread emails in the given folder."""
        conn = self._get_imap(account_email)
        try:
            conn.select(folder, readonly=True)
            status, msg_ids = conn.search(None, "UNSEEN")
            if status != "OK":
                return 0
            return len(msg_ids[0].split()) if msg_ids[0] else 0
        except Exception:
            return 0

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _get_imap(self, account_email: str) -> imaplib.IMAP4_SSL:
        """Get an IMAP connection, raising if the account is not configured."""
        if account_email not in self._imap_connections:
            if account_email in self._accounts:
                return self.connect_imap(self._accounts[account_email])
            raise ConnectionError(f"No IMAP connection for {account_email}")
        return self._imap_connections[account_email]

    def _reconnect(self, account_email: str) -> None:
        """Attempt to reconnect IMAP after a connection error."""
        self._imap_connections.pop(account_email, None)
        if account_email in self._accounts:
            try:
                self.connect_imap(self._accounts[account_email])
            except Exception:
                pass

    def _reconnect_smtp(self, account_email: str) -> None:
        """Attempt to reconnect SMTP after a connection error."""
        self._smtp_connections.pop(account_email, None)
        if account_email in self._accounts:
            try:
                self.connect_smtp(self._accounts[account_email])
            except Exception:
                pass

    def _set_flag(self, account_email: str, email_id: str, flag: str) -> bool:
        conn = self._get_imap(account_email)
        try:
            conn.select("INBOX")
            conn.store(email_id.encode(), "+FLAGS", flag)
            return True
        except Exception:
            return False

    @staticmethod
    def _decode_header_value(raw: str) -> str:
        """Decode an RFC 2047 encoded header value."""
        if raw is None:
            return ""
        decoded_parts = decode_header(raw)
        parts: List[str] = []
        for content, charset in decoded_parts:
            if isinstance(content, bytes):
                parts.append(content.decode(charset or "utf-8", errors="replace"))
            else:
                parts.append(content)
        return "".join(parts)

    @staticmethod
    def _get_body(msg: Message) -> str:
        """Extract the plain text body from a MIME message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
            # Fallback to HTML if no plain text
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/html" and "attachment" not in disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    @staticmethod
    def _get_html_body(msg: Message) -> str:
        """Extract the HTML body from a MIME message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/html" and "attachment" not in disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
        elif msg.get_content_type() == "text/html":
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    def _parse_header(self, msg: Message, msg_id: str) -> Dict[str, Any]:
        """Parse a message header into a summary dict."""
        return {
            "id": msg_id,
            "from": self._decode_header_value(msg.get("From", "")),
            "to": self._decode_header_value(msg.get("To", "")),
            "subject": self._decode_header_value(msg.get("Subject", "")),
            "date": msg.get("Date", ""),
            "unread": "\\Seen" not in str(msg.get_flags() if hasattr(msg, "get_flags") else ""),
        }

    def _parse_full_email(self, msg: Message, msg_id: str) -> Dict[str, Any]:
        """Parse a full email message including body and attachments."""
        attachments: List[Dict[str, Any]] = []
        if msg.is_multipart():
            for part in msg.walk():
                disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header_value(filename)
                    attachments.append({
                        "filename": filename or "unnamed",
                        "content_type": part.get_content_type(),
                        "size": len(part.get_payload(decode=True) or b""),
                    })

        return {
            "id": msg_id,
            "from": self._decode_header_value(msg.get("From", "")),
            "to": self._decode_header_value(msg.get("To", "")),
            "cc": self._decode_header_value(msg.get("Cc", "")),
            "subject": self._decode_header_value(msg.get("Subject", "")),
            "date": msg.get("Date", ""),
            "body": self._get_body(msg),
            "html_body": self._get_html_body(msg),
            "attachments": attachments,
            "message_id": msg.get("Message-ID", ""),
            "in_reply_to": msg.get("In-Reply-To", ""),
        }

