CREATE DATABASE IF NOT EXISTS placement_scheduler CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'scheduler'@'%' IDENTIFIED BY 'scheduler';
GRANT ALL PRIVILEGES ON placement_scheduler.* TO 'scheduler'@'%';
FLUSH PRIVILEGES;
