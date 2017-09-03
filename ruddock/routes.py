import flask

from ruddock import app
from ruddock.decorators import login_required

@app.route('/')
def home():
  """The homepage of the site."""
  return flask.render_template('index.html')

@app.route('/info')
@login_required()
def show_info():
  """Shows info page on door combos, printers, etc."""
  return flask.render_template('info.html')

@app.route('/contact')
def show_contact():
  """Shows Contact Us page."""
  return flask.render_template('contact.html')
