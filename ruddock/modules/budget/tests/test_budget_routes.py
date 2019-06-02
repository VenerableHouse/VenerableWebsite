import flask
import http.client

from datetime import date
from decimal import Decimal
from ruddock.modules.budget import helpers, routes
from ruddock.testing import utils
from ruddock.resources import Permissions

def assert_subdict(left, right):
  """Returns True if left is a strict subset of right."""
  for k, v in left.items():
    assert right[k] == v, "Key {} didn't match".format(k)


def test_expense_direct(client, app):
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.ADMIN)

  # Check that view page is okay
  response = client.get(flask.url_for('budget.route_expenses'))
  assert response.status_code == http.client.OK

  # Check that add page is okay
  response = client.get(flask.url_for('budget.route_add_expense'))
  assert response.status_code == http.client.OK

  # Add an expense, directly from account
  post_params = {
    "budget_id": "1",
    "date_incurred": "2019-06-02",
    "amount": "10.00", 
    "description": "mystery items",
    "payee_id": "",
    "new_payee": "",
    "payment_type": str(helpers.PaymentType.DEBIT.value),
    "account_id": "1",
    "check_no": "",
    "defer_payment": None,  # i.e., False
  }
  response = client.post(
    flask.url_for('budget.route_submit_expense'),
    data=post_params,
    follow_redirects=True
  )
  assert b"Expense recorded successfully!" in response.data

  # Check that the expense showed up
  with app.app_context():
      flask.g.db = app.engine.connect()
      expenses = helpers.get_expenses()
      payments = helpers.get_payments()
      payees = helpers.get_payees()

  assert len(expenses) == 1
  assert len(payments) == 1
  assert len(payees) == 0

  expected_expense = {
    "expense_id": 1,
    "budget_id": 1,
    "date_incurred": date(2019, 6, 2),
    "description": "mystery items",
    "cost": Decimal("10.00"),
    "payment_id": 1,
    "payee_id": None,
  }

  expected_payment = {
    "payment_id": 1,
    "account_id": 1,
    "payment_type": helpers.PaymentType.DEBIT.value,
    "amount": Decimal("10.00"),
    "date_written": date(2019, 6, 2),
    "date_posted": date(2019, 6, 2),
    "payee_id": None,
    "check_no": "",
  }

  assert_subdict(expected_expense, dict(expenses[0]))
  assert_subdict(expected_payment, dict(payments[0]))

  # Check that we can view the expense page
  response = client.get(flask.url_for('budget.route_show_expense', expense_id=1))
  assert response.status_code == http.client.OK

def test_expense_delayed(client, app):
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.ADMIN)

  # Add an expense, but delay the payment
  post_params = {
    "budget_id": "2",
    "date_incurred": "2019-09-21",
    "amount": "20.00",
    "description": "beverages",
    "payee_id": "",
    "new_payee": "Joe Public",
    "payment_type": str(helpers.PaymentType.CHECK.value),
    "account_id": "1",
    "check_no": "1337",
    "defer_payment": "on",  # i.e., True
  }
  response = client.post(
    flask.url_for('budget.route_submit_expense'),
    data=post_params,
    follow_redirects=True
  )
  assert b"Expense recorded successfully!" in response.data

  # Check that the expense showed up
  with app.app_context():
      flask.g.db = app.engine.connect()
      expenses = helpers.get_expenses()
      payments = helpers.get_payments()
      payees = helpers.get_payees()

  assert len(expenses) == 1
  assert len(payments) == 0
  assert len(payees) == 1

  expected_expense = {
    "expense_id": 1,
    "budget_id": 2,
    "date_incurred": date(2019, 9, 21),
    "description": "beverages",
    "cost": Decimal("20.00"),
    "payment_id": None,
    "payee_id": 1,
  }

  expected_payee = {
    "payee_id": 1,
    "payee_name": "Joe Public",
  }

  assert_subdict(expected_expense, expenses[0])
  assert_subdict(expected_payee, payees[0])