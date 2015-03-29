from flask import Blueprint
blueprint = Blueprint('auth', __name__, template_folder='templates')

import RuddockWebsite.modules.auth.routes
