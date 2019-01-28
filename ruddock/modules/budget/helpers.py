import flask
import sqlalchemy
from enum import Enum

import ruddock.validation_utils as vu

class PaymentType(Enum):
  CASH = 1
  CHECK = 2
  DEBIT = 3
  ONLINE = 4
  TRANSFER = 5
  OTHER = 6
  INCOME = 7

  @classmethod
  def has_value(cls, value):
    try:
      PaymentType(value)
      return True
    except ValueError:
      return False

  @classmethod
  def get_all(cls):
    return {x.value: x.name.title() for x in PaymentType}


# ==== SQL QUERIES ====

def select_fyear_info(fyear_num):
  """
  Looks up the record for the given year, returning the record, and a boolean
  indicating if it is the current year.

  If None is given, returns the current year.
  """

  current = get_current_fyear()

  if fyear_num is None:
    return current, True

  fyear_num = int(fyear_num)
  record = [r for r in get_fyears() if r["fyear_num"] == fyear_num][0]

  return record, current["fyear_num"] == fyear_num


def get_current_fyear():
  """
  Looks up the record for the current year.
  If no matching row is found, returns None.
  """

  query = sqlalchemy.text("""
    SELECT fyear_id, fyear_num
    FROM budget_fyears
    WHERE CURDATE() BETWEEN start_date AND end_date
  """)
  rp = flask.g.db.execute(query)

  return rp.first()


def get_expenses():
  """Gets list of all expenses."""
  query = sqlalchemy.text("""
    SELECT expense_id, budget_id, budget_name, fyear_num, date_incurred,
        description, cost, payee_name, payment_id
    FROM budget_expenses
      NATURAL JOIN budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL LEFT JOIN budget_payees
    ORDER BY expense_id DESC
    """)

  return flask.g.db.execute(query).fetchall()

def get_expense(expense_id):
  """Gets a particular expense, or None"""
  query = sqlalchemy.text("""
    SELECT expense_id, budget_id, budget_name, fyear_id, fyear_num,
        date_incurred, description, cost, payee_name, payment_id
    FROM budget_expenses
      NATURAL JOIN budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL LEFT JOIN budget_payees
    WHERE expense_id = (:e)
    """)

  return flask.g.db.execute(query, e=expense_id).first()


def get_payments():
  """Gets list of all payments."""
  query = sqlalchemy.text("""
    SELECT payment_id, account_name, payment_type, amount, date_written,
        date_posted, payee_name, check_no
    FROM budget_payments
      NATURAL JOIN budget_accounts
      NATURAL LEFT JOIN budget_payees
    ORDER BY payment_id DESC
    """)

  return flask.g.db.execute(query).fetchall()


def get_transactions():
  """Gets list of all expenses + payments."""
  # We need the USING clause because there's a payee_id in both tables
  # TODO change the column in one of the tables to a different name
  query = sqlalchemy.text("""
    SELECT *
    FROM budget_expenses LEFT JOIN budget_payments USING(payment_id)
      NATURAL JOIN budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL LEFT JOIN budget_accounts
      LEFT JOIN budget_payees ON budget_expenses.payee_id = budget_payees.payee_id
    ORDER BY expense_id DESC
    """)

  return flask.g.db.execute(query).fetchall()


