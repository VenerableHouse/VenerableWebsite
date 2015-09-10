def login(session):
  """
  Simulates a login by manually adding values to the session variable provided.
  Example usage:

  with client.session_transaction() as session:
    login(session)

  You can now send requests as if you were logged in.
  """
  session['username'] = 'test_user'
  session['permissions'] = []
  return

def add_permission(session, permission):
  """
  Adds a permission to the session variable provided.
  """
  session['permissions'].append(int(permission))
  return
