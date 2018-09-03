/*
 * This is the schema for the database.
 * If you make any schema changes, you must also reflect those changes here!
 */

-- TODO(dkong): remove this table.
CREATE TABLE membership_types (
  member_type INTEGER NOT NULL,
  membership_desc VARCHAR(32) NOT NULL,
  membership_desc_short VARCHAR(32) NOT NULL,
  PRIMARY KEY (member_type),
  UNIQUE (membership_desc),
  UNIQUE (membership_desc_short)
);

-- All members have an entry in this table.
CREATE TABLE members (
  user_id INTEGER NOT NULL AUTO_INCREMENT,
  uid VARCHAR(10) NOT NULL,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  preferred_name VARCHAR(255),
  email VARCHAR(255) NOT NULL,
  member_type INTEGER NOT NULL,
  birthday DATE,
  matriculation_year YEAR,
  graduation_year YEAR,
  msc INTEGER,
  phone VARCHAR(64),
  building VARCHAR(255),
  room_number INTEGER,
  major VARCHAR(255),
  create_account_key CHAR(32),
  PRIMARY KEY (user_id),
  UNIQUE (uid),
  FOREIGN KEY (member_type) REFERENCES membership_types (member_type)
);

-- Account details. Every account has an entry in this table.
-- Not every member will necessarily have an account if they don't create one.
CREATE TABLE users (
  user_id INTEGER NOT NULL,
  username VARCHAR(32) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  lastlogin DATETIME,
  PRIMARY KEY (user_id),
  UNIQUE (username),
  FOREIGN KEY (user_id) REFERENCES members (user_id)
    ON DELETE CASCADE
);

-- Permissions granted to individual users.
-- This should only be used temporarily and sparingly; most use cases should
-- already be covered by office permissions.
CREATE TABLE user_permissions (
  user_id INTEGER NOT NULL,
  -- References the permissions enum.
  permission_id INTEGER NOT NULL,
  PRIMARY KEY (user_id, permission_id),
  FOREIGN KEY (user_id) REFERENCES users (user_id)
    ON DELETE CASCADE
);

-- Every house position has an entry in this table.
CREATE TABLE offices (
  office_id INTEGER NOT NULL AUTO_INCREMENT,
  office_name VARCHAR(32) NOT NULL,
  is_excomm BOOLEAN NOT NULL,
  is_ucc BOOLEAN NOT NULL,
  office_email VARCHAR(255),
  -- Used for displaying offices in a fixed order.
  office_order INTEGER,
  -- Indicates whether the position is one that is currently being used
  -- or is only present for historical reasons.
  is_active BOOLEAN NOT NULL,
  PRIMARY KEY (office_id)
);

-- Many to many mapping between offices and members.
CREATE TABLE office_assignments (
  assignment_id INTEGER NOT NULL AUTO_INCREMENT,
  office_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  PRIMARY KEY (assignment_id),
  -- The tuple (office_id, user_id) is NOT required to be unique.
  -- It is possible for someone to hold the same position multiple times.
  FOREIGN KEY (office_id) REFERENCES offices (office_id)
    ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES members (user_id)
    ON DELETE CASCADE
);

-- Permissions granted to each office.
CREATE TABLE office_permissions (
  office_id INTEGER NOT NULL,
  -- References the permissions enum.
  permission_id INTEGER NOT NULL,
  PRIMARY KEY (office_id, permission_id),
  FOREIGN KEY (office_id) REFERENCES offices (office_id)
    ON DELETE CASCADE
);

-- Table of all residential rooms in the house.
CREATE TABLE rooms (
  room_number INTEGER NOT NULL,
  alley INTEGER NOT NULL,
  coords VARCHAR(255), -- Unused.
  PRIMARY KEY (room_number)
);

-- Rooms available for the room hassle.
CREATE TABLE hassle_rooms (
  room_number INTEGER NOT NULL,
  PRIMARY KEY (room_number),
  FOREIGN KEY (room_number) REFERENCES rooms (room_number)
    ON DELETE CASCADE
);

