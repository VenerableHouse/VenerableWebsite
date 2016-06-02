"""
Tests routes in the admin module.
"""

import flask
import http.client

from ruddock import auth_utils
from ruddock.resources import Permissions
from ruddock.testing import utils
from ruddock.testing.fixtures import client

def test_admin_home(client):
  """Tests the /admin route."""
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.ADMIN)
  response = client.get(flask.url_for('admin.admin_home'))
  assert response.status_code == http.client.OK
