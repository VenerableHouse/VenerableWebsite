import flask

from RuddockWebsite import app

@app.route('/')
def home():
  return flask.render_template('index.html')

@app.route('/contact')
def show_contact():
  return flask.render_template('contact.html')
