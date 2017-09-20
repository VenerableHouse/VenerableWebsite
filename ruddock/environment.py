class Environment(object):
  """A configuration environment.

  Provides environment-specific configuration variables:
    db_uri: uri to connect to the database.
    db_hostname: database hostname.
    db_name: name of the database.
    db_user: database user.
    db_password: database password.
    debug: bool for whether or not debug mode should be enabled.
    testing: bool for whether or not testing mode should be enabled.
    secret_key: secret key for session cookie.
  """

  def __init__(self, db_hostname, db_name, db_user, db_password, debug,
      testing, secret_key, media_folder):
    self.db_hostname = db_hostname
    self.db_name = db_name
    self.db_user = db_user
    self.db_password = db_password
    self.debug = debug
    self.testing = testing
    self.secret_key = secret_key
    self.media_folder = media_folder

  @property
  def db_uri(self):
    return "mysql://{0}:{1}@{2}/{3}".format(
        self.db_user, self.db_password, self.db_hostname, self.db_name)
