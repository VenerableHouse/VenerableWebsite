import flask
import http.client

def test_txn(transaction):
  """
  This test is designed to break all other tests. Since it runs alphabetically
  before at least one test, this will detect when our pytest fixtures are broken.

  If it is broken, just rerun database/reset.sql.

  TODO this is not a good way to test that your fixtures are working lol
  """

  # Make sure we're not testing against prod!
  assert flask.current_app.config["TESTING"]

  flask.g.db.execute("""
  	SET FOREIGN_KEY_CHECKS = 0;
  	DELETE FROM members WHERE TRUE;
  	SET FOREIGN_KEY_CHECKS = 1
  """)
  result = flask.g.db.execute("SELECT * FROM members")
  assert len(result.fetchall()) == 0