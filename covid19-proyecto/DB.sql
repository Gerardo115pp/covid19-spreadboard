  DROP DATABASE IF EXISTS `covid19`;
  CREATE DATABASE `covid19`;

  USE `covid19`;


  DROP TABLE IF EXISTS `continents`;
  CREATE TABLE `continents` (
    `uuid` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    PRIMARY KEY `pk_con_uuid`(`uuid`)
  ) ENGINE = InnoDB DEFAULT CHARSET='utf8';


  DROP TABLE IF EXISTS `countries`;
  CREATE TABLE `countries` (
    `uuid` CHAR(40) NOT NULL,
    `country_name` VARCHAR(255) NOT NULL,
    `population` INT NOT NULL,
    `cca2` VARCHAR(5) DEFAULT 'N/A',
    `cca3` VARCHAR(5) DEFAULT 'N/A',
    `ccn3` VARCHAR(5) DEFAULT 'N/A',
    `hospibed_per_kp` FLOAT(10,1) DEFAULT -1.0,
    `slug` VARCHAR(50) DEFAULT 'missing',
    `latitud` FLOAT(10,2),
    `longitud` FLOAT(10,2),
    `overall_status` CHAR(40),
    `continent` INT UNSIGNED,
    CONSTRAINT `fk_continent` FOREIGN KEY(`continent`) REFERENCES `continents`(`uuid`),
    PRIMARY KEY `pk_c_uuid`(`uuid`)
  ) ENGINE = InnoDB DEFAULT CHARSET='utf8';


  DROP TABLE IF EXISTS `overall_status`;
  CREATE TABLE `overall_status` (
    `uuid` CHAR(40) NOT NULL,
    `total_recoverys` INT DEFAULT 0,
    `total_deaths` INT DEFAULT 0,
    `cases` INT DEFAULT 0,
    `tests_made` INT DEFAULT 0,
    `arrival` TIMESTAMP,
    `index_case` VARCHAR(110) DEFAULT 'unknown',
    PRIMARY KEY `pk_oas_uuid`(`uuid`)
  ) ENGINE = InnoDB DEFAULT CHARSET='utf8';

  ALTER TABLE `countries` ADD CONSTRAINT `fk_overall_status` FOREIGN KEY(`overall_status`) REFERENCES `overall_status`(`uuid`);


  DROP TABLE IF EXISTS `daily_cases`;
  CREATE TABLE `daily_cases` (
    `uuid` CHAR(40) NOT NULL,
    `date` TIMESTAMP NOT NULL,
    `cases` INT NOT NULL,
    `deaths` INT NOT NULL,
    `recoverys` INT NOT NULL,
    `country` CHAR(40) NOT NULL,
    CONSTRAINT `fk_country` FOREIGN KEY(`country`) REFERENCES `countries`(`uuid`),
    PRIMARY KEY `pk_dc_uuid`(`uuid`)
  ) ENGINE = InnoDB DEFAULT CHARSET='utf8';


DROP TABLE IF EXISTS `infectedinfector`;
CREATE TABLE `infectedinfector` (
  `infected` CHAR(40) NOT NULL,
  `infector` CHAR(40) NOT NULL,
  CONSTRAINT `fk_infected` FOREIGN KEY(`infected`) REFERENCES `countries`(`uuid`),
  CONSTRAINT `fk_infector` FOREIGN KEY(`infector`) REFERENCES `countries`(`uuid`)
) ENGINE = InnoDB DEFAULT CHARSET='utf8';


CREATE USER 'covid-admin'@'localhost' IDENTIFIED BY 'KjlWTvxWpL21Y1k6sEjWTNpe4gfsdfs'; -- equal to a root user but only for this database, cannot creat more users
CREATE USER 'covid-manager'@'localhost' IDENTIFIED BY 'IKf00gPLlWiUfSjdFWTvxW'; --has all basic priviliges
CREATE USER 'covid-selecter'@'%' IDENTIFIED BY 'XzMzpDP5'; --most basic app operations of them all
CREATE USER 'covid-updater'@'%' IDENTIFIED BY 'BW3kzO2uW'; --app operations: update
CREATE USER 'covid-delete'@'%' IDENTIFIED BY 'Okf9DfZR'; --deleting operations by performed by the app 
CREATE USER 'covid-insert'@'%' IDENTIFIED BY 'wojmbctk'; --insertion operations made by the automatizaded cron job


GRANT ALL ON covid19.* TO 'covid-admin'@'localhost';
GRANT ALTER, INSERT, DROP, SELECT, UPDATE, DELETE ON covid19.* TO 'covid-manager'@'localhost';
GRANT SELECT, UPDATE ON covid19.* TO 'covid-updater'@'%';
GRANT INSERT, SELECT ON covid19.* TO 'covid-insert'@'%';
GRANT ALTER, INSERT, DROP, SELECT, UPDATE, DELETE ON covid19.* TO 'covid-delete'@'%';
GRANT SELECT ON covid19.* TO 'covid-selecter'@'%';



