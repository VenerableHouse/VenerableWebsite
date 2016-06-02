import flask
import sqlalchemy

alleys = [1, 2, 3, 4, 5, 6]

def get_all_members():
  """Gets all current members (potential hassle participants)."""
  query = sqlalchemy.text("""
    SELECT user_id, name, graduation_year,
      member_type, membership_desc, user_id IN (
        SELECT user_id FROM hassle_participants
      ) AS participating
    FROM members
      NATURAL JOIN members_extra
      NATURAL JOIN members_current
      NATURAL JOIN membership_types
    ORDER BY member_type, graduation_year, name
    """)
  return flask.g.db.execute(query).fetchall()

def get_rising_members():
  """Gets IDs for all current frosh, sophomores, and juniors."""
  query = sqlalchemy.text("""
    SELECT user_id
    FROM members NATURAL JOIN members_current
    WHERE member_type = 1
      AND CONCAT(graduation_year, '-07-01') > NOW() + INTERVAL 1 YEAR
    """)
  return flask.g.db.execute(query).fetchall()

def get_frosh():
  """Gets IDs for all current frosh."""
  query = sqlalchemy.text("""
    SELECT user_id
    FROM members NATURAL JOIN members_current
    WHERE member_type = 1
      AND CONCAT(graduation_year, '-07-01') > NOW() + INTERVAL 3 YEAR
    """)
  return flask.g.db.execute(query).fetchall()

def get_participants():
  """Gets all members participating in the hassle."""
  query = sqlalchemy.text("""
    SELECT user_id, name, graduation_year,
      member_type, membership_desc
    FROM members
      NATURAL JOIN members_extra
      NATURAL JOIN hassle_participants
      NATURAL JOIN membership_types
    ORDER BY member_type, graduation_year, name
    """)
  return flask.g.db.execute(query).fetchall()

def get_available_participants():
  """Gets all participants who have not yet picked a room."""
  query = sqlalchemy.text("""
    SELECT user_id, name
    FROM members
      NATURAL JOIN members_extra
      NATURAL JOIN hassle_participants
    WHERE user_id NOT IN (
      SELECT user_id FROM hassle_events
      UNION
      SELECT roommate_id FROM hassle_roommates
    )
    ORDER BY name
    """)
  return flask.g.db.execute(query).fetchall()

def set_participants(participants):
  """Sets hassle participants."""
  # Delete old participants.
  delete_query = sqlalchemy.text("DELETE FROM hassle_participants")
  flask.g.db.execute(delete_query)

  # Insert new participants.
  insert_query = sqlalchemy.text("""
    INSERT INTO hassle_participants (user_id)
    VALUES (:p)
    """)
  for participant in participants:
    flask.g.db.execute(insert_query, p=participant)

def get_all_rooms():
  """Gets all rooms in the house."""
  query = sqlalchemy.text("""
    SELECT room_number, alley,
      room_number IN (
        SELECT room_number FROM hassle_rooms
      ) AS participating
    FROM rooms
    ORDER BY room_number
    """)
  return flask.g.db.execute(query).fetchall()

def get_participating_rooms():
  """Gets all rooms participating in the hassle."""
  query = sqlalchemy.text("""
    SELECT room_number, alley
    FROM hassle_rooms NATURAL JOIN rooms
    ORDER BY room_number
    """)
  return flask.g.db.execute(query).fetchall()

def get_available_rooms():
  """Gets all rooms that have not been picked."""
  query = sqlalchemy.text("""
    SELECT room_number, alley
    FROM hassle_rooms NATURAL JOIN rooms
    WHERE room_number NOT IN (
      SELECT room_number FROM hassle_events
    )
    ORDER BY room_number
    """)
  return flask.g.db.execute(query).fetchall()

def get_rooms_remaining():
  """
  Gets the number of rooms remaining for each alley.
  Returns a dict mapping alley to number of remaining rooms.
  """
  alley_counts = dict(list(zip(alleys, [0] * len(alleys))))
  available_rooms = get_available_rooms()
  for room in available_rooms:
    alley_counts[room['alley']] += 1
  return alley_counts

def set_rooms(rooms):
  """Sets rooms available for hassle."""
  # Delete old rooms.
  delete_query = sqlalchemy.text("DELETE FROM hassle_rooms")
  flask.g.db.execute(delete_query)

  # Insert rooms
  insert_query = sqlalchemy.text("INSERT INTO hassle_rooms (room_number) VALUES (:r)")
  for room in rooms:
    flask.g.db.execute(insert_query, r=room)

def get_events():
  """Returns events in the hassle."""
  query = sqlalchemy.text("""
    SELECT hassle_event_id, members.user_id, name,
      hassle_events.room_number, alley
    FROM hassle_events
      JOIN members ON hassle_events.user_id = members.user_id
      JOIN members_extra ON hassle_events.user_id = members_extra.user_id
      JOIN rooms ON hassle_events.room_number = rooms.room_number
    ORDER BY hassle_event_id
    """)
  return flask.g.db.execute(query).fetchall()

def get_events_with_roommates():
  """Returns events with additional roommate information."""
  events = get_events()
  results = []

  for event in events:
    row_dict = dict(list(event.items()))
    roommates = get_roommates(event['user_id'])
    row_dict['roommates'] = roommates
    occupant_names = [event['name']]
    for roommate in roommates:
      occupant_names.append(roommate['name'])
    row_dict['occupants'] = ', '.join(occupant_names)
    results.append(row_dict)
  return results

def new_event(user_id, room_number, roommates):
  """Inserts a new event into the database."""
  # Insert event.
  query = sqlalchemy.text("""
    INSERT INTO hassle_events (user_id, room_number) VALUES (:u, :r)
    """)
  flask.g.db.execute(query, u=user_id, r=room_number)

  # Insert roommates.
  query = sqlalchemy.text("""
    INSERT INTO hassle_roommates (user_id, roommate_id) VALUES (:u, :r)
    """)
  for roommate in roommates:
    flask.g.db.execute(query, u=user_id, r=roommate)

def clear_events(event_id=None):
  """
  Clears hassle events. If event_id is provided, all events after (not
  including) the provided event are cleared. Otherwise, everything is
  cleared.
  """
  if event_id:
    query = sqlalchemy.text("""
      DELETE FROM hassle_roommates
      WHERE user_id IN (
        SELECT user_id FROM hassle_events
        WHERE hassle_event_id >= :e
      )""")
    flask.g.db.execute(query, e=event_id)

    query = sqlalchemy.text("DELETE FROM hassle_events WHERE hassle_event_id >= :e")
    flask.g.db.execute(query, e=event_id)
  else:
    flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_roommates"))
    flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_events"))

def get_roommates(user_id):
  """Gets all roommates for the provided user."""
  query = sqlalchemy.text("""
    SELECT roommate_id, name
    FROM hassle_roommates
      JOIN members ON hassle_roommates.roommate_id = members.user_id
      JOIN members_extra ON members.user_id = members_extra.user_id
    WHERE hassle_roommates.user_id=:u
    ORDER BY name
    """)
  return flask.g.db.execute(query, u=user_id).fetchall()

def clear_all():
  """Clears all current hassle data."""
  flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_roommates"))
  flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_events"))
  flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_participants"))
  flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_rooms"))
