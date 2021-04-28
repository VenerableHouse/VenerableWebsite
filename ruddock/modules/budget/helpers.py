#!/usr/bin/env python3

import datetime
import decimal
import flask
import itertools
from .schema import FiscalYear, Expense, Payment, Payee

def optional_int(x):
    if x is None:
        return None
    return int(x)


def select_fyear(session, fyear_num):
    """
    Returns a FiscalYear object and a boolean, indicating whether the
    year is the current year.

    If a fiscal year is passed, returns that year. If None is passed,
    returns the current year.
    """

    today = datetime.date.today()
    if fyear_num is None:
        fyear = (
            session.query(FiscalYear)
            .filter(FiscalYear.start_date <= today)
            .filter(today <= FiscalYear.end_date)
            .one()
        )
        is_current = True
    else:
        fyear = session.query(FiscalYear).filter(FiscalYear.fyear_num == fyear_num).one()
        is_current = fyear.start_date <= today <= fyear.end_date
    return fyear, is_current

def flash_multiple(errors):
    """
    Like flask.flash but takes multiple strings. Returns True if errors is
    non-empty, False otherwise.
    """
    for error in errors:
        flask.flash(errors)
    return bool(errors)

class FormParser:
    def __init__(self, data):
        self.data = data

    def parse_int(self, key):
        return int(self.data[key])

    def parse_str(self, key):
        return str(self.data[key])

    def parse_date(self, key):
        val = self.data[key]
        return datetime.datetime.strptime(val, "%Y-%m-%d").date()

    def parse_checkbox(self, key):
        return key in self.data

    def parse_currency(self, key):
        TWOPLACES = decimal.Decimal("0.01")
        d = decimal.Decimal(self.data[key])
        assert d == d.quantize(TWOPLACES)
        return d

    # TODO perhaps some way to gather up all parsing errors,
    # so that they can be flask-flashed to the user?
