from flask import request, session, g, redirect, url_for, abort, \
    render_template, flash
from sqlalchemy import text
import datetime
import re

from RuddockWebsite import app, common_helpers, constants, email_utils
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

@app.route('/account/create/<create_account_key>')
def create_account(create_account_key):
  ''' Checks the key. If valid, displays the create account page. '''

  def get_user_data(user_id):
    ''' Helper to get user data. '''
    query = text("""
      SELECT fname, lname, uid, matriculate_year, grad_year, email
      FROM members
      WHERE user_id=:uid
      """)
    return g.db.execute(query, uid=user_id).first()

  user_id = auth.check_create_account_key(create_account_key)
  if user_id is None:
    flash('Invalid request. Please check your link and try again. If you continue to encounter problems, please find an IMSS rep.')
    return redirect(url_for('home'))

  user_data = get_user_data(user_id)
  if user_data is None:
    flash('An unexpected error occurred. Please find an IMSS rep.')
    return redirect(url_for('home'))
  return render_template('create_account.html', user_data=user_data,
      key=create_account_key)

@app.route('/account/create/<create_account_key>/submit', methods=['POST'])
def create_account_submit(create_account_key):
  ''' Handles a create account request. '''
  user_id = auth.check_create_account_key(create_account_key)
  if user_id is None:
    # Key is invalid.
    flash("Someone's been naughty.")
    return redirect(url_for('home'))
  username = request.form.get('username', None)
  password = request.form.get('password', None)
  password2 = request.form.get('password2', None)
  birthday = request.form.get('birthday', None)
  if username is None or password is None or password2 is None or birthday is None:
    flash('Invalid request.')
    return redirect(url_for('home'))

  # Username and password will be checked by account creation.
  # Check birthday format.
  try:
    datetime.datetime.strptime(birthday, '%Y-%m-%d')
  except ValueError:
    flash("Invalid birthday.")
    return redirect(url_for('create_account', create_account_key=create_account_key))
  if auth.handle_create_account(user_id, username, password, password2):
    # Update birthday.
    query = text("UPDATE members SET bday=:b WHERE user_id=:uid")
    g.db.execute(query, b=birthday, uid=user_id)
    flash('Account successfully created.')
    return redirect(url_for('home'))
  else:
    # Flashes already handled.
    return redirect(url_for('create_account', create_account_key=create_account_key))
