import flask
import httplib
import json
import itertools

from decimal import Decimal

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.budget import blueprint, helpers

@blueprint.route('/')
@login_required(Permissions.BUDGET)
def route_portal():
  """Displays the budget portal."""
  return flask.render_template('portal.html')

@blueprint.route('/summary')
@login_required(Permissions.BUDGET)
def route_summary():
  """Displays account and budget summaries."""
  current_fyear = helpers.get_current_fyear()
  fyears = helpers.get_fyears()
  a_summary = helpers.get_account_summary()

  return flask.render_template('summary.html',
    a_summary=a_summary,
    fyears=fyears,
    current_fyear_id=current_fyear["fyear_id"])

@blueprint.route('/expenses')
@login_required(Permissions.BUDGET)
def route_expenses():
  """Displays list of expenses."""
  expenses = helpers.get_expenses()

  return flask.render_template('expenses.html', expenses=expenses)

@blueprint.route('/payments')
@login_required(Permissions.BUDGET)
def route_payments():
  """Displays list of payments."""
  payments = helpers.get_payments()

  return flask.render_template('payments.html', payments=payments)

@blueprint.route('/add_expense')
@login_required(Permissions.BUDGET)
def route_add_expense():
  """Provides an interface for submitting an expense."""

  # TODO allow for multiple years

  # Get the lists for the dropdown menus
  current_fyear_id = helpers.get_current_fyear()["fyear_id"]
  budgets_list = helpers.get_budget_list(current_fyear_id)
  payment_types = helpers.get_payment_types()
  accounts = helpers.get_accounts()
  payees = helpers.get_payees()

  return flask.render_template('add_expense.html',
    budgets=budgets_list,
    payment_types=payment_types,
    accounts=accounts,
    payees=payees)

@blueprint.route('/add_expense/submit', methods=['POST'])
@login_required(Permissions.BUDGET)
def route_submit_expense():
  """Sends the expense to the database."""

  # Extract the form data; it's all strings
  form = flask.request.form
  budget_id = form["budget-id"]
  date_incurred = form["date-incurred"]
  amount = form["amount"]
  description = form["description"]
  payee_id = form["payee-id"]
  new_payee = form["new-payee"]
  payment_type = form["payment-type"]
  account_id = form["account-id"]
  check_no = form["check-no"]
  # except this guy, who's a boolean, because checkboxes are dumb
  defer_payment = form.get("defer-payment") is not None

  # TODO clear check number if payment isn't check? same in unpaid too

  # Server side validation
  valid = True
  if not helpers.validate_expense(budget_id, date_incurred, amount, description):
    valid = False
    flask.flash("Invalid expense.")
  if not defer_payment and not helpers.validate_payment(payment_type, account_id, check_no):
    valid = False
    flask.flash("Invalid payment.")
  if defer_payment and not helpers.validate_payee(payee_id, new_payee):
    valid = False
    flask.flash("Invalid payee.")

  # If any of the validation failed
  if not valid:
    return flask.redirect(flask.url_for("budget.route_add_expense"))

  # We use a transaction to make sure we don't submit halfway.
  transaction = flask.g.db.begin()
  try:
    # This next part depends on whether we are deferring payment or not.
    # If so, then we leave the payment ID null, cause it the corresponding payment
    # hasn't been made yet. However, we require the payee. If it's a new payee,
    # we have to insert it into the database first.
    # If not, then we need to make a new payment, and use its ID. Payee ID is not
    # needed.
    if defer_payment:
      payment_id = None
      if new_payee:
        payee_id = helpers.record_new_payee(new_payee)
    else:
      payee_id = None
      date_written = date_incurred
      date_posted = None if helpers.is_delayed_type(payment_type) else date_written
      payment_id = helpers.record_payment(account_id, payment_type, amount, date_written, date_posted, payee_id, check_no)

    # Either way, record the expense
    helpers.record_expense(budget_id, date_incurred, description, amount, payment_id, payee_id)
    transaction.commit()
    flask.flash("Expense recorded successfully!")
  except Exception:
    transaction.rollback()
    flask.flash("An unexpected error occurred. Please find an IMSS rep.")

  return flask.redirect(flask.url_for("budget.route_add_expense"))

