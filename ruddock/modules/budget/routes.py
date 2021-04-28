import flask
import http
import itertools

from sqlalchemy import func

from ruddock.sqlalchemy_utils import nonnull_sum
from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.budget import blueprint

from .helpers import select_fyear, optional_int, flash_multiple, FormParser
from .schema import FiscalYear, Expense, Payment, Budget, Account, Payee, PaymentType


@blueprint.route("/")
@login_required(Permissions.BUDGET)
def route_portal():
    """Displays the budget portal."""
    return flask.render_template("budget_portal.html")


@blueprint.route("/summary")
@login_required(Permissions.BUDGET)
def route_summary():
    """Displays account and budget summaries."""

    # Get all fiscal years
    all_fiscal_years = (
        flask.g.session.query(FiscalYear).order_by(FiscalYear.fyear_id.desc()).all()
    )

    # Get the selected year
    selected_year, is_current = select_fyear(
        flask.g.session, optional_int(flask.request.args.get("fyear", None))
    )

    # Get budgets and how much each has spent
    budgets = (
      flask.g.session.query(
        Budget,
        nonnull_sum(Expense.cost).label("spent"),
      )
      .outerjoin(Expense)  # left join
      .filter(Budget.fyear_id == selected_year.fyear_id)
      .group_by(Budget.budget_id)
      .order_by(Budget.budget_name)
      .all()
    )

    # Accounts and how much each has left
    # Note: you may be tempted to pull the WHERE clause out, thus flattening
    # the query. This won't work, because if there's no payments on some
    # account, the WHERE clause will strip that account from the output.
    subquery = (
      flask.g.session.query(
        Payment.account_id,
        nonnull_sum(Payment.amount).label("spent")
      )
      .filter(Payment.date_posted != None)
      .group_by(Payment.account_id)
      .subquery()
    )
    accounts = (
      flask.g.session.query(Account, func.coalesce(subquery.c.spent, 0))
      .outerjoin(subquery)
      .order_by(Account.account_name)
      .all()
    )

    return flask.render_template(
        "summary.html",
        selected_year=selected_year,
        is_current=is_current,
        all_fiscal_years=all_fiscal_years,
        accounts=accounts,
        budgets=budgets,
    )


@blueprint.route("/expenses")
@login_required(Permissions.BUDGET)
def route_expenses():
    """Displays list of expenses."""
    all_expenses = (
        flask.g.session.query(Expense).order_by(Expense.expense_id.desc()).all()
    )

    return flask.render_template("expenses.html", expenses=all_expenses)


@blueprint.route("/payments")
@login_required(Permissions.BUDGET)
def route_payments():
    """Displays list of payments."""
    all_payments = (
        flask.g.session.query(Payment).order_by(Payment.payment_id.desc()).all()
    )

    return flask.render_template("payments.html", payments=all_payments)


@blueprint.route("/add_expense")
@login_required(Permissions.BUDGET)
def route_add_expense():
    """Provides an interface for submitting an expense."""

    # Get all fiscal years
    all_fiscal_years = (
        flask.g.session.query(FiscalYear).order_by(FiscalYear.fyear_id.desc()).all()
    )

    # Get the selected year
    selected_year, is_current = select_fyear(
        flask.g.session, optional_int(flask.request.args.get("fyear", None))
    )

    # Get all budgets for the year
    budgets_list = (
        flask.g.session.query(Budget)
        .filter(Budget.fyear_id == selected_year.fyear_id)
        .order_by(Budget.budget_name)
        .all()
    )

    # Fetch accounts and payees
    accounts = flask.g.session.query(Account).order_by(Account.account_name).all()
    payees = flask.g.session.query(Payee).order_by(Payee.payee_name).all()

    return flask.render_template(
        "add_expense.html",
        all_fiscal_years=all_fiscal_years,
        budgets=budgets_list,
        payment_type_enum=PaymentType,
        accounts=accounts,
        payees=payees,
        selected_fy=selected_year,
        is_current=is_current,
    )


