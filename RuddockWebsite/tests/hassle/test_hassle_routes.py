"""
Tests routes in the hassle module.
"""

import flask
import httplib

from RuddockWebsite.constants import Permissions
from RuddockWebsite.tests import utils
from RuddockWebsite.tests.fixtures import client

def test_run_hassle(client):
  """ Tests /hassle route. """
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.RunHassle)
  response = client.get(flask.url_for('hassle.run_hassle'))
  assert response.status_code == httplib.OK