def get_fyears():
  """Gets list of all available fiscal years."""
  query = sqlalchemy.text("""
    SELECT fyear_id, fyear_num
    FROM budget_fyears
    ORDER BY fyear_id DESC
    """)

  return flask.g.db.execute(query).fetchall()


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
      initial_balance - IFNULL(SUM(amount), 0) AS bal
    FROM budget_accounts
      NATURAL LEFT JOIN (
        SELECT account_id, amount
        FROM budget_payments
        WHERE date_posted IS NOT NULL) AS t
    GROUP BY account_id
    ORDER BY account_name
    """)
  # you can't pull the WHERE outside the join, because if no payments
  # have posted, the account won't show up

  return flask.g.db.execute(query).fetchall()


def get_budget_summary(fyear_id):
  """Gets the status of all budgets for the given fiscal year."""
  query = sqlalchemy.text("""
    SELECT *,
      starting_amount - spent AS remaining
    FROM (
      SELECT budget_name, starting_amount, IFNULL(SUM(cost), 0) AS spent
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

  # A list of all unpaid expenses
  list_query = sqlalchemy.text("""
    SELECT expense_id, budget_name, fyear_num, date_incurred, description,
      cost, payee_id
    FROM budget_expenses
      NATURAL JOIN budget_budgets
      NATURAL JOIN budget_fyears
      NATURAL JOIN budget_payees
    WHERE ISNULL(payment_id)
    ORDER BY payee_name, expense_id
  """)

  # A list of payees and the total amount they're owed
  total_query = sqlalchemy.text("""
    SELECT payee_id, payee_name, SUM(cost) AS total
    FROM budget_payees
      NATURAL JOIN budget_expenses
    WHERE ISNULL(payment_id)
    GROUP BY payee_id
    ORDER BY payee_name
  """)

  unpaid_expenses = flask.g.db.execute(list_query).fetchall()
  unpaid_payees = flask.g.db.execute(total_query).fetchall()

  def make_tuple(payee):
    payee_id = payee['payee_id']
    payee_name = payee['payee_name']
    total = payee['total']
    expenses = [r for r in unpaid_expenses if r['payee_id'] == payee_id]

    return payee_id, payee_name, total, expenses

  # We return a list of payees w/ addl data attached
  return list(map(make_tuple, unpaid_payees))


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


def get_unposted_payments():
  """Returns all payments that haven't been posted."""
  query = sqlalchemy.text("""
    SELECT payment_id, account_name, payment_type, amount, date_written,
      date_posted, payee_name, check_no
    FROM budget_payments
      NATURAL JOIN budget_accounts
      NATURAL JOIN budget_payees
    WHERE ISNULL(date_posted)
    ORDER BY payment_id DESC
  """)

  return flask.g.db.execute(query)

# ==== SQL UPDATES ====

def record_expense(budget_id, date_incurred, description, amount, payment_id,
    payee_id):
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


def record_payment(account_id, payment_type, amount, date_written, date_posted,
    payee_id, check_no):
  """Inserts a new payment into the database, returning its ID."""

  query = sqlalchemy.text("""
    INSERT INTO budget_payments
      (account_id, payment_type, amount, date_written, date_posted, payee_id,
      check_no)
    VALUES
      ((:a_id), (:t), (:amount), (:d_writ), (:d_post), (:payee_id), (:check_no))
  """)

  result = flask.g.db.execute(
    query,
    a_id=account_id,
    t=payment_type,
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
  """
  Assigns the given payment id to all unpaid expenses from the given payee.
  """
  query = sqlalchemy.text("""
    UPDATE budget_expenses
    SET payment_id = (:payment)
    WHERE ISNULL(payment_id) AND payee_id = (:payee)
  """)

  flask.g.db.execute(query, payment=payment_id, payee=payee_id)


def post_payment(payment_id, date_posted):
  """Marks the given payment as posted, with the given date."""
  query = sqlalchemy.text("""
    UPDATE budget_payments
    SET date_posted = (:dp)
    WHERE payment_id = (:pi)
  """)

  flask.g.db.execute(query, dp=date_posted, pi=payment_id)


def void_payment(payment_id):
  """Marks the given payment as posted, with the given date."""
  transaction = flask.g.db.begin()
  try:
    # Wipe payment ID from expenses
    query = sqlalchemy.text("""
      UPDATE budget_expenses
      SET payment_id = NULL
      WHERE payment_id = (:pi)
    """)

    # Delete payment
    query2 = sqlalchemy.text("""
      DELETE FROM budget_payments
      WHERE payment_id = (:pi)
    """)

    flask.g.db.execute(query, pi=payment_id)
    flask.g.db.execute(query2, pi=payment_id)
    transaction.commit()

  except Exception:
    transaction.rollback()
    flask.flash("An unexpected error occurred. Please find an IMSS rep.")

# ==== VALIDATION ====

def test_predicates(triplets, flash=True):
  """Makes validation methods more readable."""
  errs = [err for pred, guard, err in triplets if guard and not pred]

  if flash:
    for e in errs:
      flask.flash(e)

  return errs


def validate_expense(budget_id, date_incurred, amount, description):
  valid = True
  valid &= vu.validate_integer(budget_id, flash_errors=False)
  valid &= vu.validate_date(date_incurred, flash_errors=False)
  valid &= vu.validate_currency(amount, flash_errors=False)
  valid &= len(description) > 0

  return valid


def validate_payment(payment_type, account_id, check_no):
  valid = True
  valid &= vu.validate_integer(payment_type, flash_errors=False) and \
      PaymentType.has_value(int(payment_type))
  valid &= vu.validate_integer(account_id, flash_errors=False)
  if payment_type == PaymentType.CHECK:
    valid &= vu.validate_integer(check_no, flash_errors=False)

  return valid


def validate_payee(payee_id, payee_name):
  # TODO also check that the new payee isn't actually an old one...
  # This one's a bit unusual, we want a valid old payee XOR a valid new one
  existing_payee = vu.validate_integer(payee_id, flash_errors=False)
  new_payee = len(payee_name) > 0
  return (existing_payee != new_payee)