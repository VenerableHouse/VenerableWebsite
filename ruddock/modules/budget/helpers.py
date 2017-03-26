import flask
import sqlalchemy

def postprocess(db_rows):
  """Turns every record in a row to a string."""

  # Turns the ResultProxy into a list of dictionaries
  rows = [dict(r.items()) for r in db_rows]

  # We have to convert NUMERIC to string, because it's not JSON serializable
  for row in rows:
    for k in row:
      row[k] = str(row[k]) #TODO make it more precise in what it stringifies

  return rows

def get_fyears():
  """Gets list of all fiscal years."""
  query = sqlalchemy.text("""
    SELECT fyear_id, fyear_num
    FROM budget_fyears
    ORDER BY fyear_id DESC
    """)

  results = flask.g.db.execute(query).fetchall()

  return postprocess(results)

def get_current_fyear():
  """Returns the current fiscal year."""
  query = sqlalchemy.text("""
    SELECT fyear_id, fyear_num
    FROM budget_fyears
    WHERE CURDATE() BETWEEN start_date AND end_date
  """)

  results = flask.g.db.execute(query).fetchone()

  return postprocess([results])[0]

def get_budget_list(fyear_id):
  """Gets list of all budgets in the given year."""
  query = sqlalchemy.text("""
    SELECT budget_id, budget_name
    FROM budget_budgets
      NATURAL JOIN budget_fyears
    WHERE fyear_id = (:f)
    ORDER BY budget_name
    """)

  results = flask.g.db.execute(query, f=fyear_id).fetchall()

  return postprocess(results)

def record_expense(budget_id, date_incurred, description, amount, payment_id, payee_id):
  """Inserts a new expense into the database."""

  query = sqlalchemy.text("""
    INSERT INTO budget_expenses
      (budget_id, date_incurred, description, cost, payment_id, payee_id)
    VALUES
      ((:b_id), (:d_inc), (:descr), (:cost), (:p_id), (:payee_id))
  """)

  flask.g.db.execute(
    query,
    b_id=budget_id,
    d_inc=date_incurred,
    descr=description,
    cost=amount,
    p_id=payment_id,
    payee_id=payee_id
  )

def record_payment(account_id, type, amount, date_written, date_posted, payee_id, check_no):
  """Inserts a new payment into the database, returning its ID."""

  query = sqlalchemy.text("""
    INSERT INTO budget_payments
      (account_id, type, amount, date_written, date_posted, payee_id, check_no)
    VALUES
      ((:a_id), (:t), (:amount), (:d_writ), (:d_post), (:payee_id), (:check_no))
  """)

  result = flask.g.db.execute(
    query,
    a_id=account_id,
    t=type,
    amount=amount,
    d_writ=date_written,
    d_post=date_posted,
    payee_id=payee_id,
    check_no=check_no
  )

  return result.lastrowid

def get_account_summary():
  """Gets the status of all accounts."""
  query = sqlalchemy.text("""
    SELECT account_name,
      initial_balance - IFNULL(SUM(IF(ISNULL(date_posted), 0, amount)), 0) AS bal,
      initial_balance - IFNULL(SUM(amount), 0) AS post_bal
    FROM budget_accounts
      NATURAL LEFT JOIN budget_payments
    GROUP BY account_id
    ORDER BY account_name
    """)

  results = flask.g.db.execute(query).fetchall()

  return postprocess(results)

def get_budget_summary(fyear_id):
  """Gets the status of all budgets for the given fiscal year."""
  query = sqlalchemy.text("""
    SELECT budget_name,
      starting_amount,
      IFNULL(SUM(cost), 0) AS spent
    FROM budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL LEFT JOIN budget_expenses
    WHERE fyear_id = (:f)
    GROUP BY budget_id
    ORDER BY budget_name
    """)

  results = flask.g.db.execute(query, f=fyear_id).fetchall()

  return postprocess(results)

def get_expenses():
  """Gets list of all expenses."""
  query = sqlalchemy.text("""
    SELECT budget_name, fyear_num, date_incurred, description, cost, payee_name
    FROM budget_expenses
      NATURAL JOIN budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL LEFT JOIN budget_payees
    ORDER BY expense_id DESC
    """)

  results = flask.g.db.execute(query).fetchall()

  return postprocess(results)

def get_payments():
  """Gets list of all payments."""
  query = sqlalchemy.text("""
    SELECT account_name, type, amount, date_written, date_posted, payee_name, check_no
    FROM budget_payments
      NATURAL JOIN budget_accounts
      NATURAL LEFT JOIN budget_payees
    ORDER BY payment_id DESC
    """)

  results = flask.g.db.execute(query).fetchall()

  return postprocess(results)
  