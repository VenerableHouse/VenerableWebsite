# for querying the db
from sqlalchemy import create_engine, text
import config
# for updating mailman
from subprocess import check_call
from email_utils import sendEmail
import tempfile

def updateFromList(results, lst):
  print "Updating list: " + lst

  # write emails to flat file
  if len(results) <= 0:
     sendEmail('imss@ruddock.caltech.edu', 'Email list has no subscribers: ' + \
        query + '\n\nFor list: ' + lst, '[RuddWeb] THE EMAIL SCRIPT IS BROKEN')
  else:
    try:
      f = tempfile.NamedTemporaryFile()
      for result in results:
        f.write(result[0] + '\n')
      for addition in getAdditionalEmails(lst):
        f.write(addition[0] + '\n')
      f.flush() # flush so file can be read by `sync_members`

      # update mailman list
      check_call("/usr/lib/mailman/bin/sync_members -w=no -g=no -a=yes -f " + \
          "'" + f.name + "' " + lst, shell=True)

      f.close() # this also deletes the tempfile
    except Exception as e:
      sendEmail('imss@ruddock.caltech.edu', 'Exception: ' + str(e) + \
          '\n\nFor list: ' + lst, '[RuddWeb] THE EMAIL SCRIPT IS BROKEN')

def getAdditionalEmails(lst):
  #print "Getting additional emails for list: " + lst
  query = text("SELECT email FROM updating_email_lists_additions WHERE listname=:lst")
  emails = connection.execute(query, lst=lst).fetchall()
  return emails

# Connect to the mySQL database.
engine = create_engine(config.DB_URI, convert_unicode=True)
connection = engine.connect()

### First update email lists from table 'updating_email_lists' ###
lists_query = text("SELECT listname, query FROM updating_email_lists")
lists = connection.execute(lists_query).fetchall()
# for each list, update!
for (lst, query) in lists:
  # perform query to get emails
  results = connection.execute(text(query)).fetchall()
  updateFromList(results, lst)

### Now, update email lists which correspond to an office ###
lists_query = text("SELECT office_id, office_email FROM offices WHERE office_email IS NOT NULL")
lists = connection.execute(lists_query).fetchall()
# for each list, update!
for (office_id, lst) in lists:
  query = text("SELECT email \
                FROM office_members_current NATURAL JOIN offices NATURAL JOIN members_current \
                WHERE office_id = :oid")
  results = connection.execute(query, oid=office_id).fetchall()
  updateFromList(results, lst)
