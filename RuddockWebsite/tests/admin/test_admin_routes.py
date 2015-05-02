"""
Tests routes in the admin module.
"""

import flask
import httplib

from RuddockWebsite import auth_utils
from RuddockWebsite.constants import Permissions
from RuddockWebsite.tests import utils
from RuddockWebsite.tests.fixtures import client

def test_admin_home(client):
  """ Tests the /admin route. """
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.Admin)
  response = client.get(flask.url_for('admin.admin_home'))
  assert response.status_code == httplib.OK