@blueprint.route('/unpaid')
@login_required(Permissions.BUDGET)
def route_unpaid():
  """Displays unpaid expenses, and allows the user to create payments for them."""

  # Wow, I love itertools
  unpaid = helpers.get_unpaid_expenses()
  unpaid_groups = itertools.groupby(unpaid, lambda x : x["payee_id"])

  # Convert to list so we don't exhaust the iterator
  unpaid_groups = [list(expenses) for _, expenses in unpaid_groups]

  # TODO rename!
  def foo(expense_list):
    payee_id = expense_list[0]["payee_id"]
    payee_name = expense_list[0]["payee_name"]
    total = sum(Decimal(e["cost"]) for e in expense_list)
    return payee_id, payee_name, total, expense_list

  unpaid_full = [foo(expense_list) for expense_list in unpaid_groups]

  payment_types = helpers.get_payment_types()
  accounts = helpers.get_accounts()

  return flask.render_template('unpaid.html',
    payment_types=payment_types,
    accounts=accounts,
    unpaid_expenses=unpaid_full,
    today=helpers.get_today())

@blueprint.route('/unpaid/submit', methods=['POST'])
@login_required(Permissions.BUDGET)
def route_submit_unpaid():
  """Sends the payment to the database."""

  # Extract the form data; it's all strings
  form = flask.request.form
  payee_id = form["payee-id"]
  amount = form["total"]
  payment_type = form["payment-type"]
  account_id = form["account-id"]
  check_no = form["check-no"]
  date_written = form["date-written"]

  # Server side validation
  valid = True
  db_amount = helpers.get_unpaid_amount(payee_id)
  if not helpers.validate_payment(payment_type, account_id, check_no):
    valid = False
    flask.flash("Invalid payment.")
  if db_amount is None:
    valid = False
    flask.flash("This payee has no expenses to reimburse.")
  if Decimal(amount) != db_amount:
    valid = False
    flask.flash("Payment amount does not match records ({} vs. {})".format(amount, db_amount))

  # If any of the validation failed
  if not valid:
    return flask.redirect(flask.url_for("budget.route_unpaid"))

  # The date posted is the same as the date written, unless we're using a check
  date_posted = None if helpers.is_delayed_type(payment_type) else date_written

  # We use a transaction to make sure we don't submit halfway.
  transaction = flask.g.db.begin()
  try:
    payment_id = helpers.record_payment(account_id, payment_type, amount, date_written, date_posted, payee_id, check_no)
    helpers.mark_as_paid(payee_id, payment_id)
    transaction.commit()
    flask.flash("Payment recorded successfully!")
  except Exception as e:
    transaction.rollback()
    flask.flash("An unexpected error occurred. Please find an IMSS rep.")

  return flask.redirect(flask.url_for("budget.route_unpaid"))

@blueprint.route('/checks')
@login_required(Permissions.BUDGET)
def route_checks():
  """Displays all undeposited checks."""
  checks = helpers.get_unposted_payments()

  return flask.render_template('checks.html', checks=checks)

@blueprint.route('/checks/submit', methods=["POST"])
@login_required(Permissions.BUDGET)
def route_process_check():
  """Records a check as deposited."""

  # Extract form data
  form = flask.request.form
  check_no = form["check-no"]
  date_posted = form["date-posted"]
  action = form["action"]

  if action == "Post":
    flask.flash("Recording a deposited check isn't implemented yet!")
  elif action == "Void":
    flask.flash("Voiding checks isn't implemented yet!")
  else:
    flask.flash("Not a legitimate action!")

  return flask.redirect(flask.url_for("budget.route_checks"))


@blueprint.route('/ajax/budget_summary')
@login_required(Permissions.BUDGET)
def ajax_budget_summary():
  fyear_id = flask.request.args.get('fyear_id')
  if fyear_id is None:
    #TODO respond better
    results = [["Error", "Error", "Error"]]
  else:
    results = helpers.get_budget_summary(fyear_id)
    results = helpers.stringify(results)

  return json.dumps(results)