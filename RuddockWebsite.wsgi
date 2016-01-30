activate_this = "/home/ruddweb/virtualenvs/RuddockWebsite/bin/activate_this.py"
execfile(activate_this, dict(__file__=activate_this))

import sys
sys.path.insert(0, "/home/ruddweb/RuddockWebsite")
from ruddock import app as application