@blueprint.route("/add_expense/submit", methods=["POST"])
@login_required(Permissions.BUDGET)
def route_submit_expense():
    """Sends the expense to the database."""

    # Get the URL to redirect to
    exit_url = flask.url_for("budget.route_add_expense")

    # Fetch args from form
    # TODO fold errors into flask.flash?
    fp = FormParser(flask.request.form)
    budget_id = fp.parse_int("budget-id")
    date_incurred = fp.parse_date("date-incurred")
    description = fp.parse_str("description")
    cost = fp.parse_currency("cost")
    defer_payment = fp.parse_checkbox("defer-payment")

    # Construct the expense
    expense = Expense(
        budget_id=budget_id,
        date_incurred=date_incurred,
        description=description,
        cost=cost,
    )
    # TODO validate

    # This next part depends on whether we are deferring payment or not.
    # If so, then we leave the payment ID null, cause it the corresponding
    # payment hasn't been made yet. However, we require the payee. If it's a new
    # payee, we have to insert it into the database first.
    # If not, then we need to make a new payment, and use its ID. Payee ID is
    # not needed.
    if defer_payment:
        payee_id = fp.parse_int("payee-id")
        new_payee = fp.parse_str("new-payee")

        if (payee_id and new_payee) or (not payee_id and not new_payee):
            flask.flash("Exactly one of payee ID and payee name should be specified!")
            return flask.redirect(exit_url)
        elif payee_id:
            payee = (
                flask.g.session.query(Payee).filter(Payee.payee_id == payee_id).one()
            )
        else:
            payee = Payee(payee_name=new_payee)
            flask.g.session.add(payee)
            flask.g.session.flush()  # so that payee_id is populated

        # Link the payee to the new expense
        expense.payee_id = payee.payee_id
    else:
        payment_type = PaymentType(fp.parse_int("payment-type"))
        account_id = fp.parse_int("account-id")
        check_no = fp.parse_str("check-no") or None

        date_written = date_incurred  # non-deferred payments are instant
        date_posted = None if payment_type == PaymentType.CHECK else date_written

        payment = Payment(
            account_id=account_id,
            payment_type=payment_type,
            amount=cost,
            date_written=date_written,
            date_posted=date_posted,
            payee_id=None,
            check_no=check_no,
        )
        flask.g.session.add(payment)
        flask.g.session.flush()  # to populate payment_id

        # Link the payment to the new expense
        expense.payment_id = payment.payment_id

    # In any case, commit the session and exit.
    flask.g.session.add(expense)
    flask.g.session.commit()

    flask.flash("Expense recorded successfully!")
    return flask.redirect(exit_url)


@blueprint.route("/expenses/<int:expense_id>")
@login_required(Permissions.BUDGET)
def route_show_expense(expense_id):
    """
  Displays an expense and allows you to edit it.
  """

    expense = (
        flask.g.session.query(Expense)
        .filter(Expense.expense_id == expense_id)
        .one_or_none()
    )

    if expense is None:
        flask.abort(http.client.NOT_FOUND)

    fyear_id = expense.budget.fyear_id
    budgets = flask.g.session.query(Budget).filter(Budget.fyear_id == fyear_id).all()
    payees = flask.g.session.query(Payee).order_by(Payee.payee_name).all()

    return flask.render_template(
        "edit_expense.html",
        expense=expense,
        budgets=budgets,
        payment_type_enum=PaymentType,
        payees=payees,
    )


@blueprint.route("/expense/edit", methods=["POST"])
@login_required(Permissions.BUDGET)
def route_edit_expense():
    """Changes the given expense."""

    # Fetch args from form
    fp = FormParser(flask.request.form)
    expense_id = fp.parse_int("expense-id")
    budget_id = fp.parse_int("budget-id")
    date_incurred = fp.parse_date("date-incurred")
    cost = fp.parse_currency("cost")
    description = fp.parse_str("description")
    payee_id = fp.parse_int("payee-id")  # TODO what if it's NULL?
    new_payee = fp.parse_str("new-payee")

    # Get the URL to redirect to
    exit_url = flask.url_for("budget.route_show_expense", expense_id=expense_id)

    expense = (
        flask.g.session.query(Expense)
        .filter(Expense.expense_id == expense_id)
        .one_or_none()
    )
    if expense is None:
        flask.abort(http.client.NOT_FOUND)

    existing_payment = expense.payment_id is not None
    valid_expense = True  # TODO
    cost_changed = expense.cost != cost
    payee_changed = expense.payee_id != int(payee_id)

    # Can't change payment info if there's a linked payment
    # TODO soften this so debit purchaes aren't a PITA

    errs = []
    if existing_payment and cost_changed:
        errs.append("Can't change cost with linked payment.")
    if existing_payment and payee_changed:
        errs.append("Can't change payee with linked payment.")

    if flash_multiple(errs):
        return flask.redirect(exit_url)

    expense.budget_id = budget_id
    expense.date_incurred = date_incurred
    expense.description = description
    expense.cost = cost
    expense.payee_id = payee_id
    # TODO what if payee is new?

    flask.g.session.commit()
    flask.flash("Success!")
    return flask.redirect(exit_url)


@blueprint.route("/expense/delete", methods=["POST"])
@login_required(Permissions.BUDGET)
def route_delete_expense():
    """Deletes the given expense."""

    # Fetch args from form
    fp = FormParser(flask.request.form)
    expense_id = fp.parse_int("expense-id")

    # Get the expense
    expense = (
        flask.g.session.query(Expense)
        .filter(Expense.expense_id == expense_id)
        .one_or_none()
    )
    if expense is None:
        flask.abort(http.client.NOT_FOUND)

    existing_payment = expense.payment_id is not None

    # Can't delete if there's a linked payment
    # TODO soften this so debit purchaes aren't a PITA

    if existing_payment:
        flask.flash("Cannot delete expense if there is a linked payment.")
        return flask.redirect(
            flask.url_for("budget.route_show_expense", expense_id=expense_id)
        )

    # Delete the expense
    flask.g.session.delete(expense)
    flask.g.session.commit()
    flask.flash("Success!")
    return flask.redirect(flask.url_for("budget.route_expenses"))


