-- Migration 002: Safe Migration from Legacy student_performance to semester_results
-- Preserves existing tables and prevents data loss.

INSERT INTO `semester_results` (`student_id`, `semester_number`, `academic_year`, `sgpa`, `cgpa`, `result_status`, `backlog_count`, `is_gap_after`)
SELECT 
    sp.`student_id`,
    sp.`semester` AS `semester_number`,
    CONCAT(COALESCE(s.`admission_year` + FLOOR((sp.`semester` - 1) / 2), 2024), '-', COALESCE(s.`admission_year` + FLOOR((sp.`semester` - 1) / 2) + 1, 2025)) AS `academic_year`,
    COALESCE(sp.`sgpa`, 0.0),
    COALESCE(sp.`cgpa`, 0.0),
    CASE 
        WHEN COALESCE(sp.`sgpa`, 0.0) >= 4.0 THEN 'Pass'
        WHEN COALESCE(sp.`sgpa`, 0.0) >= 2.0 THEN 'ATKT'
        ELSE 'Fail'
    END AS `result_status`,
    0 AS `backlog_count`,
    0 AS `is_gap_after`
FROM `student_performance` sp
JOIN `students` s ON sp.`student_id` = s.`student_id`
ON DUPLICATE KEY UPDATE
    `sgpa` = VALUES(`sgpa`),
    `cgpa` = VALUES(`cgpa`),
    `result_status` = VALUES(`result_status`);
