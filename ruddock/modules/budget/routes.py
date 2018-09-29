import flask

from datetime import datetime  # ugh

from ruddock.resources import Permissions
from ruddock.decorators import login_required, get_args_from_form
from ruddock.modules.budget import blueprint, helpers
from .helpers import PaymentType


@blueprint.route('/')
@login_required(Permissions.BUDGET)
def route_portal():
  """Displays the budget portal."""
  return flask.render_template('budget_portal.html')


@blueprint.route('/summary')
@login_required(Permissions.BUDGET)
def route_summary():
  """Displays account and budget summaries."""

  # Get the info we need
  fyear_dict = {r["fyear_num"]: r["fyear_id"] for r in helpers.get_fyears()}
  current_fyear = helpers.get_current_fyear()["fyear_num"]

  # Check what year the user gave, falling to the current year by default
  fyear_num = int(flask.request.args.get("fyear", current_fyear))
  fyear_id = fyear_dict[fyear_num]

  # Decide how to display the year
  if fyear_num == current_fyear:
    fyear_str = "{} (Current)".format(fyear_num)
  else:
    fyear_str = str(fyear_num)

  a_summary = helpers.get_account_summary()
  b_summary = helpers.get_budget_summary(fyear_id)

  fyear_options = [
    (num, fyear_dict[num])
    for num in reversed(sorted(fyear_dict.keys()))
  ]

  return flask.render_template('summary.html',
    a_summary=a_summary,
    b_summary=b_summary,
    fyear_num=fyear_str,
    fyear_options=fyear_options)


@blueprint.route('/expenses')
@login_required(Permissions.BUDGET)
def route_expenses():
  """Displays list of expenses."""
  return flask.render_template('expenses.html',
    expenses=helpers.get_transactions(),
    ptypes=helpers.get_payment_types())


@blueprint.route('/payments')
@login_required(Permissions.BUDGET)
def route_payments():
  """Displays list of payments."""
  return flask.render_template('payments.html',
    payments=helpers.get_payments(),
    ptypes=helpers.get_payment_types())


@blueprint.route('/add_expense')
@login_required(Permissions.BUDGET)
def route_add_expense():
  """Provides an interface for submitting an expense."""

  # TODO allow for multiple years

  # Get the lists for the dropdown menus
  current_fyear = helpers.get_current_fyear()
  budgets_list = helpers.get_budget_list(current_fyear["fyear_id"])
  payment_types = helpers.get_payment_types()
  accounts = helpers.get_accounts()
  payees = helpers.get_payees()

  return flask.render_template('add_expense.html',
    fyear_num=current_fyear["fyear_num"],
    budgets=budgets_list,
    payment_types=payment_types,
    accounts=accounts,
    payees=payees)


@blueprint.route('/add_expense/submit', methods=['POST'])
@login_required(Permissions.BUDGET)
@get_args_from_form()
def route_submit_expense(budget_id, date_incurred, amount, description,
    payee_id, new_payee, payment_type, account_id, check_no, defer_payment):
  """Sends the expense to the database."""

  # Checkboxes aren't sent as bools... :(
  defer_payment = defer_payment is not None

  # Server side validation
  valid_expense = helpers.validate_expense(budget_id, date_incurred, amount,
      description)
  valid_payment = helpers.validate_payment(payment_type,
      account_id, check_no)
  valid_payee = helpers.validate_payee(payee_id, new_payee)

  errs = helpers.test_predicates((
    (valid_expense, True,              "Invalid expense."),
    (valid_payment, not defer_payment, "Invalid payment."),
    (valid_payee,   defer_payment,     "Invalid payee."  )
  ))

  if errs:
    return flask.redirect(flask.url_for("budget.route_add_expense"))


  transaction = flask.g.db.begin()
  try:
    # This next part depends on whether we are deferring payment or not.
    # If so, then we leave the payment ID null, cause it the corresponding
    # payment hasn't been made yet. However, we require the payee. If it's a new
    # payee, we have to insert it into the database first.
    # If not, then we need to make a new payment, and use its ID. Payee ID is
    # not needed.
    if defer_payment:
      payee_id = payee_id or helpers.record_new_payee(new_payee)
      payment_id = None
    else:
      date_written = date_incurred  # non-deferred payments are instant
      date_posted = None if payment_type == PaymentType.CHECK else date_written

      payee_id = None
      payment_id = helpers.record_payment(
        account_id, payment_type, amount, date_written, date_posted,
        payee_id, check_no)

    # Either way, record the expense
    helpers.record_expense(
        budget_id, date_incurred, description, amount, payment_id, payee_id)
    transaction.commit()
    flask.flash("Expense recorded successfully!")

  except Exception:
      transaction.rollback()
      flask.flash("An unexpected error occurred. Please find an IMSS rep.")

  return flask.redirect(flask.url_for("budget.route_add_expense"))


@blueprint.route('/unpaid')
@login_required(Permissions.BUDGET)
def route_unpaid():
  """
  Displays unpaid expenses, and allows the user to create payments for them.
  """

  payment_types = helpers.get_payment_types()
  accounts = helpers.get_accounts()
  expense_groups=helpers.get_unpaid_expenses()
  today = datetime.now().strftime("%Y-%m-%d")

  return flask.render_template('unpaid.html',
    payment_types=payment_types,
    accounts=accounts,
    expense_groups=expense_groups,
    today=today)


@blueprint.route('/unpaid/submit', methods=['POST'])
@login_required(Permissions.BUDGET)
@get_args_from_form()
def route_submit_unpaid(payee_id, payment_type, account_id, check_no,
    date_written):
  """Sends the payment to the database."""

  # The date posted is the same as the date written unless we're using a check
  date_posted = None if (payment_type != PaymentType.CHECK) else date_written

  # Server side validation
  total = helpers.get_unpaid_amount(payee_id)
  valid_payment = helpers.validate_payment(payment_type, account_id, check_no)
  has_expenses = (total is not None)

  errs = helpers.test_predicates((
    (valid_payment, True, "Invalid payment."),
    (has_expenses,  True, "This payee has no expenses to reimburse."),
  ))

  if errs:
    return flask.redirect(flask.url_for("budget.route_unpaid"))


  # We use a transaction to make sure we don't submit halfway.
  transaction = flask.g.db.begin()
  try:
    payment_id = helpers.record_payment(
        account_id, payment_type, total, date_written, date_posted,
        payee_id, check_no)
    helpers.mark_as_paid(payee_id, payment_id)
    transaction.commit()
    flask.flash("Payment recorded successfully!")

  except Exception:
    transaction.rollback()
    flask.flash("An unexpected error occurred. Please find an IMSS rep.")

  return flask.redirect(flask.url_for("budget.route_unpaid"))


@blueprint.route('/checks')
@login_required(Permissions.BUDGET)
def route_checks():
  """Displays all undeposited checks."""
  return flask.render_template('checks.html',
    checks=helpers.get_unposted_payments(),
    ptypes=helpers.get_payment_types())


@blueprint.route('/checks/submit', methods=['POST'])
@login_required(Permissions.BUDGET)
@get_args_from_form()
def route_process_check(payment_id, date_posted, action):
  """Records a check as deposited."""

  # Server side validation
  unposted_ids = [str(x["payment_id"]) for x in helpers.get_unposted_payments()]

  errs = helpers.test_predicates((
    (payment_id in unposted_ids, True,             "Not a valid payment ID!"),
    (date_posted != "",          action == "Post", "No date entered!"       )
  ))

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
