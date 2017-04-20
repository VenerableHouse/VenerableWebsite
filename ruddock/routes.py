import flask
import sqlalchemy
import io

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

@app.route('/tmp/<img_id>.png')
def img(img_id):
  query = sqlalchemy.text("SELECT img FROM tmp WHERE id=:img_id")
  r = flask.g.db.execute(query, img_id=img_id)
  return flask.send_file(
      io.BytesIO(r.first()['img']),
      attachment_filename=img_id + ".png",
      mimetype="image/png")
