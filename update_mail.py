# for querying the db
from sqlalchemy import create_engine, text
import config
# for updating mailman
from subprocess import check_call
# for email
import smtplib
from email.mime.text import MIMEText

def sendEmail(to, msg, subject='[RuddWeb] THE EMAIL SCRIPT IS BROKEN'):
  msg = MIMEText(msg)
  msg['Subject'] = subject
  msg['From'] = 'auto@ruddock.caltech.edu'
  msg['To'] = to

  s = smtplib.SMTP('localhost')
  s.sendmail('auto@ruddock.caltech.edu', [to], msg.as_string())
  s.quit()


""" Connect to the mySQL database. """
engine = create_engine(config.DB_URI, convert_unicode=True)
connection = engine.connect()

# get the email lists that we should update
lists_query = text("SELECT listname, query FROM updating_email_lists")
lists = connection.execute(lists_query).fetchall()

# for each list, update!
for (lst, query) in lists:
  # perform query to get emails
  results = connection.execute(query).fetchall()

  print "Updating list: " + lst

  # write emails to flat file
  if len(results) <= 0:
     sendEmail('imss@ruddock.caltech.edu', 'Query yielded no results: ' + \
        query + '\n\nFor list: ' + lst)
     exit(0)
  else:
    try:
      f = open('temp_emails.txt', 'w')
      for result in results:
        f.write(result[0] + '\n')
      f.close()

      # update mailman list
      check_call("/usr/lib/mailman/bin/sync_members -w=no -g=no -a=yes -f " + \
          "'/home/epelz/RuddockWebsite/temp_emails.txt' " + lst, shell=True)
    except Exception as e:
      sendEmail('imss@ruddock.caltech.edu', 'Exception: ' + str(e) + \
          '\n\nQuery: ' + query + '\n\nFor list: ' + lst)
