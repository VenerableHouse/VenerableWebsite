/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE hassle_events (
  hassle_event_id int(11) NOT NULL,
  user_id int(11) NOT NULL,
  room_number int(11) NOT NULL,
  PRIMARY KEY (hassle_event_id),
  UNIQUE KEY user_id (user_id),
  UNIQUE KEY room_number (room_number),
  CONSTRAINT hassle_events_ibfk_1 FOREIGN KEY (user_id) REFERENCES hassle_participants (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT hassle_events_ibfk_2 FOREIGN KEY (room_number) REFERENCES hassle_rooms (room_number) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE hassle_participants (
  user_id int(11) NOT NULL,
  PRIMARY KEY (user_id),
  CONSTRAINT hassle_participants_ibfk_1 FOREIGN KEY (user_id) REFERENCES members (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE hassle_roommates (
  user_id int(11) NOT NULL,
  roommate_id int(11) NOT NULL,
  PRIMARY KEY (roommate_id),
  KEY hassle_roommates_ibfk_1 (user_id),
  CONSTRAINT hassle_roommates_ibfk_1 FOREIGN KEY (user_id) REFERENCES hassle_events (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT hassle_roommates_ibfk_2 FOREIGN KEY (roommate_id) REFERENCES hassle_participants (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE hassle_rooms (
  room_number int(11) NOT NULL,
  PRIMARY KEY (room_number),
  CONSTRAINT hassle_rooms_ibfk_1 FOREIGN KEY (room_number) REFERENCES rooms (room_number) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE members (
  user_id int(11) NOT NULL,
  uid varchar(10) NOT NULL,
  first_name varchar(255) NOT NULL,
  last_name varchar(255) NOT NULL,
  preferred_name varchar(255) DEFAULT NULL,
  birthday date DEFAULT NULL,
  email varchar(255) NOT NULL,
  matriculation_year year(4) DEFAULT NULL,
  graduation_year year(4) DEFAULT NULL,
  msc int(11) DEFAULT NULL,
  phone varchar(64) DEFAULT NULL,
  building varchar(255) DEFAULT NULL,
  room_number int(11) DEFAULT NULL,
  member_type int(11) NOT NULL,
  major varchar(255) DEFAULT NULL,
  create_account_key char(32) DEFAULT NULL,
  PRIMARY KEY (user_id),
  UNIQUE KEY uid (uid),
  KEY members_ibfk_1 (member_type),
  CONSTRAINT members_ibfk_1 FOREIGN KEY (member_type) REFERENCES membership_types (member_type)
);
/*!40101 SET character_set_client = @saved_cs_client */;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `members_alumni` (
  user_id tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `members_current` (
  user_id tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `members_extra` (
  user_id tinyint NOT NULL,
  name tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE membership_types (
  member_type int(11) NOT NULL,
  membership_desc varchar(32) NOT NULL,
  membership_desc_short varchar(32) NOT NULL,
  PRIMARY KEY (member_type),
  UNIQUE KEY membership_desc (membership_desc),
  UNIQUE KEY membership_desc_short (membership_desc_short)
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE office_assignments (
  assignment_id int(11) NOT NULL,
  office_id int(11) NOT NULL,
  user_id int(11) NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  PRIMARY KEY (assignment_id),
  KEY office_members_ibfk_2 (user_id),
  KEY office_members_ibfk_1 (office_id),
  CONSTRAINT office_assignments_ibfk_1 FOREIGN KEY (office_id) REFERENCES offices (office_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT office_assignments_ibfk_2 FOREIGN KEY (user_id) REFERENCES members (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `office_assignments_current` (
  assignment_id tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `office_assignments_future` (
  assignment_id tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `office_assignments_past` (
  assignment_id tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE office_permissions (
  office_id int(11) NOT NULL,
  permission_id int(11) NOT NULL,
  PRIMARY KEY (office_id,permission_id),
  KEY permission_id (permission_id),
  CONSTRAINT office_permissions_ibfk_1 FOREIGN KEY (office_id) REFERENCES offices (office_id) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE offices (
  office_id int(11) NOT NULL,
  office_name varchar(32) NOT NULL,
  is_excomm tinyint(1) NOT NULL,
  is_ucc tinyint(1) NOT NULL,
  office_email varchar(255) DEFAULT NULL,
  office_order int(11) DEFAULT NULL,
  is_active tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (office_id)
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE rooms (
  room_number int(11) NOT NULL,
  alley int(11) NOT NULL,
  coords varchar(255) DEFAULT NULL,
  PRIMARY KEY (room_number)
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE updating_email_lists (
  listname varchar(20) NOT NULL DEFAULT '',
  `query` text NOT NULL,
  PRIMARY KEY (listname)
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE updating_email_lists_additions (
  listname varchar(20) NOT NULL DEFAULT '',
  email varchar(64) NOT NULL DEFAULT '',
  PRIMARY KEY (listname,email)
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE user_permissions (
  user_id int(11) NOT NULL,
  permission_id int(11) NOT NULL,
  PRIMARY KEY (user_id,permission_id),
  KEY permission_id (permission_id),
  CONSTRAINT user_permissions_ibfk_1 FOREIGN KEY (user_id) REFERENCES `users` (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE users (
  user_id int(11) NOT NULL,
  username varchar(32) NOT NULL,
  password_hash varchar(255) NOT NULL,
  lastlogin datetime DEFAULT NULL,
  password_reset_key char(32) DEFAULT NULL,
  password_reset_expiration datetime DEFAULT NULL,
  PRIMARY KEY (user_id),
  UNIQUE KEY username (username),
  CONSTRAINT users_ibfk_1 FOREIGN KEY (user_id) REFERENCES members (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50001 DROP TABLE IF EXISTS members_alumni*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=root@localhost SQL SECURITY DEFINER */
/*!50001 VIEW members_alumni AS select members.user_id AS user_id from members where (now() >= concat(members.graduation_year,'-07-01')) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP TABLE IF EXISTS members_current*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=root@localhost SQL SECURITY DEFINER */
/*!50001 VIEW members_current AS select members.user_id AS user_id from members where (now() < concat(members.graduation_year,'-07-01')) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP TABLE IF EXISTS members_extra*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=root@localhost SQL SECURITY DEFINER */
/*!50001 VIEW members_extra AS select members.user_id AS user_id,concat(ifnull(members.preferred_name,members.first_name),' ',members.last_name) AS `name` from members */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP TABLE IF EXISTS office_assignments_current*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=root@localhost SQL SECURITY DEFINER */
/*!50001 VIEW office_assignments_current AS select office_assignments.assignment_id AS assignment_id from office_assignments where ((office_assignments.start_date < now()) and (office_assignments.end_date > now())) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP TABLE IF EXISTS office_assignments_future*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=root@localhost SQL SECURITY DEFINER */
/*!50001 VIEW office_assignments_future AS select office_assignments.assignment_id AS assignment_id from office_assignments where (office_assignments.start_date > now()) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP TABLE IF EXISTS office_assignments_past*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=root@localhost SQL SECURITY DEFINER */
/*!50001 VIEW office_assignments_past AS select office_assignments.assignment_id AS assignment_id from office_assignments where ((office_assignments.start_date < now()) and (office_assignments.end_date < now())) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

