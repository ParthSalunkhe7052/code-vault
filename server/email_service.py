"""
Email Notification Service
Handles sending email notifications for license events.
Supports Resend, SendGrid and SMTP fallback.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Try to import Resend
try:
    import resend

    HAS_RESEND = True
except ImportError:
    HAS_RESEND = False

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content

    HAS_SENDGRID = True
except ImportError:
    HAS_SENDGRID = False

# Configuration
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "").lower()  # resend, sendgrid, smtp
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@codevault.local")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "CodeVault")
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

# Thread pool for async email sending
_executor = ThreadPoolExecutor(max_workers=2)


@dataclass
class EmailMessage:
    """Represents an email message."""

    to: str
    subject: str
    html_body: str
    text_body: Optional[str] = None


class EmailService:
    """Email service with Resend, SendGrid and SMTP support."""

    def __init__(self):
        self.use_resend = False
        self.use_sendgrid = False
        self.use_smtp = False

        # Check Resend first (preferred)
        if HAS_RESEND and RESEND_API_KEY:
            resend.api_key = RESEND_API_KEY
            self.use_resend = True
            print("[Email] Using Resend")
        elif HAS_SENDGRID and SENDGRID_API_KEY:
            self.sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
            self.use_sendgrid = True
            print("[Email] Using SendGrid")
        elif SMTP_HOST and SMTP_USER:
            self.use_smtp = True
            print("[Email] Using SMTP")
        else:
            print("[Email] No email provider configured")

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return EMAIL_ENABLED and (self.use_resend or self.use_sendgrid or self.use_smtp)

    def _send_via_resend(self, message: EmailMessage) -> bool:
        """Send email via Resend."""
        try:
            params = {
                "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
                "to": [message.to],
                "subject": message.subject,
                "html": message.html_body,
            }
            if message.text_body:
                params["text"] = message.text_body

            response = resend.Emails.send(params)
            return response.get("id") is not None
        except Exception as e:
            print(f"[Email] Resend error: {e}")
            return False

    def _send_via_sendgrid(self, message: EmailMessage) -> bool:
        """Send email via SendGrid."""
        if not hasattr(self, "sendgrid_client"):
            return False

        try:
            mail = Mail(
                from_email=Email(EMAIL_FROM, EMAIL_FROM_NAME),
                to_emails=To(message.to),
                subject=message.subject,
                html_content=Content("text/html", message.html_body),
            )
            response = self.sendgrid_client.send(mail)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"[Email] SendGrid error: {e}")
            return False

    def _send_via_smtp(self, message: EmailMessage) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
            msg["To"] = message.to

            if message.text_body:
                msg.attach(MIMEText(message.text_body, "plain"))
            msg.attach(MIMEText(message.html_body, "html"))

            if SMTP_USE_TLS:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)

            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)

            server.sendmail(EMAIL_FROM, message.to, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"[Email] SMTP error: {e}")
            return False

    def send(self, message: EmailMessage) -> bool:
        """Send an email message."""
        if not self.is_configured():
            print("[Email] Email service not configured, skipping")
            return False

        if self.use_resend:
            return self._send_via_resend(message)
        elif self.use_sendgrid:
            return self._send_via_sendgrid(message)
        elif self.use_smtp:
            return self._send_via_smtp(message)

        return False

    async def send_async(self, message: EmailMessage) -> bool:
        """Send email asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.send, message)


# Global email service instance
email_service = EmailService()


# =============================================================================
# Email Templates
# =============================================================================


