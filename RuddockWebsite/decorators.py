from functools import update_wrapper
from flask import session, redirect, flash, request, url_for, abort

from RuddockWebsite import auth_utils

def login_required(permission=None):
  '''
  Login required decorator. Requires user to be logged in. If a permission
  is provided, then user must also have the appropriate permissions to
  access the page.
  '''
  def decorator(fn):
    def wrapped_function(*args, **kwargs):
      # User must be logged in.
      if 'username' not in session:
        flash("This page requires you to be logged in.")
        # Store page to be loaded after login in session.
        session['next'] = request.url
        return redirect(url_for('auth.login'))

      # Check permissions.
      if permission is not None:
        if not auth_utils.check_permission(permission):
          # Abort with an access forbidden HTTP code.
          abort(403)
      return fn(*args, **kwargs)
    return update_wrapper(wrapped_function, fn)
  return decorator
