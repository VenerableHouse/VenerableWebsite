"""
Tests routes in the hassle module.
"""

import flask
import httplib

from RuddockWebsite.constants import Permissions
from RuddockWebsite.tests.fixtures import client

def test_run_hassle(client):
  """ Tests /hassle route. """
  with client.session_transaction() as session:
    session['username'] = 'test_user'
    session['permissions'] = [int(Permissions.RunHassle)]
  rv = client.get(flask.url_for('hassle.run_hassle'))
  assert rv.status_code == httplib.OK
