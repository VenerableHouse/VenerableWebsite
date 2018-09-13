# Activate the virtualenv.
activate_this = "/home/ruddweb/virtualenvs/RuddockWebsite3/bin/activate_this.py"
exec(compile(open(activate_this).read(), activate_this, 'exec'), dict(__file__=activate_this))

# Put the repository in Python's path.
import sys
sys.path.insert(0, "/home/ruddweb/RuddockWebsite")

# Import and initialize the application.
import ruddock
from ruddock import app as application
ruddock.init("prod")
