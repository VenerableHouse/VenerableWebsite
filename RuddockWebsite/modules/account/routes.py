from flask import render_template, redirect, flash, url_for, request
from RuddockWebsite import auth_utils
from RuddockWebsite.modules.account import blueprint, helpers

@blueprint.route('/create/<create_account_key>')
def create_account(create_account_key):
  ''' Checks the key. If valid, displays the create account page. '''
  user_id = auth_utils.check_create_account_key(create_account_key)
  if user_id is None:
    flash('Invalid request. Please check your link and try again. If you continue to encounter problems, please find an IMSS rep.')
    return redirect(url_for('home'))

  user_data = helpers.get_user_data(user_id)
  if user_data is None:
    flash('An unexpected error occurred. Please find an IMSS rep.')
    return redirect(url_for('home'))
  return render_template('create_account.html', user_data=user_data,
      key=create_account_key)

@blueprint.route('/create/<create_account_key>/submit', methods=['POST'])
def create_account_submit(create_account_key):
  ''' Handles a create account request. '''
  user_id = auth_utils.check_create_account_key(create_account_key)
  if user_id is None:
    # Key is invalid.
    flash("Someone's been naughty.")
    return redirect(url_for('home'))
  username = request.form.get('username', None)
  password = request.form.get('password', None)
  password2 = request.form.get('password2', None)
  birthday = request.form.get('birthday', None)
  if username is None \
      or password is None \
      or password2 is None \
      or birthday is None:
    flash('Invalid request.')
    return redirect(url_for('home'))

  if helpers.handle_create_account(user_id, username, password, password2,
      birthday):
    flash('Account successfully created.')
    return redirect(url_for('home'))
  else:
    # Flashes already handled.
    return redirect(url_for('account.create_account',
        create_account_key=create_account_key))
