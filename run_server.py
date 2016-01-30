"""
Starts an instance of the test server for testing locally. The production
enviornment uses the wsgi script to start up and bypasses this file, so we are
free to have debug settings enabled.
"""
from ruddock import app
from ruddock import config

if __name__ == "__main__":
  test_port = getattr(config, 'TEST_PORT', 5000)
  debug = getattr(config, 'DEBUG', True)
  app.run(debug=debug, port=test_port)
