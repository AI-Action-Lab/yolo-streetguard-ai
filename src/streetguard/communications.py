import asyncio
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from urllib.parse import quote

from streetguard.config import Settings
from streetguard.models.core import Location, Report

_EMAIL_ADDRESS = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


class EmailProviderNotConfigured(RuntimeError):
    pass


def valid_email_address(value: str) -> bool:
    return len(value) <= 320 and _EMAIL_ADDRESS.fullmatch(value) is not None


def public_report_url(settings: Settings, public_id: str) -> str:
    base_url = str(settings.public_base_url).rstrip("/")
    return f"{base_url}/track/{quote(public_id, safe='')}"


def report_email_content(
    report: Report,
    location: Location,
    settings: Settings,
    *,
    status_update: bool = False,
) -> tuple[str, str]:
    label = "Report status update" if status_update else "Road damage report"
    subject = f"{label}: {report.public_id}"
    tracking_line = (
        f"View public report: {public_report_url(settings, report.public_id)}"
        if report.visibility == "public"
        else "This report is not publicly visible while it is under review."
    )
    lines = [
        "YOLO StreetGuard AI",
        "",
        f"Report ID: {report.public_id}",
        f"Status: {report.status.replace('_', ' ')}",
        f"Issue: {report.title or 'Road damage report'}",
        f"Location: {location.formatted_address or 'Address unavailable'}",
        f"Visual severity estimate: {report.severity or 'unavailable'}",
        tracking_line,
        "",
        "Severity is an image-based estimate, not a measurement of pothole depth or road risk.",
    ]
    return subject, "\n".join(lines)


def _send_smtp(
    settings: Settings,
    recipient: str,
    subject: str,
    body: str,
) -> str:
    if not settings.smtp_configured:
        raise EmailProviderNotConfigured("SMTP email delivery is not configured")
    if not valid_email_address(settings.smtp_from_email):
        raise EmailProviderNotConfigured("SMTP sender address is invalid")

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message["Message-ID"] = make_msgid()
    message.set_content(body)

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
            context=ssl.create_default_context(),
        ) as client:
            if settings.smtp_username:
                client.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
            client.send_message(message)
    else:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as client:
            if settings.smtp_starttls:
                client.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                client.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
            client.send_message(message)
    return str(message["Message-ID"])


async def send_smtp_email(
    settings: Settings,
    recipient: str,
    subject: str,
    body: str,
) -> str:
    return await asyncio.to_thread(_send_smtp, settings, recipient, subject, body)
