import flask
import sqlalchemy

from RuddockWebsite import app
from RuddockWebsite import constants
from RuddockWebsite import email_utils
from RuddockWebsite.decorators import login_required

@app.route('/')
def home():
  return flask.render_template('index.html')

@app.route('/government')
def show_gov():
  # Get current officers
  query = sqlalchemy.text("""
    SELECT CONCAT(fname, ' ', lname) AS name, username, office_name,
      office_email, office_id, is_excomm, is_ucc
    FROM office_assignments_current
      NATURAL JOIN office_assignments
      NATURAL JOIN offices
      NATURAL JOIN members
      NATURAL JOIN users
      """)
  results = flask.g.db.execute(query)

  # Organize by type (excomm and ucc are special)
  excomm = []
  ucc = []
  other = []
  for result in results:
    # Organize by type
    if result['is_excomm']:
      excomm.append(result)
    elif result['is_ucc']:
      ucc.append(result)
    else:
      other.append(result)

  ucc.sort(key=lambda x: x['office_name'])
  other.sort(key=lambda x: x['office_name'])

  # Tuple with name, email, and users, so that template can parse efficiently
  all_offices = [
    ('Executive Committee', 'excomm', excomm),
    ('Upperclass Counselors', 'uccs', ucc),
    ('Other Offices', None, other)
  ]
  return flask.render_template('government.html', all_offices = all_offices)

@app.route('/contact')
def show_contact():
  return flask.render_template('contact.html')
