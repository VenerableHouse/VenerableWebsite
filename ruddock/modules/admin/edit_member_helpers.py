import flask
import sqlalchemy

def delete_member(user_id):
    """Deletes a member"""
    query = sqlalchemy.text("""
      DELETE FROM members
      WHERE user_id = :a
      """)
    try:
        flask.g.db.execute(query, a=user_id)
        return True
    except Exception:
        return False



