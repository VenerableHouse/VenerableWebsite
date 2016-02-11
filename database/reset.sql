/*
 * This script resets the test database to a consistent state
 * and should be run at the beginning of each integration test.
 */

DROP DATABASE IF EXISTS ruddweb_test;
CREATE DATABASE ruddweb_test;
USE ruddweb_test;

-- Create the database schema.
SOURCE database/schema.sql

-- Populate with test data.
SOURCE database/test_data.sql
