import os
import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple

from backend.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL
)

def send_verification_email(recipient_email: str, recipient_name: str, verification_code: str) -> Tuple[bool, str, str]:
    """
    Sends 6-digit email verification code to user's email via SMTP server.
    Returns (success: bool, user_message: str, error_case: str).
    
    Distinguishes error cases:
    - CASE 1: Verification email successfully handed to SMTP server.
    - CASE 2: SMTP authentication failed.
    - CASE 3: SMTP connection failed.
    - CASE 4: Invalid SMTP configuration.
    - CASE 5: Recipient rejected.
    - CASE 6: Other email-sending error.
    
    Does NOT log or expose sensitive credentials.
    """
    host = os.getenv("SMTP_HOST", SMTP_HOST).strip()
    try:
        port = int(os.getenv("SMTP_PORT", str(SMTP_PORT)))
    except (ValueError, TypeError):
        port = 587

    username = os.getenv("SMTP_USERNAME", SMTP_USERNAME).strip()
    password = os.getenv("SMTP_PASSWORD", SMTP_PASSWORD).strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", SMTP_FROM_EMAIL).strip() or username or "noreply@wayvista.com"

    # CASE 4: Invalid SMTP configuration
    if not host or not username or not password or host.startswith("your_") or username.startswith("your_"):
        print("[EmailService Diagnostic] CASE 4: Invalid SMTP configuration (missing environment variables).")
        return False, "SMTP email service is not configured on the server. Please set valid SMTP environment variables in .env file.", "CASE_4_INVALID_CONFIG"

    subject = "WayVista Email Verification Code"

    text_content = (
        f"Hello {recipient_name},\n\n"
        f"Your WayVista verification code is:\n\n"
        f"{verification_code}\n\n"
        f"This code will expire in 10 minutes.\n\n"
        f"If you did not create this account, you can ignore this email."
    )

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #090d16; color: #f8fafc; margin: 0; padding: 20px;">
    <div style="max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(59, 130, 246, 0.35); border-radius: 16px; padding: 30px; text-align: center;">
        <h2 style="color: #ffffff; margin-bottom: 8px;">✈️ WayVista</h2>
        <p style="color: #94a3b8; font-size: 14px; margin-top: 0; margin-bottom: 24px;">Smart Travel • Smarter Journeys</p>
        
        <p style="font-size: 15px; color: #cbd5e1; text-align: left; margin-bottom: 8px;">Hello <strong>{recipient_name}</strong>,</p>
        <p style="font-size: 15px; color: #cbd5e1; text-align: left;">Your WayVista verification code is:</p>
        
        <div style="background: rgba(59, 130, 246, 0.15); border: 1px dashed #3b82f6; color: #60a5fa; font-size: 34px; font-weight: bold; letter-spacing: 8px; padding: 16px; border-radius: 12px; margin: 24px 0;">
            {verification_code}
        </div>
        
        <p style="font-size: 14px; color: #94a3b8; text-align: left; margin-bottom: 6px;">This code will expire in 10 minutes.</p>
        <p style="font-size: 13px; color: #64748b; text-align: left; margin-top: 0;">If you did not create this account, you can ignore this email.</p>
    </div>
</body>
</html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = recipient_email

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=12) as server:
                server.login(username, password)
                server.sendmail(from_email, recipient_email, msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=12) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(from_email, recipient_email, msg.as_string())

        print(f"[EmailService Diagnostic] CASE 1: Verification email successfully handed to SMTP server for {recipient_email}")
        return True, "Verification email sent successfully.", "CASE_1_SUCCESS"

    except smtplib.SMTPAuthenticationError:
        print("[EmailService Diagnostic] CASE 2: SMTP authentication failed.")
        return False, "SMTP authentication failed. Please check your email address and App Password in server configuration.", "CASE_2_AUTH_FAILED"

    except (smtplib.SMTPConnectError, socket.error, TimeoutError) as conn_err:
        print(f"[EmailService Diagnostic] CASE 3: SMTP connection failed ({type(conn_err).__name__}).")
        return False, "SMTP connection failed. Could not connect to email server.", "CASE_3_CONN_FAILED"

    except smtplib.SMTPRecipientsRefused:
        print("[EmailService Diagnostic] CASE 5: Recipient email rejected.")
        return False, "Recipient email address was rejected by the SMTP server.", "CASE_5_RECIPIENT_REJECTED"

    except smtplib.SMTPException as smtp_err:
        print(f"[EmailService Diagnostic] CASE 6: SMTP protocol exception ({type(smtp_err).__name__}).")
        return False, "SMTP sending error occurred while communicating with email provider.", "CASE_6_OTHER_ERROR"

    except Exception as gen_err:
        print(f"[EmailService Diagnostic] CASE 6: General email dispatch error ({type(gen_err).__name__}).")
        return False, "Failed to send verification email due to an unexpected error.", "CASE_6_OTHER_ERROR"
