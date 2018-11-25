import flask
import pytest
import sqlalchemy

import ruddock
from ruddock import app as ruddock_app

@pytest.fixture(scope='session')
def app():
  """
  Return the Flask app for the Ruddock website.

  Will always be in test mode. Will likely never need to be used directly,
  but other fixtures depend on this.
  """
  ruddock.init("test")

  # Specify a server name (needed for url building in the test client).
  ruddock_app.config["SERVER_NAME"] = "127.0.0.1"

  return ruddock_app

@pytest.yield_fixture(scope='function')
def client(app):
  """
  Return a Flask test client.

  Use for testing routes.
  """

  # Establish application and request context before running tests.
  app_ctx = ruddock_app.app_context()
  req_ctx = ruddock_app.test_request_context()
  app_ctx.push()
  req_ctx.push()

  # Connect to the database and publish it in flask.g
  flask.g.db = app.engine.connect()

  yield app.test_client()

  # Undo our setup
  flask.g.db.close()
  req_ctx.pop()
  app_ctx.pop()

@pytest.yield_fixture(scope='function')
def transaction(client):
  """
  Using this fixture will wrap all database operations in a transaction. The
  fixture itself returns None, and isn't particularly useful.
  """
  txn = flask.g.db.begin()

  try:
    yield None
  finally:
    txn.rollback()
