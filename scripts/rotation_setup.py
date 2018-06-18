"""
Script to set up the rotation module. Requires
a directory of prefrosh images in last-first.jpg format.
You need to manually replace any hyphenated last names with
another character (I used a space). In the future we should
probably use another character as a delimiter...
You will need to manually add any preferred names, as well as
the dinner values for each prefrosh.

usage: python rotation_setup.py --env ENV /path/to/images/
"""

import argparse
import csv
import os
import sqlalchemy
try:
  from ruddock import config
except ImportError:
  from ruddock import default_config as config
from ruddock.modules.rotation import helpers

parser = argparse.ArgumentParser(
  description="Set up the rotation tables.")

parser.add_argument("--env", default="dev",
  help="Environment to run application in. Can be 'prod', 'dev', or 'test'. "
      + "Default is 'dev'.")
parser.add_argument('imgpath', metavar='imgpath', type=str,
  help="Image path to pull prefrosh images from. Must be an exact copy of the"
       "MEDIA_FOLDER/prefrosh folder.")
parser.add_argument('csvfile', metavar='csvfile', type=str,
  help="CSV file to pull prefrosh information from.")


def main():
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

  # clear out old data
  query = sqlalchemy.text("""
    DELETE FROM rotation_move_history;
    DELETE FROM rotation_prefrosh;
    DELETE FROM rotation_buckets;
  """)
  db.execute(query)

  # initialize the buckets
  for bucket in helpers.BUCKETS:
    query = sqlalchemy.text("""
    INSERT INTO rotation_buckets (bucket_name) VALUES (:b)
    """)
    db.execute(query, b=bucket)

  # grab the bucket_id for the 1 bucket, since this is the default bucket
  # due to our smoothing method
  query = sqlalchemy.text("""
    SELECT bucket_id FROM rotation_buckets WHERE bucket_name = '1'
    """)
  bucket_id = db.execute(query).first()['bucket_id']

  # import the prefrosh from the csv
  with open(args.csvfile, 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    next(reader)  # skip the header row
    for row in reader:
        # DEAR FUTURE READER: when the columns change, just edit this
        last_name = row[0]
        first_name = row[1]
        preferred_name = row[2] if row[2] != "" else None
        dinners = row[3:11]
        dinners = [d.lower() for d in dinners]

        try:
            # Dinners are 1-indexed, but the array is 0-indexed
            ruddock_dinner = dinners.index('ruddock') + 1
        except ValueError:
            ruddock_dinner = ask_for_dinner(first_name, last_name)

        # Add more escaping as necessary
        # TODO if you're feeling fancy, suggest something with low
        # Levenshtein distance
        image_name = "{}-{}.jpg".format(last_name, first_name)
        image_name = image_name.lower().replace(' ', '-')

        if not os.path.isfile(args.imgpath + '/' + image_name):
            image_name = ask_for_image(last_name, first_name, args.imgpath)

        query = sqlalchemy.text("""
          INSERT INTO rotation_prefrosh (first_name, last_name,
            preferred_name, dinner, bucket_id, image_name)
          VALUES (:first, :last, :pref, :dinner, :bid, :img)
        """)

        db.execute(query, first=first_name, last=last_name,
            pref=preferred_name, dinner=ruddock_dinner, bid=bucket_id,
            img=image_name)


def ask_for_dinner(last_name, first_name):
    print(("Could not determine which dinner {} {} is supposed to "
          "attend.".format(first_name, last_name)))
    while True:
        resp = input("Please enter a dinner (1-8): ")
        try:
            dinner = int(resp)
            if dinner < 1 or dinner > 8:
                print("Integer must be between 1 and 8, inclusive.")
            else:
                return dinner
        except ValueError:
            print("Please enter an integer between 1 and 8, inclusive.")


def ask_for_image(last_name, first_name, imgpath):
    print(("Could not determine the name of the image for "
          "{} {}".format(first_name, last_name)))
    while True:
        resp = input("Please enter the image name, or NULL if there is "
                         "no image available: ")
        if resp == "NULL" or os.path.isfile(imgpath + '/' + resp):
            return resp
        else:
            print("That file does not exist; please try again.")

if __name__ == "__main__":
    main()
