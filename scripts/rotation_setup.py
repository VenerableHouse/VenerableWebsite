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

import sqlalchemy
import os
import argparse
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
  help="Image path to pull prefrosh images from.")


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

  # grab the bucket_id for the 000 bucket, since this is the default bucket
  query = sqlalchemy.text("""
    SELECT bucket_id FROM rotation_buckets WHERE bucket_name = '000'
    """)
  bucket_id = db.execute(query).first()['bucket_id']

  # import the prefrosh from the image directory
  for filename in os.listdir(args.imgpath):
    full_name = os.path.splitext(filename)
    last, dash, first = full_name[0].partition('-')
    with open(args.imgpath + filename, 'rb') as f:
      img_data = f.read()
    query = sqlalchemy.text("""
    INSERT INTO rotation_prefrosh (first_name, last_name, image, bucket_id)
    VALUES (:first, :last, :img_data, :bid)
    """)
    db.execute(query, first=first, last=last, img_data=img_data, bid=bucket_id)
