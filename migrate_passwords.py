''' Python script to migrate database password hashing algorithms. '''

from sqlalchemy import create_engine, text
from RuddockWebsite import config
from RuddockWebsite import auth
from RuddockWebsite import constants as const
import time

if __name__ == '__main__':
  start_time = time.clock()

  # Connect to the database.
  engine = create_engine(config.DB_URI, convert_unicode=True)
  db = engine.connect()

  # Use transactions.
  trans = db.begin()
  try:
    # Get all user's password hashes and salts.
    query = text("SELECT username, password_hash, salt FROM users")
    result = db.execute(query)

    for row in result:
      # Migrate each user's password hash.
      username = row['username']
      md5_hash = row['password_hash']
      md5_salt = row['salt'] if row['salt'] is not None else ''

      # Generate a new salt and compute a new hash.
      salt = auth.generate_salt()
      password_hash = auth.hash_password(md5_hash, salt, const.HASH_ROUNDS,
          const.PWD_HASH_ALGORITHM)

      # Get full hash string.
      algorithms = ['md5', const.PWD_HASH_ALGORITHM]
      rounds = [None, const.HASH_ROUNDS]
      salts = [md5_salt, salt]
      parser = auth.PasswordHashParser(algorithms, rounds, salts, password_hash)
      full_hash = str(parser)

      # Insert into database
      query = text("""
        UPDATE users
        SET password_hash = :ph, salt = NULL
        WHERE username = :u
        """)
      db.execute(query, ph=full_hash, u=username)

      print "Updated hash for user: {}".format(username)
    trans.commit()
  except Exception:
    trans.rollback()
    raise
  print "Done!"

  end_time = time.clock()
  print "Time used: {} seconds".format(end_time - start_time)
