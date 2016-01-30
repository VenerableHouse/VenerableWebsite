import pytest
import sqlalchemy

from ruddock import app
from ruddock import config

@pytest.fixture
def client():
  """Use the client fixture to test requests to the application."""
  # Specify a server name (needed for url building in the test client).
  app.config['SERVER_NAME'] = "127.0.0.1"
  # Turn debug and testing modes on.
  app.config['DEBUG'] = True
  app.config['TESTING'] = True

  # Establish application context before running tests.
  ctx = app.app_context()
  ctx.push()
  return app.test_client()

@pytest.fixture(scope="function")
def db():
  """
  Provides a database connection for testing the database directly. A
  transaction is used to ensure that testing does not change the database, and
  that each test is run against the same initial state of the database.

  Be warned that this is for testing methods that modify the database directly.
  It does NOT roll back changes made as a result of sending requests to
  endpoints that change database state.
  """
  engine = sqlalchemy.create_engine(config.DB_URI, convert_unicode=True)
  connection = engine.connect()
  # Use a transaction so we can rollback it later.
  transaction = connection.begin()

  def teardown():
    transaction.rollback()
    connection.close()

  return connection
