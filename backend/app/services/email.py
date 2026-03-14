import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def send_reset_email(to_email: str, reset_url: str):
    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
      <div style="font-size:1.4rem;font-weight:800;color:#0f172a;margin-bottom:8px">costly</div>
      <h2 style="font-size:1.1rem;color:#0f172a;margin:0 0 12px">Reset your password</h2>
      <p style="color:#64748b;font-size:0.9rem;line-height:1.6;margin:0 0 24px">
        We received a request to reset your password. Click the button below.
        This link expires in <strong>30 minutes</strong>.
      </p>
      <a href="{reset_url}"
         style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;
                padding:12px 28px;border-radius:8px;font-weight:700;font-size:0.95rem">
        Reset Password
      </a>
      <p style="color:#94a3b8;font-size:0.8rem;margin-top:24px">
        If you didn't request this, you can safely ignore this email.
        Your password won't change.
      </p>
      <hr style="border:none;border-top:1px solid #f1f5f9;margin:24px 0"/>
      <p style="color:#cbd5e1;font-size:0.75rem">costly - Snowflake Cost Intelligence</p>
    </div>
    """
    text = f"Reset your costly password: {reset_url}\n\nThis link expires in 30 minutes."

    if not settings.smtp_host or not settings.smtp_user:
        print(f"[RESET PASSWORD] SMTP not configured - reset URL for {to_email}: {reset_url}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your costly password"
    msg["From"] = f"costly <{settings.smtp_from}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, to_email, msg.as_string())


def send_alert_email(to_email: str, alert_name: str, metric: str, threshold: float, current_value: float):
    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
      <div style="font-size:1.4rem;font-weight:800;color:#0f172a;margin-bottom:8px">costly</div>
      <h2 style="font-size:1.1rem;color:#0f172a;margin:0 0 12px">Alert: {alert_name}</h2>
      <p style="color:#64748b;font-size:0.9rem;line-height:1.6;margin:0 0 24px">
        Metric <strong>{metric}</strong> has reached <strong>{current_value:.2f}</strong>
        (threshold: {threshold:.2f}).
      </p>
      <hr style="border:none;border-top:1px solid #f1f5f9;margin:24px 0"/>
      <p style="color:#cbd5e1;font-size:0.75rem">costly - Snowflake Cost Intelligence</p>
    </div>
    """
    text = f"Alert fired: {alert_name} - {metric} = {current_value:.2f} (threshold: {threshold:.2f})"

    if not settings.smtp_host or not settings.smtp_user:
        print(f"[ALERT EMAIL] SMTP not configured - {text}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"costly Alert: {alert_name}"
    msg["From"] = f"costly <{settings.smtp_from}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, to_email, msg.as_string())
