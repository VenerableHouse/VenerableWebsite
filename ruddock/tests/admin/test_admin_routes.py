"""
Tests routes in the admin module.
"""

import flask
import httplib

from ruddock import auth_utils
from ruddock.resources import Permissions
from ruddock.tests import utils
from ruddock.tests.fixtures import client

def test_admin_home(client):
  """Tests the /admin route."""
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.ADMIN)
  response = client.get(flask.url_for('admin.admin_home'))
  assert response.status_code == httplib.OK
