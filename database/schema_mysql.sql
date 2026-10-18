-- ==============================================================================
-- ScholarTrack Academic Progression DBMS — MySQL 8.0 Schema
-- Database: student_ledger
-- Relational 3NF Architecture with Foreign Key Constraints & Indexes
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS `student_ledger` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `student_ledger`;

-- ------------------------------------------------------------------------------
-- 1. STUDENTS TABLE (Core Student Entity)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `students` (
    `student_id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_name` VARCHAR(150) NOT NULL,
    `roll_no` VARCHAR(50) NOT NULL UNIQUE,
    `branch` VARCHAR(100) NOT NULL,
    `admission_year` INT NOT NULL,
    `email` VARCHAR(150) UNIQUE,
    `current_status` ENUM('Active', 'Graduated', 'On Hold', 'Discontinued') NOT NULL DEFAULT 'Active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `chk_admission_year` CHECK (`admission_year` >= 1900 AND `admission_year` <= 2100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_students_roll_no` ON `students` (`roll_no`);
CREATE INDEX `idx_students_name` ON `students` (`student_name`);
CREATE INDEX `idx_students_branch` ON `students` (`branch`);

-- ------------------------------------------------------------------------------
-- 2. SCHOOL RECORDS TABLE (Prior Education: SSC & HSC)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `school_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `level` ENUM('SSC', 'HSC') NOT NULL,
    `board` VARCHAR(100) NOT NULL,
    `passing_year` INT NOT NULL,
    `marks_obtained` DOUBLE NOT NULL,
    `marks_total` DOUBLE NOT NULL,
    `percentage` DOUBLE NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `uk_student_school_level` UNIQUE (`student_id`, `level`),
    CONSTRAINT `fk_school_records_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
    CONSTRAINT `chk_school_marks` CHECK (`marks_obtained` >= 0 AND `marks_obtained` <= `marks_total` AND `marks_total` > 0),
    CONSTRAINT `chk_school_percentage` CHECK (`percentage` >= 0.0 AND `percentage` <= 100.0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_school_student` ON `school_records` (`student_id`);

-- ------------------------------------------------------------------------------
-- 3. SEMESTER RESULTS TABLE (Academic Progression Tracking)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `semester_results` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `semester_number` INT NOT NULL,
    `academic_year` VARCHAR(20) NOT NULL,
    `sgpa` DOUBLE NOT NULL,
    `cgpa` DOUBLE NOT NULL,
    `result_status` ENUM('Pass', 'ATKT', 'Fail', 'Pending') NOT NULL DEFAULT 'Pass',
    `backlog_count` INT NOT NULL DEFAULT 0,
    `is_gap_after` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `uk_student_semester` UNIQUE (`student_id`, `semester_number`),
    CONSTRAINT `fk_semester_results_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
    CONSTRAINT `chk_semester_number` CHECK (`semester_number` >= 1 AND `semester_number` <= 10),
    CONSTRAINT `chk_sgpa` CHECK (`sgpa` >= 0.0 AND `sgpa` <= 10.0),
    CONSTRAINT `chk_cgpa` CHECK (`cgpa` >= 0.0 AND `cgpa` <= 10.0),
    CONSTRAINT `chk_backlogs` CHECK (`backlog_count` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_sem_results_student` ON `semester_results` (`student_id`);
CREATE INDEX `idx_sem_results_year` ON `semester_results` (`academic_year`);

-- ------------------------------------------------------------------------------
-- 4. SUBJECTS TABLE (Normalized Course Registry)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_code` VARCHAR(50) NOT NULL UNIQUE,
    `subject_name` VARCHAR(150) NOT NULL,
    `subject_type` ENUM('Theory', 'Lab') NOT NULL,
    `credits` DOUBLE NOT NULL DEFAULT 3.0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `chk_subject_credits` CHECK (`credits` >= 0.0 AND `credits` <= 10.0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_subjects_code` ON `subjects` (`subject_code`);

-- ------------------------------------------------------------------------------
-- 5. SUBJECT MARKS TABLE (Detailed Exam Breakdown)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `subject_marks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `semester_result_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `marks_obtained` DOUBLE NOT NULL,
    `marks_total` DOUBLE NOT NULL,
    `passing_marks` DOUBLE NOT NULL DEFAULT 40.0,
    `component` ENUM('Internal', 'External', 'Practical', 'Final') NOT NULL DEFAULT 'Final',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `uk_sem_subject` UNIQUE (`semester_result_id`, `subject_id`, `component`),
    CONSTRAINT `fk_marks_semester_result` FOREIGN KEY (`semester_result_id`) REFERENCES `semester_results` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_marks_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `chk_marks_obtained` CHECK (`marks_obtained` >= 0 AND `marks_obtained` <= `marks_total` AND `marks_total` > 0),
    CONSTRAINT `chk_passing_marks` CHECK (`passing_marks` >= 0 AND `passing_marks` <= `marks_total`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_marks_sem_result` ON `subject_marks` (`semester_result_id`);
CREATE INDEX `idx_marks_subject` ON `subject_marks` (`subject_id`);

-- ------------------------------------------------------------------------------
-- 6. ATTENDANCE TABLE (Held vs Attended Monitoring)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `attendance` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `academic_year` VARCHAR(20) NOT NULL,
    `semester_number` INT NOT NULL,
    `classes_held` INT NOT NULL,
    `classes_attended` INT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `uk_student_subject_attendance` UNIQUE (`student_id`, `subject_id`, `academic_year`, `semester_number`),
    CONSTRAINT `fk_attendance_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_attendance_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `chk_classes_held` CHECK (`classes_held` >= 0),
    CONSTRAINT `chk_classes_attended` CHECK (`classes_attended` >= 0 AND `classes_attended` <= `classes_held`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_attendance_student` ON `attendance` (`student_id`);
CREATE INDEX `idx_attendance_subject` ON `attendance` (`subject_id`);

-- ------------------------------------------------------------------------------
-- 7. GAP YEARS TABLE (Academic Leave & Gap Documentation)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `gap_years` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `start_year` INT NOT NULL,
    `end_year` INT NOT NULL,
    `reason_category` ENUM('Academic', 'Medical', 'Personal', 'Other') NOT NULL,
    `notes` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_gap_years_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
    CONSTRAINT `chk_gap_years` CHECK (`end_year` >= `start_year` AND `start_year` >= 1990)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_gap_years_student` ON `gap_years` (`student_id`);

-- ------------------------------------------------------------------------------
-- 8. ACTIVITIES TABLE (Technical & Co-Curricular Portfolio)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `activities` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `activity_type` ENUM('Technical', 'Co-curricular', 'Extra-curricular') NOT NULL,
    `organization` VARCHAR(150),
    `activity_date` DATE,
    `description` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_activities_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_activities_student` ON `activities` (`student_id`);

-- ------------------------------------------------------------------------------
-- 9. SEMINARS TABLE (Paper Presentations & Expert Talks)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `seminars` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `seminar_scope` ENUM('Internal', 'External') NOT NULL,
    `organizer` VARCHAR(150),
    `seminar_date` DATE,
    `certificate_url` VARCHAR(500),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_seminars_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_seminars_student` ON `seminars` (`student_id`);

-- ------------------------------------------------------------------------------
-- 10. CERTIFICATES TABLE (Verified Credentials & Badges)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `certificates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `issuer` VARCHAR(150) NOT NULL,
    `category` ENUM('Course', 'Hackathon', 'Internship', 'Achievement', 'Seminar', 'Other') NOT NULL,
    `issue_date` DATE,
    `credential_url` VARCHAR(500),
    `notes` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_certificates_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `idx_certificates_student` ON `certificates` (`student_id`);

-- ------------------------------------------------------------------------------
-- 11. LEGACY TABLE (Preserved for Backward Compatibility)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `student_performance` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `semester` INT NOT NULL,
    `sgpa` DOUBLE,
    `cgpa` DOUBLE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `uk_student_perf_sem` UNIQUE (`student_id`, `semester`),
    CONSTRAINT `fk_perf_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
