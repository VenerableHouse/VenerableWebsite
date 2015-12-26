ALTER TABLE members
CHANGE fname first_name VARCHAR(255) NOT NULL;

ALTER TABLE members
CHANGE lname last_name VARCHAR(255) NOT NULL;

-- Don't use nicknames as alternate names... that ends poorly.
ALTER TABLE members
DROP nickname;

ALTER TABLE members
ADD alternate_name VARCHAR(255) AFTER last_name;

ALTER TABLE members
DROP usenickname;

ALTER TABLE members
CHANGE bday birthday DATE;

ALTER TABLE members
MODIFY email VARCHAR(255) NOT NULL;

ALTER TABLE members
DROP email2;

ALTER TABLE members
DROP status;

ALTER TABLE members
CHANGE matriculate_year matriculation_year YEAR;

ALTER TABLE members
CHANGE grad_year graduation_year YEAR;

ALTER TABLE members
CHANGE room_num room_number INTEGER;

ALTER TABLE members
CHANGE membership_type member_type INTEGER NOT NULL;

ALTER TABLE members
MODIFY uid VARCHAR(10) NOT NULL UNIQUE AFTER user_id;

ALTER TABLE members
DROP isabroad;

ALTER TABLE members
MODIFY msc INTEGER;

ALTER TABLE members
MODIFY major VARCHAR(255);

ALTER TABLE members
MODIFY building VARCHAR(255);

ALTER TABLE membership_types
CHANGE membership_type member_type INTEGER NOT NULL;

DROP VIEW IF EXISTS members_current;
DROP VIEW IF EXISTS members_alumni;
DROP VIEW IF EXISTS members_extra;

CREATE VIEW members_current AS
  SELECT user_id
  FROM members
  WHERE NOW() < CONCAT(graduation_year, '-07-01');

CREATE VIEW members_alumni AS
  SELECT user_id
  FROM members
  WHERE NOW() >= CONCAT(graduation_year, '-07-01');

CREATE VIEW members_extra AS
  SELECT user_id, CONCAT(IFNULL(alternate_name, first_name), ' ', last_name) AS name
  FROM members;

UPDATE updating_email_lists
SET query='SELECT email FROM members WHERE graduation_year = 2014 AND member_type = 1'
WHERE listname='2014';

UPDATE updating_email_lists
SET query='SELECT email FROM members WHERE graduation_year = 2015 AND member_type = 1'
WHERE listname='2015';

UPDATE updating_email_lists
SET query='SELECT email FROM members WHERE graduation_year = 2016 AND member_type = 1'
WHERE listname='2016';

UPDATE updating_email_lists
SET query='SELECT email FROM members WHERE graduation_year = 2017 AND member_type = 1'
WHERE listname='2017';

UPDATE updating_email_lists
SET query='SELECT email FROM members WHERE graduation_year = 2018 AND member_type = 1'
WHERE listname='2018';

UPDATE updating_email_lists
SET query='SELECT email FROM members_current NATURAL JOIN members WHERE member_type in (1, 4)'
WHERE listname='members';

UPDATE updating_email_lists
SET query='SELECT email FROM members_current NATURAL JOIN members WHERE member_type in (1, 2, 4)'
WHERE listname='socials';

-- Clear out empty strings.
UPDATE members SET phone=NULL WHERE phone='';
UPDATE members SET building=NULL WHERE building='';
UPDATE members SET major=NULL WHERE major='';
