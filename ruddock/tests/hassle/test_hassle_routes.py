"""
Tests routes in the hassle module.
"""

import flask
import httplib

from ruddock.resources import Permissions
from ruddock.tests import utils
from ruddock.tests.fixtures import client

def test_run_hassle(client):
  """Tests /hassle route."""
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.HASSLE)
  response = client.get(flask.url_for('hassle.run_hassle'))
  assert response.status_code == httplib.OK
