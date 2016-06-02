"""
Checks that constitution in static/ is synced with the upstream repository.
"""

import hashlib
import http.client
import requests
import sys

UPSTREAM_URL = "https://github.com/RuddockHouse/RuddockConstitution/raw/master/constitution.pdf"
LOCAL_PATH = "ruddock/static/constitution/constitution.pdf"

def get_upstream_constitution():
  """
  Retrieves a copy of the constitution from the master branch of the upstream
  repository. Returns a string in binary format.
  """
  response = requests.get(UPSTREAM_URL)
  if response.status_code == http.client.OK:
    return response.content
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
    print("Could not open local copy of constitution. Make sure you're running the test suite from the top level RuddockWebsite/ directory.", file=sys.stderr)
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
