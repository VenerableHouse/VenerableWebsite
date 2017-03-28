import flask
import httplib
import json
import itertools

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.budget import blueprint, helpers

@blueprint.route('/')
def route_portal():
  """Displays the budget portal."""
  return flask.render_template('portal.html')

@blueprint.route('/summary')
def route_summary():
  """Displays account and budget summaries."""
  current_fyear = helpers.get_fyear_from_num(None)
  fyears = helpers.get_fyears()
  a_summary = helpers.get_account_summary()

  return flask.render_template('summary.html',
    a_summary=a_summary, fyears=fyears, current_fyear_id=current_fyear["fyear_id"])

@blueprint.route('/expenses')
def route_expenses():
  """Displays list of expenses."""
  expenses = helpers.get_expenses()

  return flask.render_template('expenses.html', expenses=expenses)

@blueprint.route('/payments')
def route_payments():
  """Displays list of payments."""
  payments = helpers.get_payments()

  return flask.render_template('payments.html', payments=payments)

@blueprint.route('/add_expense')
def route_add_expense():
  """Provides an interface for submitting an expense."""

  # TODO allow for multiple years

  # Get the lists for the dropdown menus
  budgets_list = helpers.get_budget_list(2) #TODO don't leave this
  payment_types = helpers.get_payment_types()
  accounts = helpers.get_accounts()
  payees = helpers.get_payees()

  return flask.render_template('add_expense.html',
    budgets=budgets_list,
    payment_types=payment_types,
    accounts=accounts,
    payees=payees)

@blueprint.route('/add_expense/submit', methods=['POST'])
def route_submit_expense():
  """Sends the expense to the database."""
  form = flask.request.form

  # Extract the form data
  budget_id = form["budget-id"]
  date_incurred = form["date-incurred"]
  amount = form["amount"]
  description = form["description"]
  defer_payment = form.get("defer-payment") is not None # checkboxes are dumb
  payee_id = form["payee-id"]
  new_payee = form["new-payee"]
  payment_type = form["payment-type"]
  account_id = form["account-id"]
  check_no = form["check-no"]

  # TODO do some server-side validation too!

  # This next part depends on whether we are deferring payment or not.
  # If so, then we leave the payment ID null, cause it the corresponding payment
  # hasn't been made yet. However, we require the payee. If it's a new payee,
  # we have to insert it into the database first.
  # If not, then we need to make a new payment, and use its ID. Payee ID is not
  # needed.
  # TODO transaction stuff?
  if defer_payment:
    payment_id = None
    if new_payee:
      payee_id = helpers.record_new_payee(new_payee)
  else:
    payee_id = None
    payment_id = helpers.record_payment(account_id, payment_type, amount, date_incurred, date_incurred, None, check_no)

  # Either way, record the expense and refresh the page
  helpers.record_expense(budget_id, date_incurred, description, amount, payment_id, payee_id)
  return flask.redirect(flask.url_for("budget.route_add_expense"))

@blueprint.route('/unpaid')
def route_unpaid():
  """Displays unpaid expenses, and allows the user to create payments for them."""

  # Wow, I love itertools
  unpaid = helpers.get_unpaid_expenses()
  unpaid_groups = itertools.groupby(unpaid, lambda x : x["payee_name"])

  payment_types = helpers.get_payment_types()
  accounts = helpers.get_accounts()

  return flask.render_template('unpaid.html',
    payment_types=payment_types,
    accounts=accounts,
    unpaid_groups=unpaid_groups)


@blueprint.route('/ajax/budget_summary')
def ajax_budget_summary():
  fyear_id = flask.request.args.get('fyear_id')
  if fyear_id is None:
    #TODO respond better
    results = [["Error", "Error", "Error"]]
  else:
    results = helpers.get_budget_summary(fyear_id)

  return json.dumps(results)










