from email_utils import sendEmail
from sqlalchemy import text
from flask import session
SALT_SIZE = 8

def get_user_id(username, db):
  ''' Takes a username and returns the user's ID. '''
  query = text("SELECT user_id FROM users WHERE username = :u")
  result = db.execute(query, u = username).first()

  if result != None:
    return int(result['user_id'])
  return None

def authenticate(user, passwd, db):
  '''
  Takes a username, password, and connection object as input, and checks
  if this corresponds to an actual user. Salts the password as necessary.
  '''
  # get salt and add to password if necessary
  saltQuery = db.execute(text("SELECT salt FROM users WHERE username=:u"),
                         u = user)
  # if there's a salt set, then use it
  if saltQuery.returns_rows:
    salt = saltQuery.first()
    # make sure username is found and salt isn't null
    if salt != None and salt[0] != None:
      passwd = salt[0] + passwd

  # query whether there's a match for the username and password
  query = db.execute(text("SELECT * FROM users WHERE username=:u AND " \
                          + "passwd=MD5(:p)"), u = user, p = passwd)

  row = query.first()
  if (query.returns_rows and row != None):
    return row[0]
  return 0

def passwd_reset(user, newpasswd, db, salt=True, email=None):
  '''
  Resets a user's password with newpasswd. Uses a random salt if salt is
  set to true.
  '''
  if salt:
    from random import choice
    from string import uppercase, digits
    randSalt = ''.join(choice(uppercase + digits) for i in range(SALT_SIZE))
    newpasswd = randSalt + newpasswd

  query = db.execute(text("UPDATE users SET salt=:s, passwd=MD5(:p) WHERE " + \
                          "username=:u"), s = randSalt, p = newpasswd, u = user)

  if (query.rowcount == 1):
    if email:
      # notify user that their password was changed
      try:
        msg = "Your password has been successfully changed.\n" + \
              "If you did not request a password change, please" + \
              " email imss@ruddock.caltech.edu immediately.\n" + \
              "\n\nThanks,\nThe Ruddock Website"
        sendEmail(str(email), msg, "[RuddWeb] Changed Password")
      except Exception as e:
        sendEmail("imss@ruddock.caltech.edu",
                  "Something went wrong when trying to email user " + user + \
                  " after changing their password. You should look into this." + \
                  "\n\nException: " + str(e), "[RuddWeb] EMAIL ERROR")
    return 1
  else:
    return 0

def reset_key(hashed_pw, salt, username):
  if salt == None:
    return hash(username + hashed_pw)
  else:
    return hash(salt + hashed_pw)

def get_permissions(username, db):
  '''
  Takes a username and database connection as input. Returns a list with
  all of the permissions available to the user. A list is returned because
  Python sets cannot be stored in cookie data.
  '''

  query = text("""
    (SELECT permission
      FROM users
        NATURAL JOIN offices
        NATURAL JOIN office_members_current
        NATURAL JOIN office_permissions
      WHERE username=:u)
    UNION
    (SELECT permission
      FROM users
        NATURAL JOIN user_permissions
      WHERE username=:u)
    """)
  result = db.execute(query, u=username)
  permissions = [row['permission'] for row in result]
  return permissions

def check_permission(permission):
  if 'permissions' in session:
    return permission in session['permissions']
  return False

def update_last_login(username, db):
  '''
  Takes a username and database connection as input. Updates the last
  login time for the user.
  '''

  query = text("UPDATE users SET lastlogin=NOW() WHERE username=:u")
  db.execute(query, u=username)
