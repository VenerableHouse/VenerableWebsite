"""Runs a test server.

Example usage:
  python run_server.py --env test --port 9001
"""

import argparse

import ruddock
from ruddock import app

parser = argparse.ArgumentParser(
    description="Run a local instance of the test server.")
parser.add_argument("--env", default="test",
    help="Environment to run application in. Can be 'prod', 'dev', or 'test'. "
        + "Default is 'test'.")
parser.add_argument("--port", type=int, default=5000,
    help="Port to attach application to. Default is 5000.")

if __name__ == "__main__":
  args = parser.parse_args()
  ruddock.init(args.env)
  app.run(port=args.port)
