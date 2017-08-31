import json
import flask

import datetime

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.birthdays import blueprint, helpers

@blueprint.route('/')
@login_required(Permissions.BIRTHDAYS)
def show_bdays():
  """Displays a list of birthdays for current students."""

  # Extract parts of today's date
  today = datetime.date.today()
  ref_date = today.strftime("%m/%d")
  ref_year = today.year

  def process(row):
    name = row["name"]
    birthday = row["birthday"]

    # Split the birthday into year and date
    bdate = birthday.strftime("%m/%d")
    byear = birthday.year

    # Find the year of the upcoming birthday
    if bdate >= ref_date:
      year = ref_year
    else:
      year = ref_year + 1

    # Make upcoming birthday date and age
    date_str = str(year) + "/" + bdate
    age = year - byear

    # Return results as a dictionary
    out_dict = {"date":date_str, "name":name, "age":age, "byear":byear }
    return out_dict

  # Fetch rows, process them, and sort them by upcoming birthday
  db_rows = helpers.fetch_birthdays()

  bdays = [process(r) for r in db_rows if r["birthday"] is not None]
  bdays.sort(key=lambda x:x["date"])

  unknowns = [r["name"] for r in db_rows if r["birthday"] is None]

  return flask.render_template('bday_list.html', bdays=bdays,
      unknowns=unknowns)