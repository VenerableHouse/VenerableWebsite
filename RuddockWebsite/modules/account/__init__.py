from flask import Blueprint
blueprint = Blueprint('account', __name__, template_folder='templates')

import RuddockWebsite.modules.account.routes