@blueprint.route("/unpaid")
@login_required(Permissions.BUDGET)
def route_unpaid():
    """
  Displays unpaid expenses, and allows the user to create payments for them.
  """

    # List of expenses, ordered by payee name so itertools.groupby works.
    # Also, sort by payee id, in case we have two people with the same name,
    # and a sort on expense id for cleanliness.
    unpaid_list = (
        flask.g.session.query(Expense)
        .join(Payee)
        .filter(Expense.payment_id == None)
        .order_by(Payee.payee_name, Payee.payee_id, Expense.expense_id)
        .all()
    )

    # Group those expenses by payee, and materialize into a list
    unpaid_grouped = [
        (payee, list(expenses))
        for payee, expenses in itertools.groupby(unpaid_list, lambda e: e.payee)
    ]

    accounts = flask.g.session.query(Account).order_by(Account.account_name).all()
    today = date.today().strftime("%Y-%m-%d")

    return flask.render_template(
        "unpaid.html",
        unpaid_grouped=unpaid_grouped,
        payment_type_enum=PaymentType,
        accounts=accounts,
        today=today,
    )


@blueprint.route("/unpaid/submit", methods=["POST"])
@login_required(Permissions.BUDGET)
def route_submit_unpaid():
    """Sends the payment to the database."""

    # Fetch args from form
    fp = FormParser(flask.request.form)
    payee_id = fp.parse_int("payee-id")
    payment_type = PaymentType(fp.parse_int("payment-type"))
    account_id = fp.parse_int("account-id")
    check_no = fp.parse_str("check-no") or None
    date_written = fp.parse_date("date-written")

    # The date posted is the same as the date written unless we're using a check
    date_posted = date_written if (payment_type != PaymentType.CHECK) else None

    # Get related expenses and compute total cost
    expenses = (
        flask.g.session.query(Expense)
        .filter(Expense.payee_id == payee_id)
        .filter(Expense.payment_id == None)
        .all()
    )
    total = sum(e.cost for e in expenses)

    # Construct the payment
    new_payment = Payment(
        account_id=account_id,
        payment_type=payment_type,
        amount=total,
        date_written=date_written,
        date_posted=date_posted,
        payee_id=payee_id,
        check_no=check_no,
    )
    # TODO validate payment

    # Validation
    errs = []
    if not expenses:
        errs.append("This payee has no expenses to reimburse.")

    if flash_multiple(errs):
        return flask.redirect(flask.url_for("budget.route_unpaid"))

    # Submit the payment and modify the expenses
    flask.g.session.add(new_payment)
    flask.g.session.flush()
    for e in expenses:
        e.payment_id = new_payment.payment_id
    flask.g.session.commit()

    return flask.redirect(flask.url_for("budget.route_unpaid"))


@blueprint.route("/checks")
@login_required(Permissions.BUDGET)
def route_checks():
    """Displays all undeposited checks."""

    unposted = (
        flask.g.session.query(Payment)
        .filter(Payment.date_posted == None)
        .order_by(Payment.payment_id.desc())
        .all()
    )

    return flask.render_template("checks.html", unposted_payments=unposted,)


@blueprint.route("/checks/submit", methods=["POST"])
@login_required(Permissions.BUDGET)
def route_process_check():
    """Records a check as deposited."""

    # Get the URL to redirect to
    exit_url = flask.url_for("budget.route_checks")

    # Fetch args from form
    fp = FormParser(flask.request.form)
    payment_id = fp.parse_int("payment-id")
    action = fp.parse_str("action")

    # Get the list of unposted payments
    unposted = (
        flask.g.session.query(Payment)
        .filter(Payment.date_posted == None)
        .order_by(Payment.payment_id.desc())
        .all()
    )
    unposted_ids = [p.payment_id for p in unposted]

    # Validation
    errs = []
    if payment_id not in unposted_ids:
        errs.append(f"Payment #{payment_id} is not unposted!")
    if action == "Post" and not "date-posted" not in fp.data:
        errs.append("Need to specify the date the payment posted!")

    if flash_multiple(errs):
        return flask.redirect(exit_url)

    # Decide what to do
    if action == "Post":
        # Set the date_posted of the payment
        date_posted = fp.parse_date("date-posted")

        flask.g.session.query(Payment).filter(Payment.payment_id == payment_id).update(
            {"date_posted": date_posted}
        )
        flask.g.session.commit()

        flask.flash("Payment successfully posted!")
    elif action == "Void":
        # Remove the payment from the table, and change the corresponding
        # expenses to have NULL payment ID
        flask.g.session.query(Expense).filter(Expense.payment_id == payment_id).update(
            {"payment_id": None}
        )
        flask.g.session.query(Payment).filter(Payment.payment_id == payment_id).delete()
        flask.g.session.commit()

        flask.flash("Payment successfully voided!")
    else:
        flask.flash("Not a legitimate action!")

    return flask.redirect(exit_url)
