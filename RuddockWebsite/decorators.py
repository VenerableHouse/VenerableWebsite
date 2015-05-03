import httplib
import functools
import flask

from RuddockWebsite import auth_utils

def login_required(permission=None):
  """
  Login required decorator. Requires user to be logged in. If a permission
  is provided, then user must also have the appropriate permissions to
  access the page.

  Note that this function does not necessarily cover every scenario, so if you
  need something specific that is not implemented here, you may need to handle
  it manually instead of relying on this function.
  """
  def decorator(fn):
    def wrapped_function(*args, **kwargs):
      # User must be logged in.
      if not auth_utils.check_login():
        return auth_utils.login_redirect()
      # Check permissions.
      if permission is not None:
        if not auth_utils.check_permission(permission):
          # Abort with an access forbidden HTTP code.
          flask.abort(httplib.FORBIDDEN)
      return fn(*args, **kwargs)
    return functools.update_wrapper(wrapped_function, fn)
  return decorator
