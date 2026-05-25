"""
通用郵件寄送服務

提供：
- send_otp_email()：寄送一次性密碼給使用者
- send_simple_email()：通用純文字 / HTML 郵件
"""
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

from app.core.config import settings


def _send(
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    text_body: str,
    attachment: Optional[tuple[str, bytes]] = None,
) -> None:
    """底層 SMTP 寄信（同步，呼叫者自行處理 exception）。"""
    if not settings.MAIL_HOST:
        raise RuntimeError("MAIL_HOST 未設定，請在 .env 中設定郵件伺服器參數")

    msg = MIMEMultipart("mixed")
    from_addr = settings.MAIL_FROM or settings.MAIL_USERNAME
    msg["From"]    = formataddr((settings.MAIL_FROM_NAME, from_addr))
    msg["To"]      = formataddr((to_name, to_email)) if to_name else to_email
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html",  "utf-8"))
    msg.attach(alt)

    if attachment:
        filename, data = attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=("utf-8", "", filename),
        )
        msg.attach(part)

    with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_SMTP_PORT, timeout=30) as server:
        server.ehlo()
        if settings.MAIL_USE_TLS:
            ctx = ssl.create_default_context()
            ctx.set_ciphers("DEFAULT@SECLEVEL=1")
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            server.starttls(context=ctx)
            server.ehlo()
        if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.sendmail(from_addr, [to_email], msg.as_bytes())


def send_otp_email(to_email: str, to_name: str, otp: str, expires_minutes: int = 15) -> None:
    """
    寄送一次性密碼（OTP）給使用者。

    :param to_email: 收件人 email
    :param to_name: 收件人姓名
    :param otp: 明文 OTP（6 位數字）
    :param expires_minutes: 有效期（分鐘）
    """
    subject = "【集團管理 Portal】一次性登入密碼"

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background:#f0f4f8; padding:32px;">
  <div style="max-width:480px; margin:0 auto; background:#fff; border-radius:12px;
              box-shadow:0 2px 8px rgba(27,58,92,0.10); overflow:hidden;">
    <div style="background:linear-gradient(135deg,#1B3A5C,#4BA8E8); padding:24px 32px;">
      <h2 style="color:#fff; margin:0; font-size:20px;">集團管理 Portal</h2>
      <p style="color:rgba(255,255,255,0.8); margin:4px 0 0; font-size:13px;">維春集團內部作業與管理平台</p>
    </div>
    <div style="padding:32px;">
      <p style="color:#374151; font-size:15px;">您好，{to_name}，</p>
      <p style="color:#374151; font-size:14px;">
        您已申請重設密碼。請使用以下一次性密碼登入，登入後系統將強制您設定新密碼。
      </p>
      <div style="text-align:center; margin:24px 0;">
        <div style="display:inline-block; background:#f0f4f8; border:2px dashed #4BA8E8;
                    border-radius:8px; padding:16px 32px;">
          <span style="font-size:36px; font-weight:700; letter-spacing:8px;
                       color:#1B3A5C; font-family:monospace;">{otp}</span>
        </div>
      </div>
      <p style="color:#ef4444; font-size:13px; text-align:center; margin:0 0 16px;">
        ⏱ 此密碼 <strong>{expires_minutes} 分鐘</strong>內有效，請盡快使用
      </p>
      <hr style="border:none; border-top:1px solid #e5e7eb; margin:16px 0;">
      <p style="color:#9ca3af; font-size:12px;">
        若您未申請重設密碼，請忽略此信。如有疑問，請聯繫系統管理員。
      </p>
    </div>
  </div>
</body>
</html>
""".strip()

    text_body = (
        f"您好 {to_name}，\n\n"
        f"您的一次性登入密碼為：{otp}\n\n"
        f"此密碼 {expires_minutes} 分鐘內有效，登入後請立即設定新密碼。\n\n"
        "若您未申請重設密碼，請忽略此信。"
    )

    _send(to_email, to_name, subject, html_body, text_body)
