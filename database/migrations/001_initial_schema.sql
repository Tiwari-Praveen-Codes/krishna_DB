-- Migration 001: Initial Schema Provisioning
-- Creates the normalized 10 tables if not already existing.

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
    CONSTRAINT `fk_school_records_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    CONSTRAINT `fk_semester_results_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_code` VARCHAR(50) NOT NULL UNIQUE,
    `subject_name` VARCHAR(150) NOT NULL,
    `subject_type` ENUM('Theory', 'Lab') NOT NULL,
    `credits` DOUBLE NOT NULL DEFAULT 3.0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    CONSTRAINT `fk_marks_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    CONSTRAINT `fk_attendance_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `gap_years` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `start_year` INT NOT NULL,
    `end_year` INT NOT NULL,
    `reason_category` ENUM('Academic', 'Medical', 'Personal', 'Other') NOT NULL,
    `notes` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_gap_years_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
