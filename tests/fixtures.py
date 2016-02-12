import pytest
import sqlalchemy

import ruddock
from ruddock import app

@pytest.fixture
def client():
  """Use the client fixture to test requests to the application."""
  ruddock.init("test")
  # Specify a server name (needed for url building in the test client).
  app.config['SERVER_NAME'] = "127.0.0.1"
  # Turn testing modes on.
  app.config['TESTING'] = True

  # Establish application context before running tests.
  ctx = app.app_context()
  ctx.push()
  return app.test_client()
