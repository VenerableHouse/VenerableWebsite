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

def fetch_specific_office_permissions(office_id):
  """Returns the office name and permissions of the specified office.
     May be none."""
  if type(office_id) is not int:
      raise TypeError("Must pass office id number to fetch office permissions.")
  query = sqlalchemy.text("""
    SELECT GROUP_CONCAT(permission_id) AS permissions, 
           office_name, office_id
    FROM office_permissions
      NATURAL RIGHT JOIN offices
    WHERE office_id = :id
    GROUP BY office_id
  """)
  return flask.g.db.execute(query, id=office_id).fetchone()

def delete_office_permission(office_id, perm_id):
    """Deletes the specified permission from the office."""
    if type(perm_id) is str or type(perm_id) is unicode:
        perm_id = int(perm_id)
    if type(office_id) is not int or type(perm_id) is not int:
        raise TypeError("Must pass office id number and permission id to fetch office permissions.")
    query = sqlalchemy.text("""
        DELETE FROM office_permissions
        WHERE office_id = :o_id
        AND permission_id = :p_id
    """)
    return flask.g.db.execute(query, o_id=office_id, p_id=perm_id)

def insert_office_permission(office_id, perm_id):
    """Inserts the specified permission for the office."""
    if type(perm_id) is str or type(perm_id) is unicode:
        perm_id = int(perm_id)
    if type(office_id) is not int or type(perm_id) is not int:
        raise TypeError("Must pass office id number and permission id to fetch office permissions.")
    query = sqlalchemy.text("""
        INSERT INTO office_permissions VALUES (:o_id, :p_id)
    """)
    return flask.g.db.execute(query, o_id=office_id, p_id=perm_id)


def fetch_user_permissions():
  """Returns the user's name and permissions of all users.
     Returns the permissions of all users who have permissions,
     and the permissions of all current members (which may be none)"""
  query = sqlalchemy.text("""
    SELECT GROUP_CONCAT(permission_id) AS permissions, name, user_id
    FROM user_permissions 
      NATURAL RIGHT JOIN members_current 
      NATURAL JOIN users
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

def fetch_specific_user_permissions(user_id):
  """Returns the name and permissions of the specified user.
     May be none."""
  if type(user_id) is not int:
      raise TypeError("Must pass user id number to fetch user permissions.")
  query = sqlalchemy.text("""
    SELECT GROUP_CONCAT(permission_id) AS permissions, name, user_id
    FROM user_permissions 
      NATURAL RIGHT JOIN users 
        NATURAL JOIN members_extra 
    WHERE user_id = :id
    GROUP BY user_id
  """)
  return flask.g.db.execute(query, id=user_id).fetchone()

def delete_user_permission(user_id, perm_id):
    """Deletes the specified permission from the user."""
    if type(perm_id) is str or type(perm_id) is unicode:
        perm_id = int(perm_id)
    if type(user_id) is not int or type(perm_id) is not int:
        raise TypeError("Must pass user id number and permission id to fetch user permissions.")
    query = sqlalchemy.text("""
        DELETE FROM user_permissions
        WHERE user_id = :o_id
        AND permission_id = :p_id
    """)
    return flask.g.db.execute(query, o_id=user_id, p_id=perm_id)

def insert_user_permission(user_id, perm_id):
    """Inserts the specified permission for the user."""
    if type(perm_id) is str or type(perm_id) is unicode:
        perm_id = int(perm_id)
    if type(user_id) is not int or type(perm_id) is not int:
        raise TypeError("Must pass user id number and permission id to fetch user permissions.")
    query = sqlalchemy.text("""
        INSERT INTO user_permissions VALUES (:o_id, :p_id)
    """)
    return flask.g.db.execute(query, o_id=user_id, p_id=perm_id)

def decode_perm_string(string, sep=","):
  """Decodes a `sep`-separated string of permissions."""
  if string is None:
    return ["None"]
  elif type(string) is int:
    return get_perm_name(string)
  elif type(string) is not str:
    raise TypeError("decode_perm_string takes int or str only, received "
                    + str(type(string)))
  return [get_perm_name(int(x)) for x in string.split(sep)]

def decode_perm_string_with_id(string, sep=","):
  """Decodes a `sep`-separated string of permissions into a dictionary
   of ID and name."""
  if string is None:
      return [{"name": "None", "id": 0}]
  elif type(string) is int:
      return {"name": get_perm_name(string), "id": string}
  elif type(string) is not str:
    raise TypeError("decode_perm_string takes int or str only, received "
                    + str(type(string)))
  return [{"name": get_perm_name(int(x)), "id": x} for x in string.split(sep)]

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

def get_all_perms():
    """Gets a list of all permissions possible to assign."""
    x = []
    for p in Permissions:
        x.append({"name": get_perm_name(p.value), "id": str(p.value)})
    return x
