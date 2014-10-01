from sqlalchemy import text
from flask import g

def get_all_members():
  ''' Gets all current members (potential hassle participants). '''

  query = text("""
    SELECT user_id, CONCAT(fname, ' ', lname) AS name, grad_year,
      membership_desc, user_id IN (
        SELECT user_id FROM hassle_participants
      ) AS participating
    FROM members_current NATURAL JOIN membership_types
    ORDER BY membership_type, grad_year, name
    """)
  return g.db.execute(query)

def set_participants(participants):
  ''' Sets hassle participants. '''

  # Delete old participants.
  delete_query = text("DELETE FROM hassle_participants")
  g.db.execute(delete_query)

  # Insert new participants.
  insert_query = text("INSERT INTO hassle_participants (user_id) VALUES (:p)")
  for participant in participants:
    g.db.execute(insert_query, p=participant)

def get_all_rooms():
  ''' Gets all rooms in the house. '''

  query = text("""
    SELECT room_number, alley,
      room_number IN (
        SELECT room_number FROM hassle_rooms
      ) AS participating
    FROM rooms
    ORDER BY room_number
    """)
  return g.db.execute(query)

def set_rooms(rooms):
  ''' Sets rooms available for hassle. '''

  # Delete old rooms.
  delete_query = text("DELETE FROM hassle_rooms")
  g.db.execute(delete_query)

  # Insert rooms
  insert_query = text("INSERT INTO hassle_rooms (room_number) VALUES (:r)")
  for room in rooms:
    g.db.execute(insert_query, r=room)

def get_participants():
  ''' Gets all members participating in the hassle. '''

  query = text("""
    SELECT user_id, CONCAT(fname, ' ', lname) AS name, grad_year,
      membership_desc
    FROM members NATURAL JOIN hassle_participants NATURAL JOIN membership_types
    ORDER BY membership_type, grad_year, name
    """)
  return g.db.execute(query)

def get_rooms():
  ''' Gets all rooms participating in the hassle. '''

  query = text("""
    SELECT room_number, alley
    FROM rooms NATURAL JOIN hassle_rooms
    ORDER BY room_number
    """)
  return g.db.execute(query)

def clear_all():
  ''' Clears all current hassle data. '''

  g.db.execute(text("DELETE FROM hassle_events"))
  g.db.execute(text("DELETE FROM hassle_participants"))
  g.db.execute(text("DELETE FROM hassle_rooms"))

def clear_events(event_id=None):
  '''
  Clears hassle events. If event_id is provided, all events after (not
  including) the provided event are cleared. Otherwise, everything is
  cleared.
  '''

  if event_id:
    query = text("DELETE FROM hassle_events WHERE hassle_event_id > :e")
    g.db.execute(query, e=event_id)
  else:
    query = text("DELETE FROM hassle_events")
    g.db.execute(query)
