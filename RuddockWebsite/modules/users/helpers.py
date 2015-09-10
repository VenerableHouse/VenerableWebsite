import flask
import sqlalchemy
from collections import OrderedDict

from RuddockWebsite import auth_utils
from RuddockWebsite.resources import Permissions

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
  query = sqlalchemy.text("""
    SELECT * FROM users
      NATURAL JOIN members
      NATURAL JOIN membership_types
    WHERE username=:u
    """)
  result = flask.g.db.execute(query, u=username)

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
  cols = ["office_name", "start_date", "end_date"]
  query = sqlalchemy.text("""
    SELECT office_name, start_date, end_date
    FROM office_assignments NATURAL JOIN users NATURAL JOIN offices
    WHERE username = :u
    ORDER BY start_date, end_date, office_name
  """)
  return flask.g.db.execute(query, u=username)

def check_edit_permission(username):
  """ Returns true if user has permission to edit page. """
  if not auth_utils.check_login():
    return False
  return flask.session['username'] == username \
      or auth_utils.check_permission(Permissions.USERS)
