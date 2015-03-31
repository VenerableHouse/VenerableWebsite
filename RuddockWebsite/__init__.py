import traceback
from datetime import datetime
from flask import Flask, g, url_for, render_template, redirect
from sqlalchemy import create_engine

from RuddockWebsite import config, constants, email_templates, email_utils
from RuddockWebsite.modules import account, admin, auth, hassle, users

app = Flask(__name__)
app.debug = False
app.secret_key = config.SECRET_KEY

# Maximum file upload size, in bytes.
app.config['MAX_CONTENT_LENGTH'] = constants.MAX_CONTENT_LENGTH

# Update jinja global functions
app.jinja_env.globals.update(current_year=lambda: datetime.now().year)

# Load blueprint modules
app.register_blueprint(account.blueprint, url_prefix='/account')
app.register_blueprint(admin.blueprint, url_prefix='/admin')
# Auth blueprint has no prefix, since not all endpoints have the same prefix.
app.register_blueprint(auth.blueprint)
app.register_blueprint(hassle.blueprint, url_prefix='/hassle')
app.register_blueprint(users.blueprint, url_prefix='/users')

# Create database engine object.
engine = create_engine(config.DB_URI, convert_unicode=True)

@app.before_request
def before_request():
  ''' Logic executed before request is processed. '''
  # Connect to the database and publish it in flask.g
  g.db = engine.connect()

@app.teardown_request
def teardown_request(exception):
  ''' Logic executed after every request is finished. '''
  # Close database connection.
  db = getattr(g, 'db', None)
  if db is not None:
    db.close()

# Error handlers
@app.errorhandler(404)
def page_not_found(error):
  ''' Handles a 404 page not found error. '''
  return render_template("404.html"), 404

@app.errorhandler(403)
def access_forbidden(error):
  ''' Handles a 403 access forbidden error. '''
  return render_template("403.html"), 403

@app.errorhandler(500)
def internal_server_error(error):
  '''
  Handles a 500 internal server error response. This error is usually the
  result of an improperly configured server or bugs in the actual codebase
  (user errors should be handled gracefully), so IMSS must be notified if this
  error occurs.
  '''
  msg = email_templates.ErrorCaughtEmail.format(traceback.format_exc())
  subject = "Ruddock website error"
  to = "imss@ruddock.caltech.edu"
  email_utils.sendEmail(to, msg, subject)
  return render_template("500.html"), 500

# After initialization, import the routes.
from RuddockWebsite import routes