def _get_base_template(content: str, title: str) -> str:
    """Wrap content in base email template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 32px;
            margin: 20px 0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .header h1 {{
            color: #6366f1;
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            margin: 24px 0;
        }}
        .alert {{
            padding: 16px;
            border-radius: 6px;
            margin: 16px 0;
        }}
        .alert-warning {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            color: #92400e;
        }}
        .alert-danger {{
            background-color: #fee2e2;
            border-left: 4px solid #ef4444;
            color: #991b1b;
        }}
        .alert-success {{
            background-color: #d1fae5;
            border-left: 4px solid #10b981;
            color: #065f46;
        }}
        .details {{
            background-color: #f8fafc;
            border-radius: 6px;
            padding: 16px;
            margin: 16px 0;
        }}
        .details-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
        }}
        .details-row:last-child {{
            border-bottom: none;
        }}
        .details-label {{
            color: #64748b;
            font-size: 14px;
        }}
        .details-value {{
            font-weight: 600;
            color: #1e293b;
        }}
        .button {{
            display: inline-block;
            background-color: #6366f1;
            color: white !important;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            margin: 16px 0;
        }}
        .footer {{
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
            margin-top: 32px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <h1>🔐 CodeVault</h1>
            </div>
            {content}
        </div>
        <div class="footer">
            <p>This is an automated message from CodeVault.</p>
            <p>© {datetime.now().year} CodeVault. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""


def create_license_expiry_warning_email(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    expires_at: datetime,
    days_remaining: int,
) -> EmailMessage:
    """Create email for license expiry warning."""
    content = f"""
    <div class="content">
        <p>Hello {client_name or "Customer"},</p>
        
        <div class="alert alert-warning">
            <strong>⚠️ License Expiring Soon</strong><br>
            Your license will expire in <strong>{days_remaining} day(s)</strong>.
        </div>
        
        <p>Please renew your license to continue using the software without interruption.</p>
        
        <div class="details">
            <div class="details-row">
                <span class="details-label">License Key</span>
                <span class="details-value">{license_key}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Product</span>
                <span class="details-value">{project_name}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Expires On</span>
                <span class="details-value">{expires_at.strftime("%B %d, %Y at %H:%M UTC")}</span>
            </div>
        </div>
        
        <p>If you have any questions or need assistance with renewal, please contact our support team.</p>
        
        <p>Best regards,<br>The CodeVault Team</p>
    </div>
    """

    return EmailMessage(
        to=client_email,
        subject=f"⚠️ License Expiring in {days_remaining} Days - {project_name}",
        html_body=_get_base_template(content, "License Expiry Warning"),
        text_body=f"Your license for {project_name} will expire in {days_remaining} days on {expires_at.strftime('%B %d, %Y')}. Please renew to continue using the software.",
    )


def create_license_expired_email(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    expired_at: datetime,
) -> EmailMessage:
    """Create email for license expiration."""
    content = f"""
    <div class="content">
        <p>Hello {client_name or "Customer"},</p>
        
        <div class="alert alert-danger">
            <strong>❌ License Expired</strong><br>
            Your license has expired and is no longer valid.
        </div>
        
        <p>Your access to the software has been suspended. Please renew your license to restore access.</p>
        
        <div class="details">
            <div class="details-row">
                <span class="details-label">License Key</span>
                <span class="details-value">{license_key}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Product</span>
                <span class="details-value">{project_name}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Expired On</span>
                <span class="details-value">{expired_at.strftime("%B %d, %Y at %H:%M UTC")}</span>
            </div>
        </div>
        
        <p>If you believe this is an error or need assistance, please contact our support team.</p>
        
        <p>Best regards,<br>The CodeVault Team</p>
    </div>
    """

    return EmailMessage(
        to=client_email,
        subject=f"❌ License Expired - {project_name}",
        html_body=_get_base_template(content, "License Expired"),
        text_body=f"Your license for {project_name} expired on {expired_at.strftime('%B %d, %Y')}. Please renew to restore access.",
    )


def create_license_revoked_email(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    reason: str = "",
) -> EmailMessage:
    """Create email for license revocation."""
    reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""

    content = f"""
    <div class="content">
        <p>Hello {client_name or "Customer"},</p>
        
        <div class="alert alert-danger">
            <strong>🚫 License Revoked</strong><br>
            Your license has been revoked and is no longer valid.
        </div>
        
        {reason_text}
        
        <div class="details">
            <div class="details-row">
                <span class="details-label">License Key</span>
                <span class="details-value">{license_key}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Product</span>
                <span class="details-value">{project_name}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Revoked On</span>
                <span class="details-value">{datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")}</span>
            </div>
        </div>
        
        <p>If you believe this was done in error, please contact our support team immediately.</p>
        
        <p>Best regards,<br>The CodeVault Team</p>
    </div>
    """

    return EmailMessage(
        to=client_email,
        subject=f"🚫 License Revoked - {project_name}",
        html_body=_get_base_template(content, "License Revoked"),
        text_body=f"Your license for {project_name} has been revoked. Please contact support if you believe this is an error.",
    )


def create_new_license_email(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    expires_at: Optional[datetime],
    max_machines: int,
    features: List[str],
) -> EmailMessage:
    """Create email for new license issuance."""
    expiry_text = (
        expires_at.strftime("%B %d, %Y") if expires_at else "Never (Perpetual)"
    )
    features_text = ", ".join(features) if features else "Standard"

    content = f"""
    <div class="content">
        <p>Hello {client_name or "Customer"},</p>
        
        <div class="alert alert-success">
            <strong>✅ License Activated</strong><br>
            Your new license has been issued and is ready to use.
        </div>
        
        <p>Thank you for your purchase! Here are your license details:</p>
        
        <div class="details">
            <div class="details-row">
                <span class="details-label">License Key</span>
                <span class="details-value" style="font-family: monospace;">{license_key}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Product</span>
                <span class="details-value">{project_name}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Expires</span>
                <span class="details-value">{expiry_text}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Max Machines</span>
                <span class="details-value">{max_machines}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Features</span>
                <span class="details-value">{features_text}</span>
            </div>
        </div>
        
        <p><strong>Important:</strong> Please keep your license key safe. Do not share it publicly.</p>
        
        <p>If you have any questions, please contact our support team.</p>
        
        <p>Best regards,<br>The CodeVault Team</p>
    </div>
    """

    return EmailMessage(
        to=client_email,
        subject=f"✅ Your License for {project_name}",
        html_body=_get_base_template(content, "License Issued"),
        text_body=f"Your license for {project_name} has been issued. License Key: {license_key}. Expires: {expiry_text}",
    )


# =============================================================================
# Notification Functions (to be called from main.py)
# =============================================================================


async def notify_license_created(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    expires_at: Optional[datetime],
    max_machines: int,
    features: List[str],
) -> bool:
    """Send notification when a new license is created."""
    if not client_email:
        return False

    message = create_new_license_email(
        client_name,
        client_email,
        license_key,
        project_name,
        expires_at,
        max_machines,
        features,
    )
    return await email_service.send_async(message)


async def notify_license_revoked(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    reason: str = "",
) -> bool:
    """Send notification when a license is revoked."""
    if not client_email:
        return False

    message = create_license_revoked_email(
        client_name, client_email, license_key, project_name, reason
    )
    return await email_service.send_async(message)


async def notify_license_expiring(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    expires_at: datetime,
    days_remaining: int,
) -> bool:
    """Send notification when a license is about to expire."""
    if not client_email:
        return False

    message = create_license_expiry_warning_email(
        client_name, client_email, license_key, project_name, expires_at, days_remaining
    )
    return await email_service.send_async(message)


async def notify_license_expired(
    client_name: str,
    client_email: str,
    license_key: str,
    project_name: str,
    expired_at: datetime,
) -> bool:
    """Send notification when a license has expired."""
    if not client_email:
        return False

    message = create_license_expired_email(
        client_name, client_email, license_key, project_name, expired_at
    )
    return await email_service.send_async(message)


# Testing
if __name__ == "__main__":
    # Test email templates
    msg = create_license_expiry_warning_email(
        "John Doe",
        "john@example.com",
        "LIC-XXXX-XXXX-XXXX",
        "My App",
        datetime.now(),
        7,
    )
    print("Subject:", msg.subject)
    print("To:", msg.to)
    print("HTML Length:", len(msg.html_body))
