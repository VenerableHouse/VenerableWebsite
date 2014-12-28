from functools import update_wrapper
from flask import session, redirect, flash
import auth

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
        return redirect(url_for('login'))

      # Check permissions.
      if permission != None:
        if not auth.check_permission(permission):
          flash("You do not have permission to access this page.")
          session['next'] = request.url
          return redirect(url_for('login'))
      return fn(*args, **kwargs)
    return update_wrapper(wrapped_function, fn)
  return decorator


