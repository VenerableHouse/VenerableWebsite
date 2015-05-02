"""
Tests routes in the users module.
"""

import flask
import httplib

from RuddockWebsite.constants import Permissions
from RuddockWebsite.tests import utils
from RuddockWebsite.tests.fixtures import client

def test_show_users(client):
  """ Tests /users route. """
  with client.session_transaction() as session:
    utils.login(session)
  response = client.get(flask.url_for('users.show_users'))
  assert response.status_code == httplib.OK
