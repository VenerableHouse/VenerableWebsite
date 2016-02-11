"""Default website configurations, used only for testing.
"""

from ruddock import environment

TEST = environment.Environment(
    db_hostname="localhost",
    db_name="ruddweb_test",
    db_user="ruddweb_test",
    db_password="public",
    debug=True,
    secret_key="1234567890")
