import sqlalchemy
from ruddock import config

engine = sqlalchemy.create_engine(config.DEV.db_uri, convert_unicode=True)

if __name__ == "__main__":
  img = "luna1_black.png"
  with open(img, 'rb') as f:
    img_data = f.read()
  db = engine.connect()
  query = sqlalchemy.text("INSERT INTO tmp (img) VALUES (:img_data)")
  db.execute(query, img_data=img_data)
