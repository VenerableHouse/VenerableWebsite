"""
Tests routes in the government module.
"""

import flask
import http.client

def test_government(client):
  """Tests the /government route."""
  response = client.get(flask.url_for('government.government_home'))
  assert response.status_code == http.client.OK

