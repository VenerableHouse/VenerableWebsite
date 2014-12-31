from flask import g, session
from sqlalchemy import text
from collections import OrderedDict

from RuddockWebsite.constants import *
from RuddockWebsite import auth

def get_user_info(username):
  """ Procedure to get a user's info from the database. """
  cols = [["username"], ["fname", "lname"], ["nickname"], ["bday"], \
          ["email"], ["email2"], ["status"], ["matriculate_year"], \
          ["grad_year"], ["msc"], ["phone"], ["building", "room_num"], \
          ["membership_desc"], ["major"], ["uid"], ["isabroad"]]
  display = ["Username", "Name", "Nickname", "Birthday", "Primary Email", \
             "Secondary Email", "Status", "Matriculation Year", \
             "Graduation Year", "MSC", "Phone Number", "Residence", \
             "Membership", "Major", "UID", "Is Abroad"]
  # Defines the order and mapping of displayed attributes to sql columns
  d_dict = OrderedDict(zip(display, cols))
  query = text("SELECT * FROM users NATURAL JOIN members NATURAL JOIN membership_types WHERE username=:u")
  result = g.db.execute(query, u=str(username))

  values = result.first()
  if not values:
    d_dict = None
    values = None
  else:
    if not values['usenickname']:
      d_dict.pop('Nickname')
  return (d_dict, values)

def get_office_info(username):
  """ Procedure to get a user's officer info. """
  cols = ["office_name", "elected", "expired"]
  query = text("""
    SELECT office_name, elected, expired
    FROM office_members NATURAL JOIN users NATURAL JOIN offices
    WHERE username = :u
    ORDER BY elected, expired, office_name
  """)
  return g.db.execute(query, u=str(username))

def can_edit(username):
  """ Returns true if user has permission to edit page. """
  if 'username' not in session:
    return False
  return session['username'] == username or \
      auth.check_permission(Permissions.UserAdmin)


