/*
 * Populates the database with a static set of test data.
 */

INSERT INTO membership_types
  (member_type, membership_desc, membership_desc_short)
  VALUES
  (1, 'Full Member', 'Full'),
  (2, 'Social Member', 'Social'),
  (3, 'Associate Member', 'Associate'),
  (4, 'Resident Associate', 'RA');

INSERT INTO members
  (uid, first_name, last_name, preferred_name, email,
    member_type, matriculation_year, graduation_year)
  VALUES
  -- user_id = 1
  ('1000001', 'Twilight', 'Sparkle', 'Princess Twilight', 'twilight@canter.lot',
    1, 2010, 2014),
  -- user_id = 2
  ('1000002', 'Rainbow', 'Dash', NULL, 'rainbow.dash@pony.ville',
    1, 2010, 2014),
  -- user_id = 3
  ('1000003', 'Princess', 'Luna', NULL, 'luna@canter.lot',
    2, 2007, 2009),
  -- user_id = 4
  ('1000004', 'Princess', 'Celestia', NULL, 'celestia@canter.lot',
    1, 2007, 2009),
  -- user_id = 5
  -- Should always appear in the current memberlist.
  ('1000005', 'Apple', 'Bloom', NULL, 'apple.bloom@pony.ville',
    2, 2015, 2025),
  -- user_id = 6
  ('1000006', 'Sweetie', 'Belle', NULL, 'sweetie.belle@pony.ville',
    2, 2015, 2025),
  -- user_id = 7
  ('1000007', 'Scoot', 'Aloo', NULL, 'scoot@pony.ville',
    2, 2015, 2025),
  -- user_id = 8
  ('1000008', 'Princess', 'Derpy', NULL, 'muffins@pony.ville',
    3, 2010, NULL),
  -- user_id = 9
  ('1000009', 'Star', 'Swirl', NULL, 'star.swirl@canter.lot',
    4, 2000, NULL);

INSERT INTO users
  (user_id, username, password_hash)
  VALUES
  -- password = booksbooksbooks
  (1, 'twilight', '$pbkdf2_sha256$100000$y6M578psDb7b0K5W6FOCEs75$6fbc37a49ec8074cbd6fe31fe73da20c49ae9392ebdf256156856289c9001130'),
  -- password = rainboom
  (2, 'dashie', '$pbkdf2_sha256$100000$5GtZuPlmtO3deXIOyEFwlS16$971393a31eaeb0446659b77117e5185c808e309e06113f2a7960ccd551a95bd9'),
  -- password = PrincessOfTheNight
  (3, 'luna', '$pbkdf2_sha256$100000$iXtMjvmJ1VzFRyrwmpQ7y9CT$ff5d9f62daaaad885b845ab2f3fea78069b0b4b4a03f089c46115d4981ad8f97');

-- ------------
-- BUDGET STUFF
-- ------------

INSERT INTO budget_accounts
  (account_name, initial_balance)
VALUES
  ("MegaBank", 10000.00),
  ("Piggy Bank", 00.50);

INSERT INTO budget_fyears
  (fyear_num, start_date, end_date)
VALUES
  -- fyear_id = 1
  (2016, "2015-09-23", "2016-09-18"),
  -- fyear_id = 2
  (2017, "2016-09-19", "2017-09-18"),
  -- fyear_id = 3
  (2018, "2017-09-19", "2018-09-18"),
  -- fyear_id = 4
  (2019, "2018-09-19", "2019-09-18"),
  -- fyear_id = 5
  (2020, "2019-09-19", "2020-09-18");

INSERT INTO budget_budgets
  (budget_name, fyear_id, starting_amount)
VALUES
  ("Soc Team", 4, 600), 
  ("Ath Team", 4, 400);
