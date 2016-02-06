#!/bin/bash

# Use this script for consistent usage of mysqldump.
mysqldump -u root -p ruddweb \
  --skip-opt \
  --skip-quote-names \
  --no-data \
  --skip-comments \
  --skip-dump-date \
  --single-transaction \
