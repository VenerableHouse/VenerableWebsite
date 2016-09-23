import flask
import sqlalchemy

DINNERS = range(1, 9)
BUCKETS = ['000', '-2', '-1', '0', '1', '2', '3']
VOTE_TUPLES = [
  {'vote_value': -2, 'vote_string': 'votes_neg_two'},
  {'vote_value': -1, 'vote_string': 'votes_neg_one'},
  {'vote_value': 0, 'vote_string': 'votes_zero'},
  {'vote_value': 1, 'vote_string': 'votes_plus_one'},
  {'vote_value': 2, 'vote_string': 'votes_plus_two'},
  {'vote_value': 3, 'vote_string': 'votes_plus_three'},
]

def get_dinner_prefrosh_by_prefrosh_id(prefrosh_id):
  query = sqlalchemy.text("""
    SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
    bucket_name, votes_neg_two, votes_neg_one, votes_zero, votes_plus_one,
    votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN rotation_buckets WHERE dinner IN
      (SELECT dinner FROM rotation_prefrosh WHERE prefrosh_id = :pid)
    """)
  return flask.g.db.execute(query, pid=prefrosh_id).fetchall()

def get_prefrosh_by_dinner(dinner_id):
  query = sqlalchemy.text("""
    SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
      bucket_name, votes_neg_two, votes_neg_one, votes_zero,
      votes_plus_one, votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN rotation_buckets WHERE dinner = (:d)
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

def format_name(first, last, preferred):
  name_parts = []
  name_parts.append(first)
  if preferred is not None:
    name_parts.append("({})".format(preferred))
  name_parts.append(last)
  return " ".join(name_parts)

def get_prefrosh_and_adjacent(prefrosh_id):
  dinner_prefrosh = get_dinner_prefrosh_by_prefrosh_id(prefrosh_id)
  idx, prefrosh = ((idx, pf) for idx, pf in enumerate(dinner_prefrosh)
                if pf['prefrosh_id'] == prefrosh_id).next()
  prev_id = dinner_prefrosh[idx - 1]['prefrosh_id'] if idx > 0 else None
  next_id = dinner_prefrosh[idx + 1]['prefrosh_id'] if idx < len(dinner_prefrosh) - 1 else None
  return [prefrosh, prev_id, next_id]
