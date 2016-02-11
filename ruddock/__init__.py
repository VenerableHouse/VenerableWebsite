"""The Ruddock Website."""

import datetime
import flask
import httplib
import sqlalchemy
import traceback

try:
  from ruddock import config
except ImportError:
  from ruddock import default_config as config
from ruddock import constants
from ruddock import email_templates
from ruddock import email_utils
from ruddock.modules import account
from ruddock.modules import admin
from ruddock.modules import auth
from ruddock.modules import government
from ruddock.modules import hassle
from ruddock.modules import users

app = flask.Flask("ruddock")

# Load blueprint modules
app.register_blueprint(account.blueprint, url_prefix="/account")
app.register_blueprint(admin.blueprint, url_prefix="/admin")
# Auth blueprint has no prefix, since not all endpoints have the same prefix.
app.register_blueprint(auth.blueprint)
app.register_blueprint(government.blueprint, url_prefix="/government")
app.register_blueprint(hassle.blueprint, url_prefix="/hassle")
app.register_blueprint(users.blueprint, url_prefix="/users")

# After initialization, import the routes.
from ruddock import routes

def init(environment_name):
  """Initializes the application with configuration variables and routes.

  This function MUST be called before the server can be run.

  Args:
    environment_name: this must be either "prod", "dev", or "test".

  Returns:
    None
  """
  if environment_name == "prod" and hasattr(config, "PROD"):
    environment = config.PROD
  elif environment_name == "dev" and hasattr(config, "DEV"):
    environment = config.DEV
  elif environment_name == "test" and hasattr(config, "TEST"):
    environment = config.TEST
  else:
    raise ValueError("Illegal environment name.")

  # Initialize configuration variables.
  app.config["DB_URI"] = environment.db_uri
  app.config["DEBUG"] = environment.debug
  app.config["SECRET_KEY"] = environment.secret_key

  # Maximum file upload size, in bytes.
  app.config["MAX_CONTENT_LENGTH"] = constants.MAX_CONTENT_LENGTH

  # Update jinja global functions
  app.jinja_env.globals.update(
      current_year=lambda: datetime.datetime.now().year)

@app.before_request
def before_request():
  """Logic executed before request is processed."""
  # Create database engine object.
  engine = sqlalchemy.create_engine(app.config["DB_URI"], convert_unicode=True)
  # Connect to the database and publish it in flask.g
  flask.g.db = engine.connect()

@app.teardown_request
def teardown_request(exception):
  """Logic executed after every request is finished."""
  # Close database connection.
  db = getattr(flask.g, "db", None)
  if db is not None:
    db.close()

# Error handlers
@app.errorhandler(httplib.NOT_FOUND)
def page_not_found(error):
  """Handles a 404 page not found error."""
  return flask.render_template("404.html"), httplib.NOT_FOUND

@app.errorhandler(httplib.FORBIDDEN)
def access_forbidden(error):
  """Handles a 403 access forbidden error."""
  return flask.render_template("403.html"), httplib.FORBIDDEN

@app.errorhandler(httplib.INTERNAL_SERVER_ERROR)
def internal_server_error(error):
  """
  Handles a 500 internal server error response. This error is usually the
  result of an improperly configured server or bugs in the actual codebase
  (user errors should be handled gracefully), so IMSS must be notified if this
  error occurs.
  """
  msg = email_templates.ErrorCaughtEmail.format(traceback.format_exc())
  subject = "Ruddock website error"
  to = "imss@ruddock.caltech.edu"
  email_utils.send_email(to, msg, subject)
  return flask.render_template("500.html"), httplib.INTERNAL_SERVER_ERROR

