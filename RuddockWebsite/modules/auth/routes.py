from flask import render_template, redirect, flash, url_for, request, session
from RuddockWebsite import auth_utils
from RuddockWebsite import constants
from RuddockWebsite.modules.auth import blueprint, helpers

@blueprint.route('/login')
def login():
  ''' Displays the login page. '''
  return render_template('login.html')

@blueprint.route('/login/submit', methods=['POST'])
def login_submit():
  ''' Handles authentication. '''
  username = request.form.get('username', None)
  password = request.form.get('password', None)

  if username is not None and password is not None:
    user_id = helpers.authenticate(username, password)
    if user_id is not None:
      permissions = auth_utils.get_permissions(username)
      session['username'] = username
      session['permissions'] = permissions
      # True if there's any reason to show a link to the admin interface.
      session['show_admin'] = len(auth_utils.generate_admin_links()) > 0
      # Update last login time
      auth_utils.update_last_login(username)

      # Return to previous page if in session
      if 'next' in session:
        redirect_to = session.pop('next')
        return redirect(redirect_to)
      else:
        return redirect(url_for('home'))
  flash('Incorrect username or password. Please try again!')
  return redirect(url_for('auth.login'))

@blueprint.route('/login/forgot')
def forgot_password():
  ''' Displays a form for the user to reset a forgotten password. '''
  return render_template('forgot_password.html')

@blueprint.route('/login/forgot/submit', methods=['POST'])
def forgot_password_submit():
  ''' Handle forgotten password submission. '''
  username = request.form.get('username', None)
  email = request.form.get('email', None)

  if helpers.handle_forgotten_password(username, email):
    flash("An email with a recovery link has been sent. If you no longer have access to your email (alums), please contact an IMSS rep to recover your account.")
    return redirect(url_for('auth.login'))
  else:
    flash("Incorrect username and/or email. If you continue to have issues with account recovery, contact an IMSS rep.")
    return redirect(url_for('auth.forgot_password'))

@blueprint.route('/login/reset/<reset_key>')
def reset_password(reset_key):
  ''' Checks the reset key. If successful, displays the password reset prompt. '''
  username = auth_utils.check_reset_key(reset_key)
  if username is None:
    flash('Invalid request. If your link has expired, then you will need to generate a new one. If you continue to encounter problems, please find an IMSS rep.')
    return redirect(url_for('auth.forgot_password'))
  return render_template('reset_password.html', username=username,
      reset_key=reset_key)

@blueprint.route('/login/reset/<reset_key>/submit', methods=['POST'])
def reset_password_submit(reset_key):
  ''' Handles a password reset request. '''
  username = auth_utils.check_reset_key(reset_key)
  if username is None:
    # Reset key was invalid.
    flash("Someone's making it on the naughty list this year...")
    return redirect(url_for('auth.forgot_password'))
  new_password = request.form.get('password', '')
  new_password2 = request.form.get('password2', '')
  if helpers.handle_password_reset(username, new_password, new_password2):
    flash('Password reset was successful.')
    return redirect(url_for('auth.login'))
  else:
    # Password reset handler handles error flashes.
    return redirect(url_for('auth.reset_password', reset_key=reset_key))

@blueprint.route('/logout')
def logout():
  session.pop('username', None)
  return redirect(url_for('home'))
