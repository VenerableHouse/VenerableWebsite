import flask
import sqlalchemy

from RuddockWebsite import app
from RuddockWebsite import constants
from RuddockWebsite import email_utils
from RuddockWebsite import office_utils
from RuddockWebsite.decorators import login_required

@app.route('/')
def home():
  return flask.render_template('index.html')

@app.route('/government')
def show_gov():
  # Get current assignments
  assignments = office_utils.get_current_assignments()

  # Organize by type (excomm and ucc are special)
  excomm = []
  ucc = []
  other = []
  for assignment in assignments:
    # Organize by type
    if assignment['is_excomm']:
      excomm.append(assignment)
    elif assignment['is_ucc']:
      ucc.append(assignment)
    else:
      other.append(assignment)

  ucc.sort(key=lambda x: x['office_name'])
  other.sort(key=lambda x: x['office_name'])

  # Tuple with name, email, and users, so that template can parse efficiently
  assignment_data = [
    ('Executive Committee', 'excomm', excomm),
    ('Upperclass Counselors', 'uccs', ucc),
    ('Other Offices', None, other)
  ]
  return flask.render_template('government.html', \
      assignment_data=assignment_data)

@app.route('/contact')
def show_contact():
  return flask.render_template('contact.html')
