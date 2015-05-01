"""
Tests routes that are not in a module.
"""

import flask
import httplib

from RuddockWebsite.tests.fixtures import client

def test_home(client):
  """ Tests the / route. """
  rv = client.get(flask.url_for('home'))
  assert rv.status_code == httplib.OK

def test_government(client):
  """ Tests the /government route. """
  rv = client.get(flask.url_for('show_gov'))
  assert rv.status_code == httplib.OK

def test_contact(client):
  """ Tests the /contact route. """
  rv = client.get(flask.url_for('show_contact'))
  assert rv.status_code == httplib.OK
