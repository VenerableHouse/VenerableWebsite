import flask
import pytest
import sqlalchemy

import ruddock
from ruddock import app

@pytest.yield_fixture
def client():
  """Use the client fixture to test requests to the application."""
  ruddock.init("test")
  # Specify a server name (needed for url building in the test client).
  app.config["SERVER_NAME"] = "127.0.0.1"

  # Establish application context before running tests.
  ctx = app.app_context()
  ctx.push()

  # TODO right now we set these two in before_request, which runs
  # when a request context is pushed. We shouldn't necessarily be
  # doing this; flask.g is a part of the application context, which
  # comes first. Apparently it's conventional to just allocate the
  # db connection on request?
  # But for now, we'll sneak in the initialization here :)
  flask.g.db = app.engine.connect()
  flask.g.session = app.sessionmaker()

  yield app.test_client()

  if flask.g.db is not None:
    flask.g.db.close()
