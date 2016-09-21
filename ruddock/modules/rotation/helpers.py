import flask
import sqlalchemy

DINNERS = list(range(1, 9))
BUCKETS = ['000', '-2', '-1', '0', '1', '2', '3']

def get_prefrosh_data(prefrosh_id):
  query = sqlalchemy.text("""
    SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
    bucket_name, votes_neg_two, votes_neg_one, votes_zero, votes_plus_one,
    votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN buckets WHERE prefrosh_id = (:pid)
    """)
  return flask.g.db.execute(query, pid=prefrosh_id).first()

def get_prefrosh_by_dinner(dinner_id):
  query = sqlalchemy.text("""
    SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
      bucket_name, votes_neg_two, votes_neg_one, votes_zero,
      votes_plus_one, votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN buckets WHERE dinner = (:d)
    """)
  return flask.g.db.execute(query, d=dinner_id).fetchall()

def get_image_contents(prefrosh_id):
  query = sqlalchemy.text("""
    SELECT image FROM rotation_prefrosh WHERE prefrosh_id = (:pid)
    """)
  return flask.g.db.execute(query, pid=prefrosh_id).first()['image']

def update_comments(prefrosh_id, comments):
  query = sqlalchemy.text("""
    UPDATE rotation_prefrosh SET comments = (:c) WHERE prefrosh_id = (:pid)
    """)
  flask.g.db.execute(query, c=comments, pid=prefrosh_id)

def update_votes(prefrosh_id, votes):
  query = sqlalchemy.text("""
    UPDATE rotation_prefrosh SET
      votes_neg_two = (:m2),
      votes_neg_one = (:m1),
      votes_zero = (:z),
      votes_plus_one = (:p1),
      votes_plus_two = (:p2),
      votes_plus_three = (:p3)
      WHERE prefrosh_id = (:pid)
    """)
  flask.g.db.execute(
    query,
    m2=votes['votes_neg_two'],
    m1=votes['votes_neg_one'],
    z=votes['votes_zero'],
    p1=votes['votes_plus_one'],
    p2=votes['votes_plus_two'],
    p3=votes['votes_plus_three'],
    pid=prefrosh_id
  )
