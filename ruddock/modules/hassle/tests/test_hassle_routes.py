"""
Tests routes in the hassle module.
"""

import flask
import http.client

from ruddock.resources import Permissions
from ruddock.testing import utils

def test_run_hassle(client):
  """Tests /hassle route."""
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.HASSLE)
  response = client.get(flask.url_for('hassle.run_hassle'))
  assert response.status_code == http.client.OK
