"""
payment_checker.py
==================
Gmail IMAP se FamePay payment verify karta hai.
asyncio.run_in_executor use karta hai taaki bot block na ho.
"""

import imaplib
import email
import re
import os
import asyncio
from datetime import datetime, timedelta

GMAIL_USER     = os.getenv("GMAIL_USER", "").strip()
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")

FAMPAY_KEYWORDS = [
    "fampay", "FamPay", "fam pay",
    "received", "credited", "payment",
    "noreply@fampay.in", "alerts@fampay.in"
]


def _sync_verify(expected_amount: float, timeout_minutes: int = 15) -> dict:
    """
    Synchronous Gmail check — runs in thread pool via executor.
    DO NOT call this directly in async code.
    """
    if not GMAIL_USER or not GMAIL_PASSWORD:
        return {"verified": False, "message": "Gmail credentials not set in Railway variables"}

    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")

        since = (datetime.now() - timedelta(minutes=timeout_minutes)).strftime("%d-%b-%Y")

        # Search strategies
        search_queries = [
            f'(FROM "fampay.in" SINCE "{since}")',
            f'(SUBJECT "received" SINCE "{since}")',
            f'(SUBJECT "credited" SINCE "{since}")',
            f'(SUBJECT "FamPay" SINCE "{since}")',
            f'(SUBJECT "payment" SINCE "{since}")',
            f'(FROM "noreply@fampay.in")',
            f'(FROM "alerts@fampay.in")',
        ]

        all_ids = set()
        for query in search_queries:
            try:
                _, data = mail.search(None, query)
                if data and data[0]:
                    for uid in data[0].split():
                        all_ids.add(uid)
            except Exception:
                continue

        if not all_ids:
            mail.logout()
            return {
                "verified": False,
                "message": "No FamePay emails found in last 15 minutes"
            }

        # Check latest emails first (reverse order)
        sorted_ids = sorted(list(all_ids), reverse=True)

        for num in sorted_ids[:30]:
            try:
                _, msg_data = mail.fetch(num, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue

                raw     = msg_data[0][1]
                msg     = email.message_from_bytes(raw)
                body    = _extract_body(msg)
                full    = body.lower()

                # Must be FamePay related
                is_fampay = any(kw.lower() in full for kw in FAMPAY_KEYWORDS)
                if not is_fampay:
                    continue

                # Extract amount
                amount = _extract_amount(body)
                if amount is None:
                    continue

                # Check if amount matches (within 0.01 tolerance)
                if abs(amount - expected_amount) <= 0.01:
                    utr = _extract_utr(body)
                    mail.logout()
                    return {
                        "verified": True,
                        "amount":   amount,
                        "utr":      utr,
                        "message":  "✅ Payment verified!"
                    }

            except Exception:
                continue

        mail.logout()
        return {
            "verified": False,
            "message": f"₹{expected_amount:.2f} ka payment email nahi mila"
        }

    except imaplib.IMAP4.error as e:
        err = str(e)
        if "invalid credentials" in err.lower() or "authentication" in err.lower():
            return {
                "verified": False,
                "message": "❌ Gmail login failed — App Password check karo (spaces hata do)"
            }
        return {"verified": False, "message": f"Gmail error: {err}"}
    except Exception as e:
        return {"verified": False, "message": f"Error: {str(e)}"}


def _extract_body(msg) -> str:
    """Extract full text from email."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
                try:
                    body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return body


def _extract_amount(text: str) -> float | None:
    """Extract INR amount from email text."""
    patterns = [
        r"₹\s*(\d+\.?\d*)",
        r"Rs\.?\s*(\d+\.?\d*)",
        r"INR\s*(\d+\.?\d*)",
        r"(\d+\.\d{2})\s*(?:INR|₹|Rs)",
        r"amount.*?(\d+\.?\d*)",
        r"received.*?(\d+\.?\d*)",
        r"credited.*?(\d+\.?\d*)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if val > 0:
                    return val
            except Exception:
                pass
    return None


def _extract_utr(text: str) -> str:
    """Extract UTR/transaction reference from email."""
    patterns = [
        r"UTR[:\s#]*([A-Z0-9]{10,22})",
        r"UPI[:\s]+Ref[:\s#]*([A-Z0-9]{10,22})",
        r"Transaction\s+ID[:\s#]*([A-Z0-9]{10,22})",
        r"Ref\.?\s*No[:\s.]*([A-Z0-9]{10,22})",
        r"Reference[:\s#]*([A-Z0-9]{10,22})",
        r"\b([0-9]{12,20})\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return "N/A"


# ── Async wrapper ──────────────────────────────────────────────────────────────

async def verify_payment(expected_amount: float, timeout_minutes: int = 15) -> dict:
    """
    Async wrapper — runs IMAP check in thread pool so bot doesn't freeze.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _sync_verify(expected_amount, timeout_minutes)
    )
    return result


# ── Test function ──────────────────────────────────────────────────────────────

async def test_connection() -> dict:
    """Test Gmail connection without checking any payment."""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        return {"ok": False, "message": "GMAIL_USER or GMAIL_APP_PASSWORD not set"}
    try:
        loop = asyncio.get_event_loop()
        def _test():
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(GMAIL_USER, GMAIL_PASSWORD)
            mail.select("inbox")
            mail.logout()
            return True
        await loop.run_in_executor(None, _test)
        return {"ok": True, "message": f"✅ Connected to {GMAIL_USER}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


checker = PaymentChecker = type("PaymentChecker", (), {
    "verify_payment": staticmethod(verify_payment),
    "test_connection": staticmethod(test_connection),
})()
