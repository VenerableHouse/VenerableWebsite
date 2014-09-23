from sqlalchemy import text

def get_members(connection):
  ''' Gets all current members (potential hassle participants). '''

  query = text("""
    SELECT user_id, CONCAT(fname, ' ', lname) AS name, grad_year,
      membership_desc, user_id IN (
        SELECT user_id FROM hassle_participants
      ) AS participating
    FROM members_current NATURAL JOIN membership_types
    ORDER BY membership_type, grad_year, name
    """)
  return connection.execute(query)

def set_participants(participants, connection):
  ''' Sets hassle participants. '''

  # Delete old participants.
  delete_query = text("DELETE FROM hassle_participants")
  connection.execute(delete_query)

  # Insert new participants.
  insert_query = text("INSERT INTO hassle_participants (user_id) VALUES (:p)")
  for participant in participants:
    connection.execute(insert_query, p=participant)
