"""
Email service — production-ready email abstraction.

Provides:
  - ``DevelopmentEmailProvider``: logs to console, never sends real email.
  - ``SMTPEmailProvider``: async SMTP via ``aiosmtplib``, compatible with
    SendGrid, AWS SES, Mailgun, and any standard SMTP relay.

The active backend is selected by the ``EMAIL_BACKEND`` environment variable:
  ``development``  (default) → DevelopmentEmailProvider
  ``smtp``                   → SMTPEmailProvider

Never put credentials in source code.  All configuration is read from the
application ``Settings`` object which loads from environment / .env.
"""

from __future__ import annotations

import logging
import textwrap
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ── HTML email templates ──────────────────────────────────────────────────────


def _base_html(title: str, body_html: str) -> str:
    """Wrap body content in a consistent, minimal HTML email shell."""
    return textwrap.dedent(f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
          <title>{title}</title>
          <style>
            body {{font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                   background:#f4f7fa; margin:0; padding:0;}}
            .wrapper {{max-width:600px; margin:40px auto; background:#fff;
                       border-radius:8px; overflow:hidden;
                       box-shadow:0 2px 8px rgba(0,0,0,.08);}}
            .header {{background:#1a6b8a; color:#fff; padding:28px 36px;}}
            .header h1 {{margin:0; font-size:22px; font-weight:600;}}
            .content {{padding:32px 36px; color:#334155; line-height:1.6;}}
            .btn {{display:inline-block; margin:20px 0; padding:12px 28px;
                   background:#1a6b8a; color:#fff; text-decoration:none;
                   border-radius:6px; font-weight:600; font-size:15px;}}
            .footer {{padding:20px 36px; background:#f8fafc; color:#94a3b8;
                      font-size:12px; border-top:1px solid #e2e8f0;}}
            .divider {{border:none; border-top:1px solid #e2e8f0; margin:20px 0;}}
            code {{background:#f1f5f9; padding:2px 6px; border-radius:4px;
                   font-family:monospace; font-size:13px;}}
          </style>
        </head>
        <body>
          <div class="wrapper">
            <div class="header">
              <h1>&#x1F3E5; HealthPredict AI</h1>
            </div>
            <div class="content">
              {body_html}
            </div>
            <div class="footer">
              This email was sent by HealthPredict AI. Do not reply to this message.
              If you did not request this action, please ignore this email or
              <a href="#" style="color:#64748b;">contact support</a>.
            </div>
          </div>
        </body>
        </html>
    """).strip()


def render_welcome(full_name: str | None, base_url: str) -> tuple[str, str]:
    """(subject, html) for the welcome / registration email."""
    name = full_name or "there"
    subject = "Welcome to HealthPredict AI"
    body = f"""
        <h2 style="margin-top:0">Welcome, {name}! 👋</h2>
        <p>Your HealthPredict AI account has been successfully created.</p>
        <p>You can now access your personalised risk predictions for Diabetes,
        Heart Disease, and Lung Cancer — all in one place.</p>
        <a href="{base_url}/dashboard" class="btn">Go to Dashboard</a>
        <hr class="divider"/>
        <p style="font-size:13px; color:#64748b;">
          If you didn't create this account, please
          <a href="{base_url}/support">contact us</a> immediately.
        </p>
    """
    return subject, _base_html(subject, body)


def render_password_reset(reset_url: str) -> tuple[str, str]:
    """(subject, html) for the password-reset email."""
    subject = "Reset your HealthPredict AI password"
    body = f"""
        <h2 style="margin-top:0">Password Reset Requested</h2>
        <p>We received a request to reset the password for your account.</p>
        <p>Click the button below to choose a new password.
        This link is valid for <strong>30 minutes</strong>.</p>
        <a href="{reset_url}" class="btn">Reset Password</a>
        <hr class="divider"/>
        <p style="font-size:13px; color:#64748b;">
          If you didn't request a password reset, you can safely ignore this email.
          Your password will remain unchanged.
        </p>
        <p style="font-size:13px; color:#64748b;">
          Link not working? Copy and paste this URL into your browser:<br/>
          <code>{reset_url}</code>
        </p>
    """
    return subject, _base_html(subject, body)


def render_email_verification(verify_url: str) -> tuple[str, str]:
    """(subject, html) for the email verification email."""
    subject = "Verify your HealthPredict AI email address"
    body = f"""
        <h2 style="margin-top:0">Verify Your Email</h2>
        <p>Please verify your email address to activate all features of
        your HealthPredict AI account.</p>
        <a href="{verify_url}" class="btn">Verify Email</a>
        <hr class="divider"/>
        <p style="font-size:13px; color:#64748b;">
          Link not working? Copy and paste this URL into your browser:<br/>
          <code>{verify_url}</code>
        </p>
    """
    return subject, _base_html(subject, body)


def render_new_login(
    ip_address: str, user_agent: str, base_url: str
) -> tuple[str, str]:
    """(subject, html) for a new-device login security alert."""
    subject = "New login detected — HealthPredict AI"
    body = f"""
        <h2 style="margin-top:0">&#x26A0;&#xFE0F; New Login Detected</h2>
        <p>A new login was detected on your HealthPredict AI account.</p>
        <table style="width:100%; border-collapse:collapse; font-size:14px;">
          <tr>
            <td style="padding:8px; color:#64748b; width:130px;">IP Address</td>
            <td style="padding:8px; font-weight:600;">{ip_address}</td>
          </tr>
          <tr style="background:#f8fafc;">
            <td style="padding:8px; color:#64748b;">Device / Browser</td>
            <td style="padding:8px; font-weight:600;">{user_agent}</td>
          </tr>
        </table>
        <p>If this was you, no action is needed.</p>
        <p>If you don't recognise this login, please secure your account
        immediately:</p>
        <a href="{base_url}/auth/password-reset-request" class="btn"
           style="background:#dc2626;">Secure My Account</a>
    """
    return subject, _base_html(subject, body)


def render_security_alert(title: str, message: str, base_url: str) -> tuple[str, str]:
    """(subject, html) for a generic security alert."""
    subject = f"Security Alert: {title} — HealthPredict AI"
    body = f"""
        <h2 style="margin-top:0">&#x1F6A8; Security Alert</h2>
        <h3 style="color:#dc2626; margin-top:0">{title}</h3>
        <p>{message}</p>
        <a href="{base_url}/security" class="btn" style="background:#dc2626;">
          Review Security Settings
        </a>
    """
    return subject, _base_html(subject, body)


def render_generic(title: str, message: str) -> tuple[str, str]:
    """(subject, html) for a generic notification email."""
    subject = f"{title} — HealthPredict AI"
    body = f"""
        <h2 style="margin-top:0">{title}</h2>
        <p>{message}</p>
    """
    return subject, _base_html(subject, body)


# ── Notification-type → template router ──────────────────────────────────────

_SECURITY_TYPES = {
    "new_login",
    "password_changed",
    "password_reset_request",
    "suspicious_login",
    "account_locked",
}


def build_email(
    notification_type: str,
    title: str,
    message: str,
    metadata: dict[str, Any] | None,
    base_url: str,
) -> tuple[str, str]:
    """
    Route a notification type to the appropriate HTML template.

    Returns ``(subject, html_body)``.
    """
    meta = metadata or {}

    if notification_type == "password_reset_request":
        token = meta.get("reset_token", "")
        reset_url = (
            meta.get("reset_url")
            or f"{base_url}/auth/password-reset-confirm?token={token}"
        )
        return render_password_reset(reset_url)

    if notification_type == "email_verification":
        token = meta.get("verify_token", "")
        verify_url = meta.get("verify_url") or f"{base_url}/auth/verify-email/{token}"
        return render_email_verification(verify_url)

    if notification_type == "user_registration":
        return render_welcome(meta.get("full_name"), base_url)

    if notification_type == "new_login":
        return render_new_login(
            meta.get("ip_address", "unknown"),
            meta.get("user_agent", "unknown"),
            base_url,
        )

    if notification_type in _SECURITY_TYPES:
        return render_security_alert(title, message, base_url)

    return render_generic(title, message)


# ── Abstract base ─────────────────────────────────────────────────────────────


class EmailBackend(ABC):
    """Abstract email delivery backend."""

    @abstractmethod
    async def send_email(
        self,
        to_address: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """Deliver a single email. Returns ``True`` on success."""
        ...


# ── Development backend ───────────────────────────────────────────────────────


class DevelopmentEmailBackend(EmailBackend):
    """Logs email content to the application logger. No real delivery."""

    async def send_email(
        self,
        to_address: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        logger.info(
            "dev_email_provider | to=%s | subject=%s | body_len=%d",
            to_address,
            subject,
            len(html_body),
        )
        return True


# ── SMTP backend ──────────────────────────────────────────────────────────────


class SMTPEmailBackend(EmailBackend):
    """
    Production SMTP backend using ``aiosmtplib``.

    Compatible with SendGrid, AWS SES, Mailgun, and any standard SMTP relay.
    All credentials are read from Settings — never hardcoded.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        from_address: str,
        from_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._from_address = from_address
        self._from_name = from_name

    async def send_email(
        self,
        to_address: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        try:
            import aiosmtplib  # deferred — not needed in dev mode

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self._from_name} <{self._from_address}>"
            msg["To"] = to_address

            if text_body:
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                use_tls=self._use_tls,
                start_tls=not self._use_tls,
            )
            logger.info("smtp_email_sent | to=%s | subject=%s", to_address, subject)
            return True

        except Exception as exc:
            logger.error(
                "smtp_email_failed | to=%s | subject=%s | error=%s",
                to_address,
                subject,
                exc,
            )
            return False


# ── Factory ───────────────────────────────────────────────────────────────────


def create_email_backend() -> EmailBackend:
    """
    Instantiate the configured email backend.

    Reads ``EMAIL_BACKEND`` from Settings:
      ``development``  → ``DevelopmentEmailBackend`` (default)
      ``smtp``         → ``SMTPEmailBackend``
    """
    from backend.app.core.config import \
        settings  # local import avoids circular

    backend_name = getattr(settings, "email_backend", "development").lower()

    if backend_name == "smtp":
        missing = [
            field
            for field in (
                "smtp_host",
                "smtp_username",
                "smtp_password",
                "email_from_address",
            )
            if not getattr(settings, field, "")
        ]
        if missing:
            logger.error(
                "smtp_backend_misconfigured | missing fields: %s | falling back to development",
                missing,
            )
            return DevelopmentEmailBackend()

        return SMTPEmailBackend(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            from_address=settings.email_from_address,
            from_name=settings.email_from_name,
        )

    if backend_name != "development":
        logger.warning(
            "unknown_email_backend=%s | defaulting to development", backend_name
        )
    return DevelopmentEmailBackend()


# ── Module-level singleton ────────────────────────────────────────────────────

email_backend: EmailBackend = create_email_backend()
