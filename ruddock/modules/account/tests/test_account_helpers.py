import flask
import http.client

from ruddock.modules.account import helpers

def test_get_user_data(client):
  result = helpers.get_user_data(2)
  assert result["first_name"] == "Rainbow"
  assert result["last_name"] == "Dash"

  result = helpers.get_user_data(200)
  assert result is None

def test_request_account(client):
	# takes arguments (uid, last_name)

	# not a known uid
	success, errs = helpers.handle_request_account(1000000, "celestia")
	assert not success

	# already exists
	success, errs = helpers.handle_request_account(1000003, "celestia")
	assert not success

	# wrong last name
	success, errs = helpers.handle_request_account(1000004, "luna")
	assert not success

	# successful
	success, errs = helpers.handle_request_account(1000004, "celestia")
	assert success

def test_create_account(client, app):

	# the route checks for the create_account_key field, but the helper doesn't
	# takes arguments (user_id, username, password, password2, birthday)

	good_user = "some_user"
	bad_user = "b@d_us3r"

	good_pass = "alk4k2j49ss9"
	bad_pass = "skjs"

	good_bday = "2018-11-24"
	bad_bday = "11-24-2018"

	# for readability
	def check(expected, user_id, username, password, birthday):
		success = helpers.handle_create_account(user_id, username, password, password, birthday)
		assert success == expected


	# needed because we call flask.flash within the helpers
	with app.test_request_context():
		check(False, 4, bad_user, good_pass, good_bday)
		check(False, 4, good_user, bad_pass, good_bday)
		check(False, 4, good_user, good_pass, bad_bday)
		check(True, 4, good_user, good_pass, good_bday)