def authenticate(user, passwd, db):
  """ Takes a username, password, and connection object as input, and checks
  if this corresponds to an actual user. Salts the password as necessary. """
  # get salt and add to password if necessary
  saltQuery = db.execute("SELECT salt FROM users WHERE username='" + user \
          + "'")
  # if there's a salt set, then use it
  if saltQuery.returns_rows:
    salt = saltQuery.first()
    # make sure username is found and salt isn't null
    if salt != None and salt[0] != None:
      passwd = salt[0] + passwd

  # query whether there's a match for the username and password
  query = db.execute("SELECT * FROM users WHERE username='" + user + "' AND " \
          + "passwd=MD5('" + passwd + "')")

  return query.returns_rows and query.first() != None
