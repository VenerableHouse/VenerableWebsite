from flask import Blueprint
blueprint = Blueprint('hassle', __name__, template_folder='templates')

import RuddockWebsite.modules.hassle.routes
