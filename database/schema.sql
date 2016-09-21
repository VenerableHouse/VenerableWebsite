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

CREATE TABLE rotation_prefrosh (
  prefrosh_id INTEGER NOT NULL AUTO_INCREMENT,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  preferred_name VARCHAR(255),
  image LONGBLOB,
  bucket ENUM('-2', '-1', '000', '0', '0.5', '1', '1.5', '2', '3') NOT NULL DEFAULT '0',
  votes_neg_two INTEGER NOT NULL DEFAULT 0,
  votes_neg_one INTEGER NOT NULL DEFAULT 0,
  votes_zero INTEGER NOT NULL DEFAULT 0,
  votes_plus_one INTEGER NOT NULL DEFAULT 0,
  votes_plus_two INTEGER NOT NULL DEFAULT 0,
  votes_plus_three INTEGER NOT NULL DEFAULT 0,
  dinner INTEGER,
  attended_dinner BOOLEAN,
  comments VARCHAR(5000),
  PRIMARY KEY (prefrosh_id)
);

CREATE TABLE rotation_move_history (
  prefrosh_id INTEGER NOT NULL,
  old_bucket INTEGER NOT NULL,
  new_bucket INTEGER NOT NULL,
  PRIMARY KEY (prefrosh_id, old_bucket, new_bucket),
  FOREIGN KEY (prefrosh_id) REFERENCES rotation_prefrosh (prefrosh_id)
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
