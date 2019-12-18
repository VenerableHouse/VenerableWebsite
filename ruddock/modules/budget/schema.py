#!/usr/bin/env python3

from enum import Enum

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from ruddock.sqlalchemy_utils import IntEnum

Base = declarative_base()


class PaymentType(Enum):
    CASH = 1
    CHECK = 2
    DEBIT = 3
    ONLINE = 4
    TRANSFER = 5
    OTHER = 6
    INCOME = 7


class Account(Base):
    __tablename__ = "budget_accounts"

    account_id = Column(Integer, primary_key=True)
    account_name = Column(String)
    initial_balance = Column(Numeric)

    def __repr__(self):
        return f"<Account {self.account_id} named {self.account_name}>"


class FiscalYear(Base):
    __tablename__ = "budget_fyears"

    fyear_id = Column(Integer, primary_key=True)
    fyear_num = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)

    def __repr__(self):
        return f"<Fiscal Year {self.fyear_id} ending in {self.fyear_num}>"


class Budget(Base):
    __tablename__ = "budget_budgets"

    budget_id = Column(Integer, primary_key=True)
    budget_name = Column(String)
    fyear_id = Column(Integer, ForeignKey("budget_fyears.fyear_id"))
    starting_amount = Column(Numeric)

    fiscal_year = relationship(FiscalYear)

    def __repr__(self):
        return f"<Budget {self.budget_id} for {self.budget_name} in {self.fiscal_year.fyear_num}>"


class Payee(Base):
    __tablename__ = "budget_payees"

    payee_id = Column(Integer, primary_key=True)
    payee_name = Column(String)

    def __repr__(self):
        return f"<Payee {self.payee_id} named {self.payee_name}>"


class Payment(Base):
    __tablename__ = "budget_payments"

    payment_id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("budget_accounts.account_id"))
    payment_type = Column(IntEnum(PaymentType))
    amount = Column(Numeric)
    date_written = Column(Date)
    date_posted = Column(Date)
    payee_id = Column(Integer, ForeignKey("budget_payees.payee_id"))
    check_no = Column(String)

    account = relationship(Account)
    payee = relationship(Payee)

    def __repr__(self):
        return f"<Payment {self.payment_id} for {self.amount}>"


class Expense(Base):
    __tablename__ = "budget_expenses"

    expense_id = Column(Integer, primary_key=True)
    budget_id = Column(Integer, ForeignKey("budget_budgets.budget_id"))
    date_incurred = Column(Date)
    description = Column(String)
    cost = Column(Numeric)
    payment_id = Column(Integer, ForeignKey("budget_payments.payment_id"))
    payee_id = Column(Integer, ForeignKey("budget_payees.payee_id"))

    budget = relationship(Budget)
    payment = relationship(Payment)
    payee = relationship(Payee)

    def __repr__(self):
        return f"<Expense {self.expense_id} from {self.budget.budget_name} for {self.cost}>"
