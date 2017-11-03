import flask

from datetime import datetime  # ugh

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

  current_fyear_id = helpers.get_current_fyear()["fyear_id"]
  a_summary = helpers.get_account_summary()
  b_summary = helpers.get_budget_summary(current_fyear_id)

  return flask.render_template('summary.html',
    a_summary=a_summary,
    b_summary=b_summary)


@blueprint.route('/expenses')
@login_required(Permissions.BUDGET)
def route_expenses():
  """Displays list of expenses."""
  return flask.render_template('expenses.html',
    expenses=helpers.get_expenses())


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

  flask.flash("Not implemented yet, but this didn't crash!")

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
def route_submit_unpaid():
  """Sends the payment to the database."""

  flask.flash("Not implemented yet, but this didn't crash!")

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
def route_process_check():
  """Records a check as deposited or voided."""

  flask.flash("Not implemented yet, but this didn't crash!")

  return flask.redirect(flask.url_for("budget.route_checks"))