-- Members participating in the room hassle.
CREATE TABLE hassle_participants (
  user_id INTEGER NOT NULL,
  PRIMARY KEY (user_id),
  FOREIGN KEY (user_id) REFERENCES members (user_id)
    ON DELETE CASCADE
);

-- Room hassle events. An event is a member choosing a room.
CREATE TABLE hassle_events (
  hassle_event_id INTEGER NOT NULL AUTO_INCREMENT,
  user_id INTEGER NOT NULL,
  room_number INTEGER NOT NULL,
  PRIMARY KEY (hassle_event_id),
  UNIQUE (user_id),
  UNIQUE (room_number),
  FOREIGN KEY (user_id) REFERENCES hassle_participants (user_id)
    ON DELETE CASCADE,
  FOREIGN KEY (room_number) REFERENCES hassle_rooms (room_number)
    ON DELETE CASCADE
);

-- Roommates chosen for each room hassle event.
CREATE TABLE hassle_roommates (
  -- May appear multiple times (in the case of multiple roommates).
  user_id INTEGER NOT NULL,
  -- May only appear once.
  roommate_id INTEGER NOT NULL,
  PRIMARY KEY (roommate_id),
  FOREIGN KEY (user_id) REFERENCES hassle_events (user_id)
    ON DELETE CASCADE,
  FOREIGN KEY (roommate_id) REFERENCES hassle_participants (user_id)
    ON DELETE CASCADE
);

-- TODO(dkong): remove this table.
CREATE TABLE updating_email_lists (
  listname VARCHAR(20) NOT NULL,
  query text NOT NULL,
  PRIMARY KEY (listname)
);

-- TODO(dkong): remove this table.
CREATE TABLE updating_email_lists_additions (
  listname VARCHAR(20) NOT NULL,
  email VARCHAR(64) NOT NULL,
  PRIMARY KEY (listname, email)
);

-- ROTATION TABLES

CREATE TABLE rotation_buckets ( -- bucket names are defined in rotation/helpers.py
  bucket_id INTEGER NOT NULL AUTO_INCREMENT,
  bucket_name VARCHAR(10),
  PRIMARY KEY (bucket_id)
);

CREATE TABLE rotation_prefrosh (
  prefrosh_id INTEGER NOT NULL AUTO_INCREMENT,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  preferred_name VARCHAR(255),
  bucket_id INTEGER,
  votes_neg_two INTEGER NOT NULL DEFAULT 0,
  votes_neg_one INTEGER NOT NULL DEFAULT 0,
  votes_zero INTEGER NOT NULL DEFAULT 0,
  votes_plus_one INTEGER NOT NULL DEFAULT 0,
  votes_plus_two INTEGER NOT NULL DEFAULT 0,
  votes_plus_three INTEGER NOT NULL DEFAULT 0,
  dinner INTEGER, -- defined in rotation/helpers.py (1-8)
  attended_dinner BOOLEAN,
  comments BLOB,
  image_name VARCHAR(255),
  PRIMARY KEY (prefrosh_id),
  FOREIGN KEY (bucket_id) REFERENCES rotation_buckets (bucket_id)
);

CREATE TABLE rotation_move_history (
  event_id INTEGER NOT NULL AUTO_INCREMENT,
  prefrosh_id INTEGER NOT NULL,
  old_bucket INTEGER NOT NULL,
  new_bucket INTEGER NOT NULL,
  PRIMARY KEY (event_id),
  UNIQUE (prefrosh_id, old_bucket, new_bucket),
  FOREIGN KEY (prefrosh_id) REFERENCES rotation_prefrosh (prefrosh_id),
  FOREIGN KEY (old_bucket) REFERENCES rotation_buckets (bucket_id),
  FOREIGN KEY (new_bucket) REFERENCES rotation_buckets (bucket_id)
);

