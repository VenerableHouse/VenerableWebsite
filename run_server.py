"""Runs a test server."""

import argparse
import ruddock
from ruddock import app

parser = argparse.ArgumentParser()
parser.add_argument("--env", default="dev")
parser.add_argument("--port", type=int, default=5000)

if __name__ == "__main__":
  args = parser.parse_args()
  ruddock.init(args.env)
  app.run(port=args.port)
