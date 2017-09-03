import flask
import sqlalchemy
import cgi

DINNERS = range(1, 9)
BUCKETS = ['000', '-2', '-1', '0', '0.5', '1', '1.5', '2', '3']
VOTE_TUPLES = [
  {'vote_value': -2, 'vote_string': 'votes_neg_two'},
  {'vote_value': -1, 'vote_string': 'votes_neg_one'},
  {'vote_value': 0, 'vote_string': 'votes_zero'},
  {'vote_value': 1, 'vote_string': 'votes_plus_one'},
  {'vote_value': 2, 'vote_string': 'votes_plus_two'},
  {'vote_value': 3, 'vote_string': 'votes_plus_three'},
]

def get_dinner_prefrosh_by_prefrosh_id(prefrosh_id):
  """Returns the prefrosh with the given ID."""
  query = sqlalchemy.text("""
    SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
    bucket_name, votes_neg_two, votes_neg_one, votes_zero, votes_plus_one,
    votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN rotation_buckets WHERE dinner IN
      (SELECT dinner FROM rotation_prefrosh WHERE prefrosh_id = :pid)
    """)
  raw = flask.g.db.execute(query, pid=prefrosh_id).fetchall()
  return postprocess_prefrosh_data(raw)

def get_prefrosh_by_dinner(dinner_id):
  """Returns a list of prefrosh attending a particular dinner."""
  query = sqlalchemy.text("""
    SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
      bucket_name, votes_neg_two, votes_neg_one, votes_zero,
      votes_plus_one, votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN rotation_buckets WHERE dinner = (:d)
    """)
  raw = flask.g.db.execute(query, d=dinner_id).fetchall()
  return postprocess_prefrosh_data(raw)

def get_prefrosh_by_bucket(bucket_name):
  """Returns a list of prefrosh in a particular bucket."""
  query = sqlalchemy.text("""
    SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
    bucket_name, votes_neg_two, votes_neg_one, votes_zero,
      votes_plus_one, votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN rotation_buckets WHERE bucket_name = (:b)
    """)
  raw = flask.g.db.execute(query, b=bucket_name).fetchall()
  return postprocess_prefrosh_data(raw)

def get_all_prefrosh():
  """Returns the list of all prefrosh."""
  query = sqlalchemy.text("""
  SELECT prefrosh_id, first_name, preferred_name, last_name, dinner,
      bucket_name, votes_neg_two, votes_neg_one, votes_zero,
      votes_plus_one, votes_plus_two, votes_plus_three, comments
    FROM rotation_prefrosh NATURAL JOIN rotation_buckets
    """)
  raw = flask.g.db.execute(query).fetchall()
  return postprocess_prefrosh_data(raw)

def get_image_contents(prefrosh_id):
  """Return the picture for the specified prefrosh."""
  query = sqlalchemy.text("""
    SELECT image FROM rotation_prefrosh WHERE prefrosh_id = (:pid)
    """)
  return flask.g.db.execute(query, pid=prefrosh_id).first()['image']

def update_comments(prefrosh_id, comments):
  """Updates the database with new comments."""
  query = sqlalchemy.text("""
    UPDATE rotation_prefrosh SET comments = (:c) WHERE prefrosh_id = (:pid)
    """)
  flask.g.db.execute(query, c=comments, pid=prefrosh_id)

def update_votes(prefrosh_id, votes):
  """Updates the database with new votes."""
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
  """Sticks together the parts of a prefrosh's name, including preferred."""
  name_parts = []
  name_parts.append(first)
  if preferred is not None:
    name_parts.append("({})".format(preferred))
  name_parts.append(last)
  return " ".join(name_parts)

def get_prefrosh_and_adjacent(prefrosh_id, prefrosh_list):
  """Returns a prefrosh and the IDs of the neighboring two frosh in the provided list."""
  idx, prefrosh = ((idx, pf) for idx, pf in enumerate(prefrosh_list)
              if pf['prefrosh_id'] == prefrosh_id).next()
  prev_id = prefrosh_list[idx - 1]['prefrosh_id'] if idx > 0 else None
  next_id = prefrosh_list[idx + 1]['prefrosh_id'] if idx < len(prefrosh_list) - 1 else None
  return [prefrosh, prev_id, next_id]

def postprocess_prefrosh_data(ls):
  """Formats names and escapes comments for a prefrosh."""
  prefrosh_list = [dict(pf.items()) for pf in ls]
  for prefrosh in prefrosh_list:
    prefrosh['full_name'] = format_name(
      prefrosh['first_name'], prefrosh['last_name'], prefrosh['preferred_name'])
    prefrosh['escaped_comments'] = escape_comments(prefrosh['comments'])
  return prefrosh_list

def change_bucket(prefrosh_id, new_bucket_name):
  """Moves a prefrosh to the specified bucket."""
  query = sqlalchemy.text("""
    UPDATE rotation_prefrosh SET bucket_id =
      (SELECT bucket_id FROM rotation_buckets WHERE bucket_name = (:b))
    WHERE prefrosh_id = (:pid)
    """)
  flask.g.db.execute(query, b=new_bucket_name, pid=prefrosh_id)

def escape_comments(str):
  """Escapes comments so they don't mess with HTML formatting."""
  if str is not None:
    # cgi.escape escapes '<', '>', and '&'
    # unicode.escape escapes newlines to '\n'
    # the replace statement escapes apostrophes
    # TODO: refactor this to something less hacky
    ret = str.encode('unicode_escape')
    ret = ret.replace("'", "\\'")
    ret = cgi.escape(ret)
    return ret
  else:
    return str
