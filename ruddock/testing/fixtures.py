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
  # Create database engine object.
  engine = sqlalchemy.create_engine(app.config["DB_URI"], convert_unicode=True)
  # Connect to the database and publish it in flask.g
  flask.g.db = engine.connect()

  yield app.test_client()
  flask.g.db.close()
