/* These are client-side validation functions that are re-used throughout the
   budget module.
   TODO is this good practice? */

// TODO make this a kind of HTML+JS component, if that's possible. so i can
// just include "validating_expense_form" as a block. (see account_input.html)
// look into macros for this.
/* Checks if this expense information is ready to submit.
   Returns an array of error messages, possibly empty. */
function validate_expense(budget_id, date_incurred, amount, description) {
  // Looks a little peculiar, but catches both cents-only and dollar-only
  // strings, and blocks the empty string (.43, 12, for example).
  var regex_amount = /^-?\d*(\d|(\.\d\d))$/;

  var errors = [];

  if (budget_id == "") {
    errors.push("You must select a budget.");
  }

  // Bless HTML5 for not making me parse dates
  if (date_incurred == "") {
    errors.push("You must enter a date.");
  }

  if (!regex_amount.test(amount)) {
    errors.push("You must enter an amount.");
  }

  if (description == "") {
    errors.push("The description must be non-empty.");
  }

  return errors;
}

/* Checks if this payment information is ready to submit.
   Returns an array of error messages, possibly empty. */
function validate_payment(payment_type, account_id, check_no) {
  var errors = [];

  if (payment_type == "") {
    errors.push("You must specify the type of payment.");
  }
  if (account_id == "") {
    errors.push("You must specify an account to pay from.");
  }
  if (payment_type == "Check" & check_no == "") {
    errors.push("You must specify a number when paying by check.");
  }

  return errors;
}

/* Checks if any payee was specified.
   Returns an array of error messages, possibly empty. */
function validate_payee(payee_id, new_payee) {
  var errors = [];

  if (payee_id == "" & new_payee == "") {
      errors.push("You must specify a payee when deferring payment.");
  }
  if (payee_id != "" & new_payee != "") {
      errors.push("You cannot select both a new and existing payee.");
  }

  return errors;
}