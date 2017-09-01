"""
Checks that constitution in static/ is synced with the upstream repository.
"""

import hashlib
import httplib
import requests
import sys
import json

FILE_NAME = "constitution.pdf"
UPSTREAM_API_PATH = "https://api.github.com/repos/RuddockHouse/RuddockConstitution/releases/latest"
LOCAL_PATH = "ruddock/static/constitution/" + FILE_NAME
BROWSER_DOWNLOAD_URL_PROPERTY = "browser_download_url"
ASSETS_PROPERTY = "assets"
NAME_PROPERTY = "name"

def get_upstream_constitution():
  """
  Retrieves a copy of the constitution from the master branch of the upstream
  repository. Returns a string in binary format.
  """
  response = requests.get(UPSTREAM_API_PATH)
  if response.status_code == httplib.OK:
    result_dict = json.loads(response.content)
    assets = result_dict[ASSETS_PROPERTY]
    # extract URL for filename
    upstream_url = [x[BROWSER_DOWNLOAD_URL_PROPERTY]
                    for x in assets if x[NAME_PROPERTY] == FILE_NAME][0]
    pdf_response = requests.get(upstream_url)
    if pdf_response.status_code == httplib.OK:
      return pdf_response.content
    else:
      return None
  else:
    return None

def get_local_constitution():
  """
  Reads the copy of the constitution in static/.
  Returns a binary stream.
  """
  try:
    constitution_file = open(LOCAL_PATH, "rb")
  except IOError:
    print >> sys.stderr, "Could not open local copy of constitution. Make sure you're running the test suite from the top level RuddockWebsite/ directory."
    return None
  data = constitution_file.read()
  constitution_file.close()
  return data

def hash_file(file_content):
  """
  Computes the MD5 hash of a file (input should be binary string of file's data).
  """
  return hashlib.md5(file_content).hexdigest()

def test_constitution():
  """
  Checks that the local copy of the constitution is the same version as the
  upstream one.
  """
  upstream = get_upstream_constitution()
  local = get_local_constitution()

  assert upstream is not None
  assert local is not None
  assert hash_file(upstream) == hash_file(local)
