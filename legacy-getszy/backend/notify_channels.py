"""Multi-channel notification delivery (Tier 3).

Dispatches a message across configured channels:
  - in_app   : always (handled by caller via db + WS)
  - email    : SMTP (SSL) when configured
  - whatsapp : HTTP POST to a configured gateway (e.g. WhatsApp Business API)

All failures are caught so a broken channel never breaks the caller.
"""
import json
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

from db import db


async def get_channels_config():
    cfg = await db.notification_config.find_one({}, {'_id': 0})
    return cfg or {}


async def dispatch(title: str, message: str, emails=None, phones=None):
    cfg = await get_channels_config()
    results = {'email': 'not_configured', 'whatsapp': 'not_configured'}
    if emails:
        emails = [e for e in emails if e]
    if phones:
        phones = [p for p in phones if p]

    if emails and cfg.get('email_enabled') and cfg.get('smtp_host'):
        try:
            _send_email(cfg, title, message, emails)
            results['email'] = 'sent'
        except Exception as e:
            results['email'] = f'error: {str(e)[:160]}'
    if phones and cfg.get('whatsapp_enabled') and cfg.get('whatsapp_api_url'):
        try:
            _send_whatsapp(cfg, title, message, phones)
            results['whatsapp'] = 'sent'
        except Exception as e:
            results['whatsapp'] = f'error: {str(e)[:160]}'
    return results


def _send_email(cfg: dict, title: str, message: str, emails: list):
    msg = EmailMessage()
    msg['Subject'] = title
    msg['From'] = cfg.get('smtp_from') or cfg.get('smtp_user')
    msg['To'] = ', '.join(emails)
    msg.set_content(message)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(cfg['smtp_host'], int(cfg.get('smtp_port', 465)), context=ctx) as s:
        if cfg.get('smtp_user'):
            s.login(cfg['smtp_user'], cfg.get('smtp_pass', ''))
        s.send_message(msg)


def _send_whatsapp(cfg: dict, title: str, message: str, phones: list):
    url = cfg['whatsapp_api_url']
    body = f"{title}\n\n{message}"
    for phone in phones:
        payload = json.dumps({'phone': phone, 'message': body}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {cfg.get('whatsapp_token', '')}"},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            _ = resp.status
