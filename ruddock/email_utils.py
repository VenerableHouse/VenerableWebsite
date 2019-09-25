import smtplib
from email.mime.text import MIMEText

def send_email(to, msg, subject, use_prefix=True):
  """
  Sends an email to a user. Expects 'to' to be a comma separated string of
  emails, and for 'msg' and 'subject' to be strings.
  """
  msg = MIMEText(msg)

  if use_prefix and '[RuddWeb]' not in subject:
    subject = '[RuddWeb] ' + subject

  msg['Subject'] = subject
  msg['From'] = 'auto@ruddock.caltech.edu'
  msg['To'] = to

  from ruddock import app
  if app.config["TESTING"]:
    print("In test mode, will not send email: {}".format(msg.as_string()))
    return

  s = smtplib.SMTP('localhost')
  s.sendmail('auto@ruddock.caltech.edu', [to], msg.as_string())
  s.quit()
