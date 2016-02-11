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
  (uid, first_name, last_name, preferred_name, email, member_type)
  VALUES
  -- user_id = 1
  ('1000001', 'Twilight', 'Sparkle', 'Princess Twilight', 'twilight@canter.lot', 1),
  -- user_id = 2
  ('1000002', 'Rainbow', 'Dash', NULL, 'rainbow.dash@pony.ville', 1),
  -- user_id = 3
  ('1000003', 'Princess', 'Luna', NULL, 'luna@canter.lot', 1),
  -- user_id = 4
  ('1000004', 'Princess', 'Celestia', NULL, 'celestia@canter.lot', 1),
  -- user_id = 5
  ('1000005', 'Apple', 'Bloom', NULL, 'apple.bloom@pony.ville', 2),
  -- user_id = 6
  ('1000006', 'Sweetie', 'Belle', NULL, 'sweetie.belle@pony.ville', 2),
  -- user_id = 7
  ('1000007', 'Scoot', 'Aloo', NULL, 'scoot@pony.ville', 2),
  -- user_id = 8
  ('1000008', 'Princess', 'Derpy', NULL, 'muffins@pony.ville', 3),
  -- user_id = 9
  ('1000009', 'Star', 'Swirl', NULL, 'star.swirl@canter.lot', 4);

INSERT INTO users
  (user_id, username, password_hash)
  VALUES
  -- password = booksbooksbooks
  (1, 'twilight', '$pbkdf2_sha256$100000$y6M578psDb7b0K5W6FOCEs75$6fbc37a49ec8074cbd6fe31fe73da20c49ae9392ebdf256156856289c9001130'),
  -- password = rainboom
  (2, 'dashie', '$pbkdf2_sha256$100000$5GtZuPlmtO3deXIOyEFwlS16$971393a31eaeb0446659b77117e5185c808e309e06113f2a7960ccd551a95bd9'),
  -- password = PrincessOfTheNight
  (3, 'luna', '$pbkdf2_sha256$100000$iXtMjvmJ1VzFRyrwmpQ7y9CT$ff5d9f62daaaad885b845ab2f3fea78069b0b4b4a03f089c46115d4981ad8f97');
