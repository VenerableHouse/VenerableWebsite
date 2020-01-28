#!/usr/bin/env python3

import flask
from http import HTTPStatus
import sqlalchemy

from datetime import date
from decimal import Decimal

from ruddock.modules.budget.schema import (
  Base, PaymentType, Account, FiscalYear, Budget, Payee,
  Expense, Payment
)
from ruddock.resources import Permissions
from ruddock.testing import utils
from ruddock.testing.fixtures import client

def init_db():
  # Create a temporary database to use for each test, and use our
  # in-code schema to initialize the tables
  db_engine = sqlalchemy.create_engine("sqlite://", convert_unicode=True)
  Base.metadata.create_all(db_engine)

  # Then, wire it into the flask app
  app = flask.current_app
  app.engine = db_engine
  app.sessionmaker = sqlalchemy.orm.sessionmaker(bind=db_engine)
  flask.g.db = None  # we don't use it
  flask.g.session = app.sessionmaker()

  # Set up test data
  session = flask.g.session

  # Accounts
  account_bank = Account(account_name="Bank", initial_balance=0)
  account_cash = Account(account_name="Cashbox", initial_balance=20)
  session.add_all([account_bank, account_cash])

  # Fiscal Years
  fyear_2019 = FiscalYear(
    fyear_num=2019,
    start_date=date(2018, 5, 30),
    end_date=date(2019, 5, 29)
  )
  fyear_2020 = FiscalYear(
    fyear_num=2020,
    start_date=date(2019, 5, 30),
    end_date=date(2020, 5, 29)
  )
  session.add_all([fyear_2019, fyear_2020])

  # Budgets
  session.flush()  # need ids on fyears
  id_2019 = fyear_2019.fyear_id
  id_2020 = fyear_2020.fyear_id
  soc_team = Budget(budget_name="Social Team", fyear_id=id_2020, starting_amount=6000)
  ath_team = Budget(budget_name="Ath Team", fyear_id=id_2020, starting_amount=300)
  treasurer_2020 = Budget(budget_name="Treasurer", fyear_id=id_2020, starting_amount=200)
  treasurer_2019 = Budget(budget_name="Treasurer", fyear_id=id_2019, starting_amount=200)
  session.add_all([soc_team, ath_team, treasurer_2020, treasurer_2019])

  # Payees
  alice = Payee(payee_name="Alice")
  bob = Payee(payee_name="Bob")
  session.add_all([alice, bob])

  session.commit()

def login_with_permissions(client):
  # handy-dandy helper
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.BUDGET)

# -- tests --
# TODO would be nice to test render_template inputs
# https://flask.palletsprojects.com/en/1.1.x/api/#flask.render_template

def test_permissions(client):
  """Tests the /budget route."""
  url = flask.url_for("budget.route_portal")

  # try without logging in
  response = client.get(url)
  assert response.status_code == HTTPStatus.FOUND  # redirect
  assert response.location == flask.url_for("auth.login")

  # login, but without permissions
  with client.session_transaction() as session:
    utils.login(session)
  assert client.get(url).status_code == HTTPStatus.FORBIDDEN

  # try with permissions
  # Q: do sessions get cleared completely between requests? :\
  with client.session_transaction() as session:
    utils.login(session)
    utils.add_permission(session, Permissions.BUDGET)
  response = client.get(flask.url_for("budget.route_portal"))
  assert response.status_code == HTTPStatus.OK

def test_show_summary(client):
  init_db()
  login_with_permissions(client)
 
  response = client.get(flask.url_for("budget.route_summary"))
  assert b"Bank" in response.data
  assert b"Cashbox" in response.data
  assert b"$6000" in response.data
  assert b"$300" in response.data

def test_direct_expense(client):
  init_db()
  login_with_permissions(client)
  db = flask.g.session
  url_expense = flask.url_for("budget.route_submit_expense")
  url_payment = flask.url_for("budget.route_submit_unpaid")

  # Fetch some IDs from the database
  ath_team = db.query(Budget).filter(Budget.budget_name == "Ath Team").one()
  bob = db.query(Payee).filter(Payee.payee_name == "Bob").one()
  cashbox = db.query(Account).filter(Account.account_name == "Cashbox").one()

  # Check that there are no expenses
  assert not db.query(Expense).all()

  # Construct an expense from Ath team (actually an income)
  post_data = {
    "budget-id": ath_team.budget_id,
    "date-incurred": "2019-12-01",
    "description": "ath clothes",
    "cost": "-2000.01",
    # defer-payment: not-present
    "account-id": cashbox.account_id,
    "payment-type": PaymentType.CASH.value,
    "check-no": "",
  }
  assert client.post(url_expense, data=post_data).status_code == HTTPStatus.FOUND

  # Check that there's one expense and one payment
  payment = db.query(Payment).one()
  assert payment.account_id == cashbox.account_id
  assert payment.payment_type == PaymentType.CASH
  assert payment.amount == -Decimal("2000.01")
  assert payment.date_written == date(2019, 12, 1)
  assert payment.date_posted == payment.date_written
  assert payment.payee_id == None
  assert payment.check_no == None

  expense = db.query(Expense).one()
  assert expense.cost == -Decimal("2000.01")
  assert expense.payee_id == None
  assert expense.budget_id == ath_team.budget_id

  assert expense.date_incurred == payment.date_written
  assert expense.payment_id == payment.payment_id
  assert expense.cost == payment.amount
  
