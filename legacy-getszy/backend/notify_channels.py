"""Multi-channel notification delivery with encrypted credentials at rest."""
import json
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

from db import db
from routes_integrations import _decrypt_credentials

_SECRET_FIELDS = ('smtp_pass', 'whatsapp_token')


async def get_channels_config(*, include_credentials: bool = False) -> dict:
    """Return notification configuration, decrypting secrets only for delivery."""
    cfg = await db.notification_config.find_one({}, {'_id': 0}) or {}
    encrypted = cfg.pop('credentials_encrypted', None)
    if encrypted:
        try:
            secrets = _decrypt_credentials(encrypted)
        except Exception as exc:
            if include_credentials:
                raise RuntimeError('notification credential decryption failed') from exc
            secrets = {}
        if include_credentials:
            cfg.update(secrets)
        else:
            for field in _SECRET_FIELDS:
                cfg[f'{field}_configured'] = bool(secrets.get(field))
    elif not include_credentials:
        # Hide legacy plaintext values while reporting the configuration state.
        for field in _SECRET_FIELDS:
            cfg[f'{field}_configured'] = bool(cfg.pop(field, None))
    return cfg


async def dispatch(title: str, message: str, emails=None, phones=None):
    """Send configured channels; delivery failures never interrupt the caller."""
    results = {'email': 'not_configured', 'whatsapp': 'not_configured'}
    try:
        cfg = await get_channels_config(include_credentials=True)
    except Exception:
        return {'email': 'configuration_error', 'whatsapp': 'configuration_error'}

    emails = [email for email in (emails or []) if email]
    phones = [phone for phone in (phones or []) if phone]

    if emails and cfg.get('email_enabled') and cfg.get('smtp_host'):
        try:
            _send_email(cfg, title, message, emails)
            results['email'] = 'sent'
        except Exception as exc:
            results['email'] = f'error: {str(exc)[:160]}'
    if phones and cfg.get('whatsapp_enabled') and cfg.get('whatsapp_api_url'):
        try:
            _send_whatsapp(cfg, title, message, phones)
            results['whatsapp'] = 'sent'
        except Exception as exc:
            results['whatsapp'] = f'error: {str(exc)[:160]}'
    return results


def _send_email(cfg: dict, title: str, message: str, emails: list):
    msg = EmailMessage()
    msg['Subject'] = title
    msg['From'] = cfg.get('smtp_from') or cfg.get('smtp_user')
    msg['To'] = ', '.join(emails)
    msg.set_content(message)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(cfg['smtp_host'], int(cfg.get('smtp_port', 465)), context=ctx) as smtp:
        if cfg.get('smtp_user'):
            smtp.login(cfg['smtp_user'], cfg.get('smtp_pass', ''))
        smtp.send_message(msg)


def _send_whatsapp(cfg: dict, title: str, message: str, phones: list):
    url = cfg['whatsapp_api_url']
    body = f"{title}\n\n{message}"
    for phone in phones:
        payload = json.dumps({'phone': phone, 'message': body}).encode()
        request = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {cfg.get('whatsapp_token', '')}"},
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            _ = response.status
