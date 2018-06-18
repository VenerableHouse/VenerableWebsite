import http.client
import functools
import flask
import inspect

from ruddock import auth_utils

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
          flask.abort(http.client.FORBIDDEN)
      return fn(*args, **kwargs)
    return functools.update_wrapper(wrapped_function, fn)
  return decorator


def get_args_from_form():
  """
  Extracts arguments from flask.request.form and puts them into the wrapped
  function as keyword arguments.
  """
  def decorator(fn):
    def wrapped_function():

      # We might need to change the form keys a bit
      form = flask.request.form
      modified_form = {k.replace('-', '_'): v for k, v in list(form.items())}

      # Get function arguments
      fn_args = inspect.getargspec(fn)[0]
      kwargs = {k: modified_form.get(k, None) for k in fn_args}

      return fn(**kwargs)
    return functools.update_wrapper(wrapped_function, fn)
  return decorator
