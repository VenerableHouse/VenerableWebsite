from flask import request, session, g, redirect, url_for, abort, \
    render_template, flash
from sqlalchemy import text
import datetime
import re

from RuddockWebsite import app, auth, common_helpers, constants, email_utils
from RuddockWebsite.decorators import login_required

@app.route('/')
def home():
  return render_template('index.html')

@app.route('/login')
def login():
  ''' Displays the login page. '''
  return render_template('login.html')

@app.route('/login/submit', methods=['POST'])
def attempt_login():
  ''' Handles authentication. '''

  username = request.form.get('username', None)
  password = request.form.get('password', None)

  if username is not None and password is not None:
    user_id = auth.authenticate(username, password)
    if user_id is not None:
      permissions = auth.get_permissions(username)
      session['username'] = username
      session['permissions'] = permissions
      # True if there's any reason to show a link to the admin interface.
      session['show_admin'] = auth.check_permission(constants.Permissions.Admin)
      # Update last login time
      auth.update_last_login(username)

      # Return to previous page if in session
      if 'next' in session:
        redirect_to = session.pop('next')
        return redirect(redirect_to)
      else:
        return redirect(url_for('home'))
  flash('Incorrect username or password. Please try again!')
  return redirect(url_for('login'))

@app.route('/login/forgot')
def forgot_password():
  ''' Displays a form for the user to reset a forgotten password. '''
  return render_template('forgot_password.html')

@app.route('/login/forgot/submit', methods=['POST'])
def forgot_password_submit():
  ''' Handle forgotten password submission. '''

  username = request.form.get('username', None)
  email = request.form.get('email', None)

  if auth.handle_forgotten_password(username, email):
    flash("An email with a recovery link has been sent. If you no longer have access to your email (alums), please contact an IMSS rep to recover your account.")
    return redirect(url_for('login'))
  else:
    flash("Incorrect username and/or email. If you continue to have issues with account recovery, contact an IMSS rep.")
    return redirect(url_for('forgot_password'))

@app.route('/login/reset/<reset_key>')
def reset_password(reset_key):
  ''' Checks the reset key. If successful, displays the password reset prompt. '''
  username = auth.check_reset_key(reset_key)
  if username is None:
    flash('Invalid request. If your link has expired, then you will need to generate a new one.')
    return redirect(url_for('forgot_password'))
  return render_template('reset_password.html', username=username, \
      reset_key=reset_key)

@app.route('/login/reset/<reset_key>/submit', methods=['POST'])
def reset_password_submit(reset_key):
  ''' Handles a password reset request. '''
  username = auth.check_reset_key(reset_key)
  if username is None:
    # Reset key was invalid.
    flash("Someone's making it on the naughty list this year...")
    return redirect(url_for('forgot_password'))
  new_password = request.form.get('password', '')
  new_password2 = request.form.get('password2', '')
  if auth.handle_password_reset(username, new_password, new_password2):
    flash('Password reset was successful.')
    return redirect(url_for('home'))
  else:
    # Password reset handler handles error flashes.
    return redirect(url_for('reset_password', reset_key=reset_key))

@app.route('/logout')
def logout():
  session.pop('username', None)
  return redirect(url_for('home'))

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