-- BUDGET TABLES

-- Table of all accounts Ruddock owns.
CREATE TABLE budget_accounts (
  account_id INTEGER NOT NULL AUTO_INCREMENT,
  account_name VARCHAR(255) NOT NULL,
  initial_balance NUMERIC(9,2) NOT NULL,
  PRIMARY KEY (account_id)
);

-- Table of fiscal years and when they start.
CREATE TABLE budget_fyears (
  fyear_id INTEGER NOT NULL AUTO_INCREMENT,
  fyear_num INTEGER NOT NULL, -- the number itself, like 2016
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  PRIMARY KEY (fyear_id)
);

-- Table of all budgets.
CREATE TABLE budget_budgets (
  budget_id INTEGER NOT NULL AUTO_INCREMENT,
  budget_name VARCHAR(32) NOT NULL,
  fyear_id INTEGER NOT NULL,
  starting_amount NUMERIC(9,2) NOT NULL,
  PRIMARY KEY (budget_id),
  FOREIGN KEY (fyear_id) REFERENCES budget_fyears (fyear_id)
);

-- Table of payees. This is used for students, other houses, basically anyone you'd write a check to.
CREATE TABLE budget_payees (
  payee_id INTEGER NOT NULL AUTO_INCREMENT,
  payee_name VARCHAR(255) NOT NULL,
  PRIMARY KEY (payee_id)
);

-- Table of payments. This is actual money flow, and each payment could include multiple expenses.
CREATE TABLE budget_payments (
  payment_id INTEGER NOT NULL AUTO_INCREMENT,
  account_id INTEGER NOT NULL,
  payment_type INTEGER NOT NULL,
  amount NUMERIC(9,2) NOT NULL,
  date_written DATE NOT NULL,
  date_posted DATE, -- checks don't go through immediately, so this makes balance checking easier
  payee_id INTEGER, -- not strictly necessary, but hard to derive from budget_expenses
  check_no VARCHAR(10), -- only used for checks (duh)
  PRIMARY KEY (payment_id),
  FOREIGN KEY (account_id) REFERENCES budget_accounts (account_id),
  FOREIGN KEY (payee_id) REFERENCES budget_payees (payee_id)
);

-- Table of expenses. These include expenditures that need to be reimbursed.
CREATE TABLE budget_expenses (
  expense_id INTEGER NOT NULL AUTO_INCREMENT,
  budget_id INTEGER NOT NULL,
  date_incurred DATE NOT NULL,
  description VARCHAR(500) NOT NULL,
  cost NUMERIC(9,2) NOT NULL,
  payment_id INTEGER, -- null until the expense gets a matching payment
  payee_id INTEGER, -- used to keep track of who to reimburse
  PRIMARY KEY (expense_id),
  FOREIGN KEY (budget_id) REFERENCES budget_budgets (budget_id),
  FOREIGN KEY (payment_id) REFERENCES budget_payments (payment_id),
  FOREIGN KEY (payee_id) REFERENCES budget_payees (payee_id)
);

-- VIEWS

CREATE VIEW members_alumni AS
  SELECT user_id
  FROM members
  WHERE NOW() >= CONCAT(graduation_year, '-07-01');

CREATE VIEW members_current AS
  SELECT user_id
  FROM members
  WHERE NOW() < CONCAT(graduation_year, '-07-01');

CREATE VIEW members_extra AS
  SELECT user_id,
    CONCAT(IFNULL(preferred_name, first_name), ' ', last_name) AS name
  FROM members;

CREATE VIEW office_assignments_current AS
  SELECT assignment_id
  FROM office_assignments
  WHERE start_date < NOW() AND end_date > NOW();

CREATE VIEW office_assignments_future AS
  SELECT assignment_id FROM office_assignments
  WHERE start_date > NOW();

CREATE VIEW office_assignments_past AS
  SELECT assignment_id
  FROM office_assignments
  WHERE start_date < NOW() AND end_date < NOW();
