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
from ruddock import config
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

  # initialize the buckets
  engine = sqlalchemy.create_engine(db_uri, convert_unicode=True)
  db = engine.connect()
  for bucket in helpers.BUCKETS:
    query = sqlalchemy.text("""
    INSERT INTO buckets (bucket_name) VALUES (:b)
    """)
    db.execute(query, b=bucket)

  # import the prefrosh from the image directory
  for filename in os.listdir(args.imgpath):
    full_name = os.path.splitext(filename)
    last, dash, first = full_name[0].partition('-')
    with open('../../images/' + filename, 'rb') as f:
      img_data = f.read()
    query = sqlalchemy.text("""
    INSERT INTO rotation_prefrosh (first_name, last_name, image, bucket_id)
    VALUES (:first, :last, :img_data, 1)
    """)
    db.execute(query, first=first, last=last, img_data=img_data)
