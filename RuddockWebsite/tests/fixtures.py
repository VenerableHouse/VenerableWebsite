import pytest

from RuddockWebsite import app

@pytest.fixture
def client():
  """ Use the client fixture to test requests to the application. """
  # Specify a server.
  app.config['SERVER_NAME'] = "127.0.0.1"
  # Turn debug and testing modes on.
  app.config['DEBUG'] = True
  app.config['TESTING'] = True

  # Establish application context before running tests.
  ctx = app.app_context()
  ctx.push()

  return app.test_client()
