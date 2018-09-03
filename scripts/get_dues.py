"""
This script pulls dues information from the database.
It will output a CSV file of UIDs, names, and membership type of each
dues-paying member, and email it to the treasurer.

They'll need to go through by hand and extract people who are married
(yes, that's in our constitution!) and RAs.

usage: python get_dues.py --env ENV
"""

import sqlalchemy
import csv
import argparse
import tempfile
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
  from ruddock import config
except ImportError:
  from ruddock import default_config as config

CSV_FILE = 'dues.csv'
TO_EMAIL = 'treasurer@ruddock.caltech.edu'
FROM_EMAIL = 'auto@ruddock.caltech.edu'

parser = argparse.ArgumentParser(
  description="Pull dues information.")

parser.add_argument("--env", default="dev",
  help="Environment to run application in. Can be 'prod', 'dev', or 'test'. "
      + "Default is 'dev'.")

if __name__ == "__main__":
  args = parser.parse_args()
  if args.env == "prod" and hasattr(config, "PROD"):
    db_uri = config.PROD.db_uri
  elif args.env == "dev" and hasattr(config, "DEV"):
    db_uri = config.DEV.db_uri
  elif args.env == "test" and hasattr(config, "TEST"):
    db_uri = config.TEST.db_uri
  else:
    raise ValueError("Illegal environment name.")

  engine = sqlalchemy.create_engine(db_uri, convert_unicode=True)
  db = engine.connect()


  # Pull the data!
  query = sqlalchemy.text("""
    SELECT uid, last_name, first_name, membership_desc
    FROM members_current
      NATURAL JOIN members
      NATURAL JOIN membership_types
    ORDER BY membership_desc, last_name
  """)
  db.execute(query)
  records = db.execute(query).fetchall()

  # Write it out to CSV
  with open(CSV_FILE, 'w') as outfile:
    outcsv = csv.writer(outfile)
    column_names = ["uid", "last_name", "first_name", "membership_desc"]
    for row in records:
      outcsv.writerow([row[x] for x in column_names])

    print("Successfully output dues to {}".format(CSV_FILE))

  with open(CSV_FILE, 'r') as infile:
    msg = MIMEMultipart()

    msg['Subject'] = 'Dues List'
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL

    attachment = MIMEText(infile.read(), _subtype="csv")
    attachment.add_header('Content-Disposition', 'attachment', filename="dues.csv")

    msg.attach(attachment)

    smtp = smtplib.SMTP('localhost')
    smtp.set_debuglevel(1)
    smtp.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
    smtp.close()

    print("Successfully emailed the treasurer!")
