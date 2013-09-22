# for querying the db
from sqlalchemy import create_engine, text
import config
# for updating mailman
from subprocess import check_call
from email_utils import sendEmail

def updateFromList(results, lst):
  print "Updating list: " + lst

  # write emails to flat file
  if len(results) <= 0:
     sendEmail('imss@ruddock.caltech.edu', 'Email list has no subscribers: ' + \
        query + '\n\nFor list: ' + lst, '[RuddWeb] THE EMAIL SCRIPT IS BROKEN')
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
          '\n\nFor list: ' + lst, '[RuddWeb] THE EMAIL SCRIPT IS BROKEN')

# Connect to the mySQL database.
engine = create_engine(config.DB_URI, convert_unicode=True)
connection = engine.connect()

### First update email lists from table 'updating_email_lists' ###
lists_query = text("SELECT listname, query FROM updating_email_lists")
lists = connection.execute(lists_query).fetchall()
# for each list, update!
for (lst, query) in lists:
  # perform query to get emails
  results = connection.execute(query).fetchall()
  updateFromList(results, lst)

### Now, update email lists which correspond to an office ###
lists_query = text("SELECT office_id, office_email FROM offices WHERE office_email IS NOT NULL")
lists = connection.execute(lists_query).fetchall()
# for each list, update!
for (office_id, lst) in lists:
  query = text("SELECT email \
                FROM office_members NATURAL JOIN offices NATURAL JOIN members \
                WHERE office_id = :oid AND elected < NOW() AND IFNULL(expired > NOW(), true)")
  results = connection.execute(query, oid=office_id).fetchall()
  updateFromList(results, lst)
