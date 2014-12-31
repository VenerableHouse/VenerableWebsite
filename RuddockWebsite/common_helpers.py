from flask import redirect, url_for, flash

def fetch_all_results(query_result):
  '''
  Takes the result from a database query and organizes results. The output
  format is a list of dictionaries, where the dict keys are the columns
  returned.
  '''
  result = []
  result_keys = query_result.keys()

  for row in query_result:
    row_dict = dict(zip(result_keys, row))
    result.append(row_dict)

  return result

def display_error_msg(msg=False, redirect_location=None):
  if not msg:
    msg = "Invalid request. If you think you have received this message in \
        error, please find an IMSS rep immediately."

  if not redirect_location:
    redirect_location = "home"

  flash(msg)
  return redirect(url_for(redirect_location))

# TODO: This is used in admin pages and user creation, so need to find a
# better place to put it.
def create_account_hash(user_id, uid, fname, lname):
  '''
  Creates a unique hash for users trying to create an account.
  '''
  return hash(str(user_id) + str(uid) + str(fname) + str(lname))


