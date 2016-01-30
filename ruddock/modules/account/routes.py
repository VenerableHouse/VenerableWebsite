import flask

from ruddock import auth_utils
from ruddock.modules.account import blueprint, helpers

@blueprint.route('/create/<create_account_key>')
def create_account(create_account_key):
  """ Checks the key. If valid, displays the create account page. """
  user_id = auth_utils.check_create_account_key(create_account_key)
  if user_id is None:
    flask.flash('Invalid request. Please check your link and try again. If you continue to encounter problems, please find an IMSS rep.')
    return flask.redirect(flask.url_for('home'))

  user_data = helpers.get_user_data(user_id)
  if user_data is None:
    flask.flash('An unexpected error occurred. Please find an IMSS rep.')
    return flask.redirect(flask.url_for('home'))
  return flask.render_template('create_account.html', user_data=user_data,
      key=create_account_key)

@blueprint.route('/create/<create_account_key>/submit', methods=['POST'])
def create_account_submit(create_account_key):
  """ Handles a create account request. """
  user_id = auth_utils.check_create_account_key(create_account_key)
  if user_id is None:
    # Key is invalid.
    flask.flash("Someone's been naughty.")
    return flask.redirect(flask.url_for('home'))
  username = flask.request.form.get('username', None)
  password = flask.request.form.get('password', None)
  password2 = flask.request.form.get('password2', None)
  birthday = flask.request.form.get('birthday', None)
  if username is None \
      or password is None \
      or password2 is None \
      or birthday is None:
    flask.flash('Invalid request.')
    return flask.redirect(flask.url_for('home'))

  if helpers.handle_create_account(user_id, username, password, password2,
      birthday):
    flask.flash('Account successfully created.')
    return flask.redirect(flask.url_for('home'))
  else:
    # Flashes already handled.
    return flask.redirect(flask.url_for('account.create_account',
        create_account_key=create_account_key))
