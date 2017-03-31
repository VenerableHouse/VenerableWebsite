import flask
import sqlalchemy
import enum

from datetime import datetime #ugh
from decimal import Decimal

# Enum for payment types
class PaymentType(enum.Enum):
  CASH = "Cash"
  CHECK = "Check"
  DEBIT = "Debit"
  ONLINE = "Online"
  TRANSFER = "Transfer"
  OTHER = "Other"

def stringify(db_rows):
  """Changes all columns to strings.
     This is especially useful when working with NUMERIC, because
     JSON refuses to serialize Decimal objects.
     This has the side effect of replacing the RowProxy objects with
     dictionaries, but hopefully no method should notice... :/ """

  # maybe have it detect numeric columns?

  rows = [dict(r.items()) for r in db_rows]

  for r in rows:
    for k in r:
      r[k] = str(r[k])

  return rows

def get_payment_types():
  return [x.value for x in PaymentType]

def is_delayed_type(val):
  """Returns true if this is a kind of payment that doesn't take effect immediately.
     In other words, is this a check?"""
  return val == PaymentType.CHECK.value

def get_fyears():
  """Gets list of all fiscal years."""
  query = sqlalchemy.text("""
    SELECT fyear_id, fyear_num
    FROM budget_fyears
    ORDER BY fyear_id DESC
    """)

  return flask.g.db.execute(query).fetchall()

def get_fyear_from_num(fyear_num):
  """Looks up the record for the given year.
     If fyear_num is None, then this returns the current year.
     If no matching row is found, returns None."""

  if fyear_num is None:
    query = sqlalchemy.text("""
      SELECT fyear_id, fyear_num
      FROM budget_fyears
      WHERE CURDATE() BETWEEN start_date AND end_date
    """)
    rp = flask.g.db.execute(query)
  else:
    query = sqlalchemy.text("""
      SELECT fyear_id, fyear_num
      FROM budget_fyears
      WHERE fyear_num = (:f)
    """)
    rp = flask.g.db.execute(query, f=fyear_num)

  return rp.first()

def get_budget_list(fyear_id):
  """Gets list of all budgets in the given year."""
  query = sqlalchemy.text("""
    SELECT budget_id, budget_name
    FROM budget_budgets
      NATURAL JOIN budget_fyears
    WHERE fyear_id = (:f)
    ORDER BY budget_name
    """)

  return flask.g.db.execute(query, f=fyear_id).fetchall()

def get_expenses():
  """Gets list of all expenses."""
  query = sqlalchemy.text("""
    SELECT expense_id, budget_name, fyear_num, date_incurred, description, cost, payee_name, payment_id
    FROM budget_expenses
      NATURAL JOIN budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL LEFT JOIN budget_payees
    ORDER BY expense_id DESC
    """)

  return flask.g.db.execute(query).fetchall()

def get_payments():
  """Gets list of all payments."""
  query = sqlalchemy.text("""
    SELECT payment_id, account_name, type, amount, date_written, date_posted, payee_name, check_no
    FROM budget_payments
      NATURAL JOIN budget_accounts
      NATURAL LEFT JOIN budget_payees
    ORDER BY payment_id DESC
    """)

  return flask.g.db.execute(query).fetchall()

def get_accounts():
  """Gets list of all accounts."""
  query = sqlalchemy.text("""
    SELECT account_id, account_name
    FROM budget_accounts
    ORDER BY account_name
    """)

  return flask.g.db.execute(query).fetchall()

def get_payees():
  """Gets list of all payees."""
  query = sqlalchemy.text("""
    SELECT payee_id, payee_name
    FROM budget_payees
    ORDER BY payee_name
    """)

  return flask.g.db.execute(query).fetchall()

def get_account_summary():
  """Gets the status of all accounts."""
  query = sqlalchemy.text("""
    SELECT account_name,
      initial_balance - IFNULL(SUM(IF(ISNULL(date_posted), 0, amount)), 0) AS bal
    FROM budget_accounts
      NATURAL LEFT JOIN budget_payments
    GROUP BY account_id
    ORDER BY account_name
    """)

  return flask.g.db.execute(query).fetchall()

def get_budget_summary(fyear_id):
  """Gets the status of all budgets for the given fiscal year."""
  query = sqlalchemy.text("""
    SELECT *,
      starting_amount - spent AS remaining
    FROM (
      SELECT budget_name,
        starting_amount,
        IFNULL(SUM(cost), 0) AS spent
      FROM budget_budgets
        NATURAL JOIN budget_fyears
        NATURAL LEFT JOIN budget_expenses
      WHERE fyear_id = (:f)
      GROUP BY budget_id
      ORDER BY budget_name
    ) AS t
    """)

  return flask.g.db.execute(query, f=fyear_id).fetchall()

def get_unpaid_expenses():
  """Gets all expenses without a corresponding payment."""
  query = sqlalchemy.text("""
    SELECT payee_id, payee_name, budget_name, fyear_num, date_incurred, description, cost
    FROM budget_expenses
      NATURAL JOIN budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL JOIN budget_payees
    WHERE ISNULL(payment_id)
    ORDER BY payee_name
  """)

  return flask.g.db.execute(query).fetchall()

def get_unpaid_amount(payee_id):
  """Returns the amount owed to the given payee, or None if they have no
     outstanding expenses."""
  query = sqlalchemy.text("""
    SELECT SUM(cost) AS total
    FROM budget_expenses
    WHERE payee_id = (:p) AND ISNULL(payment_id)
    GROUP BY NULL
  """)

  result = flask.g.db.execute(query, p=payee_id).first()
  total = result["total"]

  return total

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

def record_new_payee(payee_name):
  """Inserts a new payee into the database, returning its ID."""
  query = sqlalchemy.text("""
    INSERT INTO budget_payees (payee_name)
    VALUES (:p)
  """)

  result = flask.g.db.execute(query, p=payee_name)
  return result.lastrowid

def mark_as_paid(payee_id, payment_id):
  """Assigns the given payment id to all expenses from the given payee."""
  query = sqlalchemy.text("""
    UPDATE budget_expenses
    SET payment_id = (:payment)
    WHERE payee_id = (:payee)
  """)

  flask.g.db.execute(query, payment=payment_id, payee=payee_id)


# these should move to somewhere more global...
def is_integer(x):
  try:
    y = int(x)
  except ValueError:
    return False
  return True

def is_date(x):
  try:
    y = datetime.strptime(x , '%Y-%m-%d')
  except ValueError:
    return False
  return True

def is_currency(x):
  try:
    y = Decimal(x)
  except ValueError:
    return False
  return True

#TODO length contraints?
def validate_expense(budget_id, date_incurred, amount, description):
  return (is_integer(budget_id) and is_date(date_incurred) and
    is_currency(amount) and len(description) > 0)

def validate_payment(payment_type, account_id, check_no):
  valid_payment_type = payment_type in get_payment_types()
  return (valid_payment_type and is_integer(account_id) and
    (payment_type != PaymentType.CHECK.value or is_integer(check_no)))

def validate_payee(payee_id, payee_name):
  well_formed = is_integer(payee_id)
  existing_payee = payee_id != 0
  new_payee = len(payee_name) > 0
  return well_formed and (existing_payee != new_payee)