from sqlalchemy import text
from flask import session, g

from RuddockWebsite import email_utils

SALT_SIZE = 8

def get_user_id(username):
  ''' Takes a username and returns the user's ID. '''
  query = text("SELECT user_id FROM users WHERE username = :u")
  result = g.db.execute(query, u = username).first()

  if result != None:
    return int(result['user_id'])
  return None

def authenticate(user, passwd):
  '''
  Takes a username and password and checks if this corresponds to
  an actual user. Salts the password as necessary.
  '''
  # get salt and add to password if necessary
  saltQuery = g.db.execute(text("SELECT salt FROM users WHERE username=:u"),
      u = user)
  # if there's a salt set, then use it
  if saltQuery.returns_rows:
    salt = saltQuery.first()
    # make sure username is found and salt isn't null
    if salt != None and salt[0] != None:
      passwd = salt[0] + passwd

  # query whether there's a match for the username and password
  query = g.db.execute(text("SELECT * FROM users WHERE username=:u AND " + \
      "passwd=MD5(:p)"), u = user, p = passwd)

  row = query.first()
  if (query.returns_rows and row != None):
    return row[0]
  return 0

def passwd_reset(user, newpasswd, salt=True, email=None):
  '''
  Resets a user's password with newpasswd. Uses a random salt if salt is
  set to true.
  '''
  if salt:
    from random import choice
    from string import uppercase, digits
    randSalt = ''.join(choice(uppercase + digits) for i in range(SALT_SIZE))
    newpasswd = randSalt + newpasswd

  query = text("UPDATE users SET salt=:s, passwd=MD5(:p) WHERE username=:u")
  result = g.db.execute(query, s=randSalt, p=newpasswd, u=user)

  if result.rowcount > 0:
    if email:
      # notify user that their password was changed
      try:
        msg = "Your password has been successfully changed.\n" + \
              "If you did not request a password change, please" + \
              " email imss@ruddock.caltech.edu immediately.\n" + \
              "\n\nThanks,\nThe Ruddock Website"
        email_utils.sendEmail(str(email), msg, "[RuddWeb] Changed Password")
      except Exception as e:
        email_utils.sendEmail("imss@ruddock.caltech.edu",
                  "Something went wrong when trying to email user " + user + \
                  " after changing their password. You should look into this." + \
                  "\n\nException: " + str(e), "[RuddWeb] EMAIL ERROR")
    return True
  else:
    return False

def reset_key(hashed_pw, salt, username):
  if salt == None:
    return hash(username + hashed_pw)
  else:
    return hash(salt + hashed_pw)

def get_permissions(username):
  '''
  Returns a list with all of the permissions available to the user.
  A list is returned because Python sets cannot be stored in cookie data.
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
  result = g.db.execute(query, u=username)
  return [row['permission'] for row in result]

def check_permission(permission):
  ''' Returns true if the user has the input permission. '''
  if 'permissions' in session:
    return permission in session['permissions']
  return False

def update_last_login(username):
  ''' Updates the last login time for the user. '''

  query = text("UPDATE users SET lastlogin=NOW() WHERE username=:u")
  g.db.execute(query, u=username)
