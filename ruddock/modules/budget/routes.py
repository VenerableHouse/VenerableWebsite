import flask
import http

from datetime import datetime  # ugh
from decimal import Decimal

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

  fyear, is_current = helpers.select_fyear_info(
    flask.request.args.get("fyear", None)
  )

  fyear_id = fyear["fyear_id"]
  fyear_num = fyear["fyear_num"]

  fyear_options = [(r["fyear_num"], r["fyear_id"]) for r in helpers.get_fyears()]
  fyear_options.sort(key=lambda x: x[0], reverse=True)

  a_summary = helpers.get_account_summary()
  b_summary = helpers.get_budget_summary(fyear_id)

  return flask.render_template('summary.html',
    a_summary=a_summary,
    b_summary=b_summary,
    fyear_num=fyear_num,
    is_current=is_current,
    fyear_options=fyear_options)


@blueprint.route('/summary/download')
@login_required(Permissions.BUDGET)
def route_download_summaries():
  """Downloads account and budget summaries."""
  fyear, is_current = helpers.select_fyear_info(
    flask.request.args.get("fyear", None)
  )
  fyear_id = fyear["fyear_id"]
  return helpers.download_summaries(fyear_id)

@blueprint.route('/expenses')
@login_required(Permissions.BUDGET)
def route_expenses():
  """Displays list of expenses."""
  return flask.render_template('expenses.html',
    expenses=helpers.get_transactions(),
    ptypes=PaymentType.get_all())


@blueprint.route('/expenses/download')
@login_required(Permissions.BUDGET)
def route_download_expenses():
  """Downloads list of expenses."""
  return helpers.download_expenses()


@blueprint.route('/payments')
@login_required(Permissions.BUDGET)
def route_payments():
  """Displays list of payments."""
  return flask.render_template('payments.html',
    payments=helpers.get_payments(),
    ptypes=PaymentType.get_all())


@blueprint.route('/add_expense')
@login_required(Permissions.BUDGET)
def route_add_expense():
  """Provides an interface for submitting an expense."""

  fyear, is_current = helpers.select_fyear_info(
    flask.request.args.get("fyear", None)
  )

  fyear_id = fyear["fyear_id"]
  fyear_num = fyear["fyear_num"]

  fyear_options = [(r["fyear_num"], r["fyear_id"]) for r in helpers.get_fyears()]
  fyear_options.sort(key=lambda x: x[0], reverse=True)

  # Get the lists for the dropdown menus
  budgets_list = helpers.get_budget_list(fyear_id)
  payment_types = PaymentType.get_all()
  accounts = helpers.get_accounts()
  payees = helpers.get_payees()

  return flask.render_template('add_expense.html',
    budgets=budgets_list,
    payment_types=payment_types,
    accounts=accounts,
    payees=payees,
    fyear_options=fyear_options,
    fyear_num=fyear_num,
    is_current=is_current)


@blueprint.route('/add_expense/submit', methods=['POST'])
@login_required(Permissions.BUDGET)
@get_args_from_form()
def route_submit_expense(budget_id, date_incurred, amount, description,
    payee_id, new_payee, payment_type, account_id):
  """Sends the expense to the database."""

  defer_payment = False # deprecated feature
  check_no = "0" # deprecated feature

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
    date_written = date_incurred
    date_posted = None if payment_type == PaymentType.CHECK.value else date_written

    payee_id = None
    payment_id = helpers.record_payment(
      account_id, payment_type, amount, date_written, date_posted,
      payee_id, check_no)

    # Record the expense
    helpers.record_expense(
        budget_id, date_incurred, description, amount, payment_id, payee_id)
    transaction.commit()
    flask.flash("Expense recorded successfully!")

  except Exception:
      transaction.rollback()
      flask.flash("An unexpected error occurred. Please find an IMSS rep.")

  return flask.redirect(flask.url_for("budget.route_add_expense"))


@blueprint.route('/expenses/<int:expense_id>')
@login_required(Permissions.BUDGET)
def route_show_expense(expense_id):
  """
  Displays an expense and allows you to edit it.
  """

  expense = helpers.get_expense(expense_id)

  if expense is None:
    flask.abort(http.client.NOT_FOUND)


  budgets_list = helpers.get_budget_list(expense["fyear_id"])
  payment_types = PaymentType.get_all()
  payees = helpers.get_payees()

  return flask.render_template(
    'edit_expense.html',
    expense=expense,
    budgets=budgets_list,
    payment_types=payment_types,
    payees=payees
  )


@blueprint.route('/expense/edit', methods=['POST'])
@login_required(Permissions.BUDGET)
@get_args_from_form()
def route_edit_expense(expense_id, budget_id, date_incurred, amount, description, payee_id, new_payee, payment_type):
  """Changes the given expense."""

  expense = helpers.get_expense(expense_id)
  if expense is None:
    flask.abort(http.client.NOT_FOUND)

  existing_payment = expense["payment_id"] is not None
  valid_expense = helpers.validate_expense(budget_id, date_incurred, amount,
      description)

  if not valid_expense:
    return flask.redirect(flask.url_for("budget.route_show_expense", expense_id=expense_id))

  if payee_id == '':
    payee_id = None

  success = helpers.edit_expense(
    expense_id, budget_id, date_incurred, description, amount, payee_id
  )
  if success:
    flask.flash("Success!")
  else:
    flask.flash("Something went wrong during the edit, not sure what.")

  if payment_type == '':
    payment = helpers.get_payment(expense["payment_id"])
    payment_type = payment["payment_type"]

  if existing_payment:
    helpers.edit_payment(expense["payment_id"], Decimal(amount), date_incurred, payee_id, payment_type)

  return flask.redirect(flask.url_for("budget.route_show_expense", expense_id=expense_id))


@blueprint.route('/expense/delete', methods=['POST'])
@login_required(Permissions.BUDGET)
@get_args_from_form()
def route_delete_expense(expense_id, budget_id, date_incurred, amount, description, payee_id, new_payee):
  """
  Deletes the given expense.
  If there is a linked payment, deletes that also.
  """

  expense = helpers.get_expense(expense_id)
  if expense is None:
    flask.abort(http.client.NOT_FOUND)

  helpers.delete_expense(expense_id)
  if expense["payment_id"] is not None:
    helpers.delete_payment(expense["payment_id"])

  flask.flash("Success!")
  return flask.redirect(flask.url_for("budget.route_expenses"))


@blueprint.route('/unpaid')
@login_required(Permissions.BUDGET)
def route_unpaid():
  """
  Displays unpaid expenses, and allows the user to create payments for them.
  """

  payment_types = PaymentType.get_all()
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
  date_posted = None if (payment_type != PaymentType.CHECK.value) else date_written

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
    ptypes=PaymentType.get_all())


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
