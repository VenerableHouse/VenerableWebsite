# for email
import smtplib
from email.mime.text import MIMEText

def sendEmail(to, msg, subject='A message from the Ruddock Website', \
    usePrefix=True):
  """ Sends an email to a user. """
  msg = MIMEText(msg)

  if usePrefix and '[RuddWeb]' not in subject:
    subject = '[RuddWeb] ' + subject

  msg['Subject'] = subject
  msg['From'] = 'auto@ruddock.caltech.edu'
  msg['To'] = to

  s = smtplib.SMTP('localhost')
  s.sendmail('auto@ruddock.caltech.edu', [to], msg.as_string())
  s.quit()
