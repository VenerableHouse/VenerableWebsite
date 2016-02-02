"""Runs a test server."""

import argparse
import ruddock
from ruddock import app

parser = argparse.ArgumentParser(
    description="Run a local instance of the test server.")
parser.add_argument("--env", default="dev",
    help="Environment to run application in. Can be 'prod' or 'dev'.")
parser.add_argument("--port", type=int, default=5000,
    help="Port to attach application to.")

if __name__ == "__main__":
  args = parser.parse_args()
  ruddock.init(args.env)
  app.run(port=args.port)
