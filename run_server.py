# Note: this file is only used for testing locally. The production environment
# uses wsgi to start up, and bypasses this file. So we are free to have debug
# settings enabled.
from RuddockWebsite import app, config

test_port = getattr(config, 'TEST_PORT', 5000)
debug = getattr(config, 'DEBUG', True)
app.run(debug=debug, port=test_port)
