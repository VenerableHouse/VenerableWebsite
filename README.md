# RuddockWebsite

The Ruddock House Website, written using Python/Flask and powered by MariaDB. The live version can be found at: https://ruddock.caltech.edu

# Setting up your environment
- You should already have SSH access to the development server.
- Clone the repository:
```
git clone https://github.com/RuddockHouse/RuddockWebsite ~/RuddockWebsite
```
- Set up your virtualenv:
```
mkdir ~/virtualenvs (if you haven't already)
cd ~/virtualenvs
virtualenv RuddockWebsite
source ~/virtualenvs/RuddockWebsite/bin/activate
```
- The last command activates the virtualenv, so that your Python version and packages are managed on a per-project basis by virtualenv instead of using the global Python installation. You may want to create an alias in your `~/.bashrc` file since this must be executed every time you want to start development. If you want to leave the virtual environment, use the `deactivate` command.
- Install the required packages using pip:
```
pip install -r requirements.txt
```
- You will also need a separate config file that we will give you in order to access the database.

# Testing

### Test site
The easiest way to set up a test site is to use SSH port forwarding, so that requests to your local computer are forwarded to the development server. For example:
```
ssh -L 9001:localhost:5000 <host>
```
This will forward your local port 9001 so that visiting [localhost:9001](http://localhost:9001) on your local computer is equivalent to visiting [localhost:5000](http://localhost:5000) on the remote server. Flask's debugging environment defaults to port 5000, but you can change that in your `config.py` file (multiple people cannot simultaneously bind to the same port through SSH port forwarding).

To start the test site:
```
python run_server.py
```
You can visit the test site by going to [localhost:9001](http://localhost:9001) (or whichever port you decided to forward) in your local browser.

### Automated testing
We use [pytest](http://pytest.org/latest/index.html) for automated testing. Tests are located in the `RuddockWebsite.tests` module. To run all tests, execute this on the command line:
```
py.test
```
Which will automatically find all test scripts (test scripts look like `test_*.py`) inside the current directory/subdirectories and execute functions or methods that look like `test_*()`.

# Other things

### Ruddock constitution

When an update is made to the [constitution](https://github.com/RuddockHouse/RuddockConstitution), simply download an updated copy of the pdf and commit it into this repository.
