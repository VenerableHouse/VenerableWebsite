/*
 * This script sets up the test database for the first time.
 * It is run by Travis at the beginning of each test run.
 *
 * This script must be run by the root account.
 */

DROP USER IF EXISTS 'ruddweb_test'@'localhost';
CREATE USER 'ruddweb_test'@'localhost' IDENTIFIED BY 'public';
GRANT ALL PRIVILEGES ON ruddweb_test.* TO 'ruddweb_test'@'localhost';
