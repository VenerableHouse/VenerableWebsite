from flask import request, session, g, redirect, url_for, abort, \
    render_template, flash
from sqlalchemy import text
from RuddockWebsite import app
from RuddockWebsite import constants
from RuddockWebsite import email_utils
from RuddockWebsite.decorators import login_required

@app.route('/')
def home():
  return render_template('index.html')

@app.route('/government')
def show_gov():
  # Get current officers
  query = text("""
    SELECT CONCAT(fname, ' ', lname) AS name, username, office_name,
      office_email, office_id, is_excomm, is_ucc
    FROM office_members_current
      NATURAL JOIN offices
      NATURAL JOIN members_current
      NATURAL JOIN users
      """)
  results = g.db.execute(query)

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

  ucc.sort(key=lambda d: d['office_name'])
  other.sort(key=lambda d: d['office_name'])

  # tuple with name, email, and users, so that template can parse efficiently
  all_types = [
    ('Executive Committee', 'excomm', excomm),
    ('Upperclass Counselors', 'uccs', ucc),
    ('Other Offices', None, other)
  ]

  return render_template('government.html', all_types = all_types)

@app.route('/about_us')
def show_about_us():
  return render_template('about_us.html')
