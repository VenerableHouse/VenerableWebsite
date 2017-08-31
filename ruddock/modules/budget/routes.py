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
  return flask.render_template('budget_portal.html')

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
  valid_expense = helpers.validate_expense(budget_id, date_incurred, amount,
      description)
  valid_payment = defer_payment or helpers.validate_payment(payment_type,
      account_id, check_no)
  valid_payee = not defer_payment or helpers.validate_payee(payee_id, new_payee)

  errs = helpers.test_predicates(
    (valid_expense, True,              "Invalid expense.")
    (valid_payment, not defer_payment, "Invalid payment.")
    (valid_payee,   defer_payment,     "Invalid payee."  )
  )

  for e in errs:
    flask.flash(e)

  if errs:
    return flask.redirect(flask.url_for("budget.route_add_expense"))

  # We use a transaction to make sure we don't submit halfway.
  transaction = flask.g.db.begin()
  try:
    # This next part depends on whether we are deferring payment or not.
    # If so, then we leave the payment ID null, cause it the corresponding
    # payment hasn't been made yet. However, we require the payee. If it's a new
    # payee, we have to insert it into the database first.
    # If not, then we need to make a new payment, and use its ID. Payee ID is
    # not needed.
    if defer_payment:
      payment_id = None
      if new_payee:
        payee_id = helpers.record_new_payee(new_payee)
    else:
      payee_id = None
      date_written = date_incurred
      date_posted = None if helpers.is_delayed_type(payment_type) \
          else date_written
      payment_id = helpers.record_payment(account_id, payment_type, amount,
          date_written, date_posted, payee_id, check_no)

    # Either way, record the expense
    helpers.record_expense(budget_id, date_incurred, description, amount,
        payment_id, payee_id)

    transaction.commit()
    flask.flash("Expense recorded successfully!")
  except Exception:
    transaction.rollback()
    flask.flash("An unexpected error occurred. Please find an IMSS rep.")

  return flask.redirect(flask.url_for("budget.route_add_expense"))

@blueprint.route('/unpaid')
@login_required(Permissions.BUDGET)
def route_unpaid():
  """Displays unpaid expenses, and allows the user to create payments for them.
  """

  # Get all unpaid expenses and group them by the payee
  # Wow, I love itertools
  unpaid = helpers.get_unpaid_expenses()
  unpaid_groups = itertools.groupby(unpaid, lambda x : x["payee_id"])

  # Convert to list so we don't exhaust the iterator
  unpaid_groups = [list(expenses) for _, expenses in unpaid_groups]

  # Given a group of expenses, sums the costs and returns a tuple of ID, name,
  # total, and the original group
  def compute_totals(expenses):
    payee_id = expenses[0]["payee_id"]
    payee_name = expenses[0]["payee_name"]
    total = sum(Decimal(e["cost"]) for e in expenses)
    return payee_id, payee_name, total, expenses

  unpaid_full = [compute_totals(expenses) for expenses in unpaid_groups]

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
  db_amount = helpers.get_unpaid_amount(payee_id)
  valid_payment = helpers.validate_payment(payment_type, account_id, check_no)
  has_expenses = (db_amount is not None)
  amounts_match = (Decimal(amount) != db_amount)

  errs = helpers.test_predicates(
    (valid_payment, True, "Invalid payment.")
    (has_expenses,  True, "This payee has no expenses to reimburse.")
    (amounts_match, True,
        "Payment amount does not match records ({} vs. {})".format(
            amount, db_amount))
  )

  for e in errs:
    flask.flash(e)

  if errs:
    return flask.redirect(flask.url_for("budget.route_unpaid"))

  # We use a transaction to make sure we don't submit halfway.
  transaction = flask.g.db.begin()
  try:
    # The date posted is the same as the date written unless we're using a check
    date_posted = None if helpers.is_delayed_type(payment_type) \
        else date_written
    payment_id = helpers.record_payment(account_id, payment_type, amount,
        date_written, date_posted, payee_id, check_no)
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

@blueprint.route('/checks/submit', methods=['POST'])
@login_required(Permissions.BUDGET)
def route_process_check():
  """Records a check as deposited."""

  # Extract form data
  form = flask.request.form
  payment_id = form["payment-id"]
  date_posted = form["date-posted"]
  action = form["action"]

  # Server side validation
  unposted_ids = [str(x["payment_id"]) for x in helpers.get_unposted_payments()]

  errs = helpers.test_predicates(
    (payment_id in unposted_ids, True,             "Not a valid payment!")
    (date_posted == "",          action == "Post", "No date entered!"    )
  )

  for e in errs:
    flask.flash(e)

  # If any of the validation failed
  if errs:
    return flask.redirect(flask.url_for("budget.route_checks"))

  # Decide what to do
  if action == "Post":
    helpers.post_payment(payment_id, date_posted)
    flask.flash("Payment successfully posted!")
  elif action == "Void":
    helpers.void_payment(payment_id)
    flask.flash("Payment successfully voided!")
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