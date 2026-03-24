import asyncio
import os
import random
from email.message import EmailMessage
from typing import Any

import aiosmtplib


async def cancel_order(order_id: str) -> dict[str, Any]:
    """Mock order cancellation tool with 20% failure rate."""
    await asyncio.sleep(0)
    if random.random() < 0.2:
        return {
            "ok": False,
            "order_id": order_id,
            "reason": "Simulated cancellation failure",
        }
    return {"ok": True, "order_id": order_id, "reason": None}


async def send_email(email: str, message: str) -> dict[str, Any]:
    """Send a real email via SMTP over TLS using env-based config."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user

    missing = [name for name, val in [
        ("SMTP_HOST", smtp_host),
        ("SMTP_USER", smtp_user),
        ("SMTP_PASS", smtp_pass),
        ("SMTP_FROM", smtp_from),
    ] if not val]
    if missing:
        return {
            "ok": False,
            "email": email,
            "message": message,
            "reason": f"Missing SMTP config: {', '.join(missing)}",
        }

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = email
    msg["Subject"] = "Order Cancellation Confirmation"
    msg.set_content(message)

    use_starttls = smtp_port == 587
    use_tls = smtp_port == 465

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_pass,
            start_tls=use_starttls,
            use_tls=use_tls,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "email": email,
            "message": message,
            "reason": f"SMTP send failed: {exc}",
        }

    await asyncio.sleep(1)
    return {"ok": True, "email": email, "message": message}