def test_deferred_expense(client):
  init_db()
  login_with_permissions(client)
  db = flask.g.session
  url_expense = flask.url_for("budget.route_submit_expense")
  url_payment = flask.url_for("budget.route_submit_unpaid")

  # Fetch some IDs from the database
  soc_team = db.query(Budget).filter(Budget.budget_name == "Social Team").one()
  alice = db.query(Payee).filter(Payee.payee_name == "Alice").one()
  bank = db.query(Account).filter(Account.account_name == "Bank").one()

  # Check that there are no expenses
  assert not db.query(Expense).all()

  # Construct an expense with a deferred payment to Alice
  post_data = {
    "budget-id": soc_team.budget_id,
    "date-incurred": "2020-02-14",
    "description": "valentimes!",
    "cost": "777.77",
    "defer-payment": "",
    "payee-id": alice.payee_id,
    "new-payee": "",
  }
  assert client.post(url_expense, data=post_data).status_code == HTTPStatus.FOUND

  # Check that there's one expense, and that it has the fields we expect
  expense = db.query(Expense).one()
  assert expense.cost == Decimal("777.77")
  assert expense.payee_id == alice.payee_id 
  assert expense.payment_id is None
  assert expense.budget_id == soc_team.budget_id
  assert expense.date_incurred == date(2020, 2, 14)

  # Construct the payment for it
  post_data = {
    "payee-id": alice.payee_id,
    "payment-type": PaymentType.CHECK.value,
    "account-id": bank.account_id,
    "check-no": "5205",
    "date-written": "2020-02-15",
  }
  assert client.post(url_payment, data=post_data).status_code == HTTPStatus.FOUND

  # Check that there's one payment, and that it has the fields we expect
  payment = db.query(Payment).one()
  assert payment.account_id == bank.account_id
  assert payment.payment_type == PaymentType.CHECK
  assert payment.amount == expense.cost
  assert payment.date_written == date(2020, 2, 15)
  assert payment.date_posted is None
  assert payment.payee_id == alice.payee_id
  assert payment.check_no == "5205"  # string
  
  # Check that the expense has a payment id now
  db.refresh(expense)  # to reload the object
  assert expense.payment_id == payment.payment_id


def test_new_payee(client):
  init_db()
  login_with_permissions(client)
  db = flask.g.session
  url_expense = flask.url_for("budget.route_submit_expense")
  url_payment = flask.url_for("budget.route_submit_unpaid")

  # Fetch some IDs from the database
  treasurer = db.query(Budget).filter(Budget.budget_name == "Treasurer").first()

  # Check that there are no expenses
  assert not db.query(Expense).all()
  
  # Check that no one named Charlie is a payee
  assert not db.query(Payee).filter(Payee.payee_name == "Charlie").all()

  # Construct an expense with a payment to someone new, Charlie
  post_data = {
    "budget-id": treasurer.budget_id,
    "date-incurred": "2020-02-03",
    "description": "Superb Owl",
    "cost": "44.31",
    "defer-payment": "",
    "payee-id": 0,
    "new-payee": "Charlie",
  }
  assert client.post(url_expense, data=post_data).status_code == HTTPStatus.FOUND

  # Check that there's one expense, and it has charlie as the payee
  charlie = db.query(Payee).filter(Payee.payee_name == "Charlie").one()
  expense = db.query(Expense).one()
  assert expense.payee_id == charlie.payee_id


def test_expense_grouping(client):
  init_db()
  login_with_permissions(client)
  db = flask.g.session
  url_payment = flask.url_for("budget.route_submit_unpaid")

  alice, bob = db.query(Payee).order_by(Payee.payee_name).all()
  soc_team = db.query(Budget).filter(Budget.budget_name == "Social Team").one()
  bank = db.query(Account).filter(Account.account_name == "Bank").one()

  # We're just gonna write some expenses directly to the
  # database
  expense_data = [
    (alice, 100),
    (bob, 200), 
    (alice, 300),
    (alice, 400),
    (alice, 0),
    (bob, 240)
  ]
  expenses = [
    Expense(
      budget_id = soc_team.budget_id,
      date_incurred = date(2020, 5, 1+i),
      description = f"Example Expense #{i}",
      cost = Decimal(cost),
      payment_id = None,
      payee_id = payee.payee_id
    )
    for i, (payee, cost) in enumerate(expense_data)
  ]
  db.add_all(expenses)
  db.commit()

  # Now do a payment for Alice
  post_data = {
    "payee-id": alice.payee_id,
    "payment-type": PaymentType.CHECK.value,
    "account-id": bank.account_id,
    "check-no": "1234",
    "date-written": "2020-05-25",
  }
  assert client.post(url_payment, data=post_data).status_code == HTTPStatus.FOUND

  # Grab new db data
  expenses = db.query(Expense).all()
  payment = db.query(Payment).one()
  
  # Check that all Alice's expenses have the same payment ID
  assert all(
    e.payment_id == payment.payment_id
    for e in expenses
    if e.payee_id == alice.payee_id
  )

  # Check that none of Bob's have any payment
  assert all(
    e.payment_id is None
    for e in expenses
    if e.payee_id == bob.payee_id
  )

  # Check that Alice's payment is the right amount
  assert payment.amount == sum(
    cost for payee, cost in expense_data if payee == alice
  )
