from flask import Flask, g
from sqlalchemy import create_engine
from RuddockWebsite.constants import *
from RuddockWebsite.config import *

from RuddockWebsite.modules.users import blueprint as users_blueprint
from RuddockWebsite.modules.hassle import blueprint as hassle_blueprint
from RuddockWebsite.modules.admin import blueprint as admin_blueprint

app = Flask(__name__)
app.debug = False
app.secret_key = config.SECRET_KEY

# Maximum file upload size, in bytes.
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Load blueprint modules
app.register_blueprint(users_blueprint, url_prefix='/users')
app.register_blueprint(hassle_blueprint, url_prefix='/hassle')
app.register_blueprint(admin_blueprint, url_prefix='/admin')

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
  if g.db != None:
    g.db.close()

from RuddockWebsite import routes
