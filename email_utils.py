# for email
import smtplib
from email.mime.text import MIMEText

def sendEmail(to, msg, subject='[RuddWeb] A message from the Ruddock Website'):
  msg = MIMEText(msg)
  msg['Subject'] = subject
  msg['From'] = 'auto@ruddock.caltech.edu'
  msg['To'] = to

  s = smtplib.SMTP('localhost')
  s.sendmail('auto@ruddock.caltech.edu', [to], msg.as_string())
  s.quit()
