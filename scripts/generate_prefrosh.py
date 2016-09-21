import sqlalchemy
import os
from ruddock import config

engine = sqlalchemy.create_engine(config.DEV.db_uri, convert_unicode=True)

if __name__ == "__main__":
  for filename in os.listdir('../../images/'):
      full_name = os.path.splitext(filename)
      last, dash, first = full_name[0].partition('-')
      with open('../../images/' + filename, 'rb') as f:
          img_data = f.read()
      db = engine.connect()
      query = sqlalchemy.text("""
        INSERT INTO rotation_prefrosh (first_name, last_name, image)
        VALUES (:first, :last, :img_data)
      """)
      db.execute(query, first=first, last=last, img_data=img_data)
