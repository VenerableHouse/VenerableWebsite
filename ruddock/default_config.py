"""Default website configurations, used only for testing.
"""

import os

from ruddock import environment

TEST = environment.Environment(
    db_hostname="localhost",
    db_name="ruddweb_test",
    db_user="ruddweb_test",
    db_password="public",
    debug=True,
    testing=True,
    secret_key="1234567890",
    media_folder=os.path.abspath("media"))

#TODO is there a better way of getting media_folder?