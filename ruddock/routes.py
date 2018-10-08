import flask

from ruddock import app
from ruddock.auth_utils import is_full_member
from ruddock.decorators import login_required
try:
  from ruddock import secrets
except ImportError:
  from ruddock import default_secrets as secrets

@app.route('/')
def home():
  """The homepage of the site."""
  return flask.render_template('index.html')

@app.route('/info')
@login_required()
def show_info():
  """Shows info page on door combos, printers, etc."""
  return flask.render_template('info.html',
    full_member=is_full_member(flask.session['username']),
    secrets=secrets)

@app.route('/contact')
def show_contact():
  """Shows Contact Us page."""
  return flask.render_template('contact.html')
