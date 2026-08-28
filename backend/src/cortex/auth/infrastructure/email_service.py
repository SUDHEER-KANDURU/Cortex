"""Email service — sends transactional emails via SMTP (async).

Supports: email verification, password reset, and generic notifications.
Falls back gracefully when SMTP is not configured (logs a warning, doesn't crash).
"""

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import structlog

from cortex.config import Settings

logger = structlog.get_logger()


class EmailService:
    """Async SMTP email sender with HTML templates."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._from_email = settings.smtp_from_email
        self._from_name = settings.smtp_from_name
        self._use_tls = settings.smtp_use_tls
        self._frontend_url = settings.frontend_url.rstrip("/")

    @property
    def is_configured(self) -> bool:
        """Returns True if SMTP credentials are set."""
        return bool(self._host and self._user and self._password)

    async def send_verification_email(self, to_email: str, name: str, token: str) -> bool:
        """Send email verification OTP code."""
        subject = "Your Cortex verification code"
        html = self._render_otp_template(name, token, "verify your email address")
        return await self._send(to_email, subject, html)

    async def send_password_reset_email(self, to_email: str, name: str, token: str) -> bool:
        """Send password reset OTP code."""
        subject = "Your Cortex password reset code"
        html = self._render_otp_template(name, token, "reset your password")
        return await self._send(to_email, subject, html)

    async def _send(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send an HTML email via SMTP. Returns True on success."""
        if not self.is_configured:
            logger.warning(
                "email_not_sent_smtp_not_configured",
                to=to_email,
                subject=subject,
                hint="Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in backend/.env",
            )
            return False

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Plain-text fallback
        plain = f"Please open this link in your browser: {html_body}"
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._user,
                password=self._password,
                start_tls=self._use_tls,
                timeout=10,
            )
            logger.info("email_sent", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("email_send_failed", to=to_email, error=str(e))
            return False

    # ── HTML Email Templates ─────────────────────────────────────────────────

    def _render_otp_template(self, name: str, otp_code: str, purpose: str) -> str:
        # Split OTP into individual digits for styled display
        digits_html = "".join(
            f'<td style="width:40px;height:48px;text-align:center;font-size:24px;font-weight:700;'
            f'color:#1A1814;background:#F4F2EE;border-radius:8px;border:1px solid #EDEAE6;'
            f'font-family:\'Courier New\',monospace;letter-spacing:0;">{d}</td>'
            for d in otp_code
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#F0EEEB;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
    <tr><td align="center">
      <table width="100%" style="max-width:480px;background:#FFFFFF;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="padding:32px 40px 16px;text-align:center;">
            <h1 style="margin:0;font-size:22px;font-weight:700;color:#1A1814;letter-spacing:-0.03em;">Cortex</h1>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:0 40px 32px;text-align:center;">
            <p style="margin:0 0 20px;font-size:14px;line-height:1.6;color:#6B6560;">
              Hi {name},<br><br>
              Use this code to {purpose}:
            </p>
            <!-- OTP Code Display -->
            <table cellpadding="0" cellspacing="6" style="margin:0 auto 24px;">
              <tr>
                {digits_html}
              </tr>
            </table>
            <p style="margin:0;font-size:12px;line-height:1.5;color:#9A9590;">
              Enter this code on the Cortex verification page.<br>
              This code expires in 24 hours.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px;background:#F9F8F6;border-top:1px solid #EDEAE6;">
            <p style="margin:0;font-size:11px;color:#9A9590;text-align:center;">
              If you didn't request this code, you can safely ignore this email.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
