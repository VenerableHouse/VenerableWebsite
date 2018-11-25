import flask
import pytest
import re
import sqlalchemy
import tempfile

import ruddock
from ruddock import app as ruddock_app

SQL_SCHEMA_FILE = "database/schema.sql"
SQL_TEST_DATA_FILE = "database/test_data.sql"

_parsed_sql = []  # initialized by reset_database

def parse_sql(script):
  """
  Given the contents of a SQL script, splits it up into a list of individual
  SQL statements.
  """

  # Remove any block comments
  # (note: '?' is lazy matching, so we won't gobble up too much)
  script = re.sub(r"/\*.*?\*/", "", script, flags=re.DOTALL)

  # Remove any trailing comments
  # (note: '.' matches everything BUT newline)
  script = re.sub(r"--.*$", "", script, flags=re.MULTILINE)  

  # Drop all newlines
  script = script.replace("\n", "")

  # Split on semicolons, because there's no semicolons internal to a statement
  # (unless we need stored procedures, but we don't)
  statements = script.split(";")

  return [s for s in statements if s]  # no empty statements

def reset_database():

  # Load sql statements into memory if we haven't yet
  global _parsed_sql

  if not _parsed_sql:
    with open(SQL_SCHEMA_FILE, "r") as f:
      _parsed_sql += parse_sql(f.read())
    with open(SQL_TEST_DATA_FILE, "r") as f:
      _parsed_sql += parse_sql(f.read())

    # Figure out what tables (and views) we have, so we can drop them later
    drops = []
    for s in _parsed_sql:
      if s.startswith("CREATE "):
        create, type_, name, _ = s.split(" ", maxsplit=3)
        drops.append("DROP {} IF EXISTS {}".format(type_, name))

    # drop tables in the opposite order of creation
    _parsed_sql = list(reversed(drops)) + _parsed_sql

  # Connect to the database and reset it
  db = ruddock_app.engine.connect()
  for s in _parsed_sql:
    db.execute(s)
  db.close()

@pytest.yield_fixture(scope='session')
def app():
  """
  Return the Flask app for the Ruddock website.

  Will always be in test mode. Will likely never need to be used directly,
  but other fixtures depend on this.
  """

  # Initialize the app, with our DB override
  ruddock.init("test")

  # Specify a server name (needed for url building in the test client).
  ruddock_app.config["SERVER_NAME"] = "127.0.0.1"

  # Initialize the database
  reset_database()

  with ruddock_app.app_context():
    yield ruddock_app


@pytest.yield_fixture
def client(app):
  """
  Return a Flask test client.

  Use for testing routes.
  """

  # before_request is not called automatically, so, we have to connect
  # to the DB ourselves
  flask.g.db = app.engine.connect()

  yield app.test_client()

  # Undo our setup
  flask.g.db.close()

  # TODO this is expensive; if possible, avoid calling it
  reset_database()
