import flask
import sqlalchemy
from ruddock.resources import Permissions

def fetch_office_permissions():
  """Returns the office name and permissions of all active offices.
     Returns the permissions of all offices that have permissions,
     plus the permissions of all active offices (which may be none)."""
  query = sqlalchemy.text("""
    SELECT GROUP_CONCAT(permission_id) AS permissions, 
           office_name, office_id, office_order
    FROM office_permissions
      NATURAL RIGHT JOIN offices
      WHERE is_active=TRUE
    GROUP BY office_id

    UNION

    SELECT GROUP_CONCAT(permission_id) AS permissions, 
           office_name, office_id, office_order
    FROM office_permissions
      NATURAL JOIN offices
    GROUP BY office_id

    ORDER BY
    CASE
      WHEN permissions IS NULL
      THEN 1
      ELSE 0
    END,
    permissions ASC,
    office_order ASC
  """)

  return flask.g.db.execute(query).fetchall()

def fetch_user_permissions():
  """Returns the user's name and permissions of all users.
     Returns the permissions of all users who have permissions,
     and the permissions of all current members (which may be none)"""
  query = sqlalchemy.text("""
    SELECT GROUP_CONCAT(permission_id) AS permissions, name, user_id
    FROM user_permissions 
      NATURAL RIGHT JOIN members_current 
      NATURAL JOIN members_extra 
    GROUP BY user_id

    UNION 

    SELECT GROUP_CONCAT(permission_id) AS permissions, name, user_id
    FROM user_permissions 
      NATURAL JOIN members_extra 
    GROUP BY user_id

    ORDER BY
    CASE
      WHEN permissions IS NULL
      THEN 1
      ELSE 0
    END,
    permissions ASC,
    name ASC
  """)

  return flask.g.db.execute(query).fetchall()

def decode_perm_string(string, sep=","):
  "Decodes a `sep`-separated string of permissions."
  if string is None:
    return ["None"]
  elif type(string) is int:
    return get_perm_name(string)
  elif type(string) is not str:
    raise TypeError("decode_perm_string takes int or str only, received "
                    + str(type(string)))
  return [get_perm_name(int(x)) for x in string.split(sep)]

def get_perm_name(id):
  """Returns the permission name corresponding to the given ID."""
  if id is None:
    return "None"
  perm_name = "";
  try:
    perm_name = Permissions(id).name.title().replace("_", " ")
  except ValueError:
    # id is not a valid permission
    perm_name = "Invalid permission"
  return perm_name
