#
# DROP DATABASE IF EXISTS util_test;
#
# #if (server == "MySQL") and (int(version) >= 80000)
GRANT ALL ON *.* TO root@localhost WITH GRANT OPTION;
-- above is a misfeature of mysql 8.0 grant definition
# #endif
CREATE DATABASE util_test;
CREATE TABLE util_test.t1 (a char(30)) ENGINE=MEMORY;
INSERT INTO util_test.t1 VALUES ("01 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("02 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("03 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("04 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("05 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("06 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("07 Test Basic database example"); 

CREATE TABLE util_test.t2 (a char(30)) ENGINE=MYISAM;
INSERT INTO util_test.t2 VALUES ("11 Test Basic database example"); 
INSERT INTO util_test.t2 VALUES ("12 Test Basic database example"); 
INSERT INTO util_test.t2 VALUES ("13 Test Basic database example");
INSERT INTO util_test.t2 VALUES (NULL);

CREATE TABLE util_test.t3 (a int not null auto_increment, b varchar(30), primary key(a)) ENGINE=InnoDB;
INSERT INTO util_test.t3 (b) VALUES ("14 test fkeys");
INSERT INTO util_test.t3 (b) VALUES ("15 test fkeys");
INSERT INTO util_test.t3 (b) VALUES ("16 test fkeys");
INSERT INTO util_test.t3 (b) VALUES (NULL);

CREATE TABLE util_test.t4 (c int not null, d int not null, CONSTRAINT ref_t3 FOREIGN KEY(c) REFERENCES util_test.t3(a)) ENGINE=InnoDB;
INSERT INTO util_test.t4 VALUES (3, 2);

CREATE TABLE util_test.t5 (product_id int UNSIGNED NOT NULL AUTO_INCREMENT, name VARCHAR(20), base_price DECIMAL(20,2) UNSIGNED, tax_percentage DECIMAL(3,0) UNSIGNED, PRIMARY KEY(product_id)) ENGINE=INNODB;
INSERT INTO util_test.t5(name, base_price, tax_percentage) values ('kitkat',0.99, 19);
INSERT INTO util_test.t5(name, base_price, tax_percentage) values ('M&M', '5.99', 19);
INSERT INTO util_test.t5(name, base_price, tax_percentage) values ('milk', 0.67, 5);
INSERT INTO util_test.t5(name, base_price, tax_percentage) values ('Dr. Pepper', 0.99, 19);

CREATE FUNCTION util_test.f2 (base_price DECIMAL(20,2) UNSIGNED, tax_percentage DECIMAL(3,0) UNSIGNED) RETURNS DECIMAL (21,2) UNSIGNED DETERMINISTIC RETURN base_price + base_price*(tax_percentage/100);

CREATE VIEW util_test.v2 AS SELECT name, util_test.f2(t5.base_price, t5.tax_percentage) AS price FROM util_test.t5;

CREATE PROCEDURE util_test.p1(p1 CHAR(20)) INSERT INTO util_test.t1 VALUES ("50");

CREATE TRIGGER util_test.trg AFTER INSERT ON util_test.t1 FOR EACH ROW INSERT INTO util_test.t2 VALUES('Test objects count');

CREATE FUNCTION util_test.f1() RETURNS INT DETERMINISTIC RETURN (SELECT 1);

CREATE VIEW util_test.v1 as SELECT * FROM util_test.t1;

CREATE EVENT util_test.e1 ON SCHEDULE EVERY 1 YEAR DISABLE DO DELETE FROM util_test.t1 WHERE a = "not there";

CREATE USER `joe_wildcard`@`%`;

CREATE USER `joe`@`user`;

GRANT ALL ON util_test.* TO `joe`@`user`;

GRANT ALL ON util_test.* TO `joe_wildcard`@`%`;
