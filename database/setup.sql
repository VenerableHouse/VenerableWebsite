/*
 * This script sets up the test database for the first time.
 * It is run by Travis at the beginning of each test run.
 *
 * For subsequent resets of the test database, use the reset script.
 */

DROP USER IF EXISTS 'ruddweb_test'@'localhost';
CREATE USER 'ruddweb_test'@'localhost' IDENTIFIED BY 'public';
GRANT ALL PRIVILEGES ON ruddweb_test.* TO 'ruddweb_test'@'localhost';

-- This creates the test database.
SOURCE 'database/reset.sql';
