import flask
import json

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.budget import blueprint, helpers

@blueprint.route('/')
def portal():
  """Displays the budget portal."""
  return flask.render_template('portal.html')

@blueprint.route('/summary')
def show_summary():
  """Displays account and budget summaries."""
  current_fyear = helpers.get_current_fyear()

  fyears = helpers.get_fyears()
  a_summary = helpers.get_account_summary()

  return flask.render_template('summary.html',
    a_summary=a_summary, fyears=fyears, current_fyear_id=current_fyear["fyear_id"])

@blueprint.route('/add_expense')
def add_expense():
  """Provides an interface for submitting an expense."""
  # Check what year was provided
  fyear_num = flask.request.args.get('fyear')

  # If no year was provided, get the current year
  if fyear_num is None:
    fyear = helpers.get_current_fyear()
    fyear_id = fyear["fyear_id"]
    fyear_num = fyear["fyear_num"]
  else:
    # Look up the id of that fiscal year
    fyears = helpers.get_fyears()
    pred = lambda r : r["fyear_num"] == fyear_num
    fyear_id = next((r["fyear_id"] for r in fyears if pred(r)), None)
  
  # If there is no such year
  if fyear_id is None:
    #TODO do something more informative!
    flask.abort(404)

  # Get the list of budgets for that year
  budgets_list = helpers.get_budget_list(fyear_id)

  return flask.render_template('add_expense.html',
    fyear=fyear_num,
    budgets=budgets_list)

@blueprint.route('/add_expense/submit', methods=['POST'])
def submit_expense():
  """Sends the expense to the database."""
  form = flask.request.form

  # Extract the expense 
  budget_id = form["budget_id"]
  date_incurred = form["date_incurred"]
  amount = form["amount"]
  description = form["description"]
  # checkboxes are dumb
  defer_payment = form.get("defer_payment") is not None

  # Are we deferring payment?
  if defer_payment:
    # If so, then we leave the payment_id field blank, but save the payee for bookkeeping
    payment_id = None
    payee_id = 1
  else:
    # If not, we need to submit a payment, so we can use it as our payment_id
    # We have no need for the payee_id field though as well
    # TODO transaction stuff?
    payment_type = form["payment_type"]
    account_id = form["account_id"]
    check_no = form["check_no"]
    payment_id = helpers.record_payment(account_id, payment_type, amount, date_incurred, date_incurred, None, check_no)

    payee_id = None

  # Record the expense
  helpers.record_expense(budget_id, date_incurred, description, amount, payment_id, payee_id)

  # Return the user to the same page, same fiscal year
  fyear = flask.request.args.get("fyear")
  return flask.redirect(flask.url_for("budget.add_expense", fyear=fyear))

@blueprint.route('/expenses')
def show_expenses():
  """Displays list of expenses."""
  expenses = helpers.get_expenses()

  return flask.render_template('expenses.html', expenses=expenses)

@blueprint.route('/payments')
def show_payments():
  """Displays list of payments."""
  payments = helpers.get_payments()

  return flask.render_template('payments.html', payments=payments)


@blueprint.route('/ajax/budget_summary')
def ajax_get_budget_summary():
  fyear_id = flask.request.args.get('fyear_id')
  if fyear_id is None:
    #TODO respond better
    results = [["Error", "Error", "Error"]]
  else:
    results = helpers.get_budget_summary(fyear_id)

  return json.dumps(results)










