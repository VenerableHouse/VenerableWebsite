import flask

from ruddock import app
from ruddock.decorators import login_required

@app.route('/')
def home():
  return flask.render_template('index.html')

@app.route('/info')
@login_required()
def show_info():
  return flask.render_template('info.html')

@app.route('/contact')
def show_contact():
  return flask.render_template('contact.html')
