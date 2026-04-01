import os
import smtplib
from email.mime.text import MIMEText

def _smtp_host():
  return os.environ.get('RUDDWEB_SMTP_HOST', 'localhost').strip() or 'localhost'

def _smtp_port():
  raw = os.environ.get('RUDDWEB_SMTP_PORT', '25')
  try:
    return int(raw)
  except ValueError:
    return 25

def _normalize_recipients(to):
  """
  Normalize to a list of unique email strings (order preserved for str/list input).
  Accepts: str (one address or comma-separated), list, tuple, or set of str.
  """
  if to is None:
    parts = []
  elif isinstance(to, str):
    parts = [p.strip() for p in to.split(',')]
  else:
    parts = [str(p).strip() for p in to]
  parts = [p for p in parts if p]
  seen = set()
  addrs = []
  for p in parts:
    if p not in seen:
      seen.add(p)
      addrs.append(p)
  return addrs

def send_email(to, msg, subject, use_prefix=True):
  """
  Sends one email to one or more recipients (single MIME message, multiple RCPT).

  Args:
    to: Single address, comma-separated string, or iterable of addresses.
    msg: Plain-text body.
    subject: Subject line (VenerableWeb prefix applied when use_prefix is True).
  """
  addrs = _normalize_recipients(to)
  if not addrs:
    raise ValueError('send_email: no recipients')

  if use_prefix and '[VenerableWeb]' not in subject:
    subject = '[VenerableWeb] ' + subject

  mime = MIMEText(msg)
  mime['Subject'] = subject
  mime['From'] = 'auto@ruddock.caltech.edu'
  mime['To'] = ', '.join(addrs)

  envelope_from = 'auto@ruddock.caltech.edu'
  s = smtplib.SMTP(_smtp_host(), _smtp_port())
  s.sendmail(envelope_from, addrs, mime.as_string())
  s.quit()
