/**
 * ScholarTrack Academic Progression Management System
 * Comprehensive Frontend Application Engine
 */

let students = [];
let selectedStudentId = null;
let currentStudent = null;
let performanceChart = null;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initChart();
    loadSystemStats();
    loadStudents();
    loadSheetsStatus();
});

// Toast Notification Manager
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "danger") icon = "❌";
    if (type === "warning") icon = "⚠️";

    toast.innerHTML = `<span>${icon}</span> <div>${message}</div>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Navigation Tabs
function initNavigation() {
    const navButtons = document.querySelectorAll(".nav-item button");
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll(".nav-item").forEach(item => {
        const btn = item.querySelector("button");
        if (btn && btn.getAttribute("data-tab") === tabId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    document.querySelectorAll(".tab-pane").forEach(pane => {
        if (pane.id === `tab-${tabId}`) {
            pane.classList.add("active");
        } else {
            pane.classList.remove("active");
        }
    });

    // Refresh context data based on tab
    if (tabId === "overview" && selectedStudentId) {
        loadStudentDashboard(selectedStudentId);
    } else if (tabId === "academics" && selectedStudentId) {
        loadAcademicsTab(selectedStudentId);
    } else if (tabId === "attendance" && selectedStudentId) {
        loadAttendanceTab(selectedStudentId);
    } else if (tabId === "portfolio" && selectedStudentId) {
        loadPortfolioTab(selectedStudentId);
    } else if (tabId === "sheets") {
        loadSheetsStatus();
    }
}

let gradeDistChart = null;
let theoryLabPieChart = null;
let courseMarksBarChart = null;
let attComplianceBarChart = null;

// Chart.js Master Analytics Suite (Line, Pie, Doughnut, and Bar Charts)
function initChart() {
    // 1. Performance Line Trend Chart (SGPA & CGPA)
    const ctxLine = document.getElementById("performanceChart");
    if (ctxLine) {
        performanceChart = new Chart(ctxLine, {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "SGPA (Semester GPA)",
                        data: [],
                        borderColor: "#2563eb",
                        backgroundColor: "rgba(37, 99, 235, 0.12)",
                        borderWidth: 3,
                        pointBackgroundColor: "#2563eb",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        tension: 0.35,
                        fill: true
                    },
                    {
                        label: "CGPA (Cumulative GPA)",
                        data: [],
                        borderColor: "#10b981",
                        backgroundColor: "rgba(16, 185, 129, 0.08)",
                        borderWidth: 3,
                        pointBackgroundColor: "#10b981",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        tension: 0.35,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: '600' }
                        }
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 10,
                        ticks: { stepSize: 2 },
                        title: { display: true, text: "Grade Point (0 - 10 Scale)", font: { weight: '600' } },
                        grid: { color: "rgba(226, 232, 240, 0.6)" }
                    },
                    x: {
                        title: { display: true, text: "Academic Progression", font: { weight: '600' } },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // 2. Grade Standing Distribution (Pie Chart)
    const ctxPie = document.getElementById("gradeDistChart");
    if (ctxPie) {
        gradeDistChart = new Chart(ctxPie, {
            type: "pie",
            data: {
                labels: ["Distinction (≥8.5)", "First Class (7.5-8.49)", "Higher Second (6.5-7.49)", "Pass Class (<6.5)"],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ["#8b5cf6", "#2563eb", "#10b981", "#f59e0b"],
                    borderWidth: 2,
                    borderColor: "#ffffff"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } }
                }
            }
        });
    }

    // 3. Theory vs Practical Performance (Doughnut Chart)
    const ctxDoughnut = document.getElementById("theoryLabPieChart");
    if (ctxDoughnut) {
        theoryLabPieChart = new Chart(ctxDoughnut, {
            type: "doughnut",
            data: {
                labels: ["Theory Coursework", "Laboratory Practical"],
                datasets: [{
                    data: [80, 85],
                    backgroundColor: ["#3b82f6", "#10b981"],
                    borderWidth: 2,
                    borderColor: "#ffffff"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } }
                }
            }
        });
    }

    // 4. Course Marks Bar Chart
    const ctxBar1 = document.getElementById("courseMarksBarChart");
    if (ctxBar1) {
        courseMarksBarChart = new Chart(ctxBar1, {
            type: "bar",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "Marks Obtained",
                        data: [],
                        backgroundColor: "#2563eb",
                        borderRadius: 4
                    },
                    {
                        label: "Passing Threshold",
                        data: [],
                        backgroundColor: "#fbbf24",
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { min: 0, max: 100, ticks: { stepSize: 20 }, grid: { color: "rgba(226, 232, 240, 0.6)" } },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } }
                }
            }
        });
    }

    // 5. Attendance Compliance Bar Chart
    const ctxBar2 = document.getElementById("attComplianceBarChart");
    if (ctxBar2) {
        attComplianceBarChart = new Chart(ctxBar2, {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Attendance %",
                    data: [],
                    backgroundColor: [],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { stepSize: 25 },
                        grid: { color: "rgba(226, 232, 240, 0.6)" }
                    },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const val = context.parsed.y;
                                return `Attendance: ${val}% (${val >= 75 ? 'Compliant' : 'Defaulter Warning'})`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// System Stats
async function loadSystemStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();
        if (data.success) {
            document.getElementById("statTotalStudents").textContent = data.total_students;
            document.getElementById("statTotalRecords").textContent = data.total_records;
            document.getElementById("statAverageCgpa").textContent = Number(data.average_cgpa).toFixed(2);
            document.getElementById("statTotalActivities").textContent = data.total_activities;
        }
    } catch (e) {
        console.error("Failed to load stats:", e);
    }
}

// Students Directory & Selection
async function loadStudents() {
    const tableBody = document.getElementById("studentTableBody");
    const countTag = document.getElementById("studentCountTag");
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading student records from MySQL...</td></tr>';

    try {
        const res = await fetch("/api/students");
        if (!res.ok) throw new Error("Could not fetch students");
        students = await res.json();

        countTag.textContent = `${students.length} students registered`;
        renderStudentsTable(students);

        if (students.length > 0) {
            const initialId = selectedStudentId || students[0].student_id;
            selectStudent(initialId);
        } else {
            clearStudentView();
        }
    } catch (err) {
        console.error(err);
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load students. Check database connection.</td></tr>';
        showToast("Error loading students list", "danger");
    }
}

function renderStudentsTable(list) {
    const tbody = document.getElementById("studentTableBody");
    tbody.innerHTML = "";

    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No students matched search criteria.</td></tr>';
        return;
    }

    list.forEach(s => {
        const tr = document.createElement("tr");
        if (Number(s.student_id) === Number(selectedStudentId)) {
            tr.classList.add("selected");
        }

        tr.innerHTML = `
            <td><strong>#${s.student_id}</strong></td>
            <td>
                <div style="font-weight: 600; color: #1e3a8a;">${s.student_name}</div>
                <small style="color: #64748b;">${s.email || 'No email'}</small>
            </td>
            <td><span class="badge-tag badge-blue">${s.roll_no}</span></td>
            <td>${s.branch}</td>
            <td>${s.admission_year}</td>
            <td>
                <div style="display: flex; gap: 6px;">
                    <button class="btn btn-sm btn-outline" onclick="selectStudent(${s.student_id})">Select</button>
                    <button class="btn btn-sm btn-outline" onclick="openEditStudentModal(${s.student_id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="confirmDeleteStudent(${s.student_id}, '${s.student_name.replace(/'/g, "\\'")}')">Delete</button>
                </div>
            </td>
        `;

        tr.addEventListener("click", (e) => {
            if (e.target.tagName !== "BUTTON") {
                selectStudent(s.student_id);
            }
        });

        tbody.appendChild(tr);
    });
}

function searchStudents() {
    const q = document.getElementById("studentSearchInput").value.toLowerCase().trim();
    const filtered = students.filter(s => 
        (s.student_name || "").toLowerCase().includes(q) ||
        (s.roll_no || "").toLowerCase().includes(q) ||
        (s.branch || "").toLowerCase().includes(q)
    );
    renderStudentsTable(filtered);
}

async function selectStudent(studentId) {
    selectedStudentId = Number(studentId);
    currentStudent = students.find(s => Number(s.student_id) === selectedStudentId);

    // Update row highlighting
    document.querySelectorAll("#studentTableBody tr").forEach(row => {
        row.classList.remove("selected");
    });

    renderStudentsTable(students);
    updateActiveStudentBanner();
    await loadStudentDashboard(selectedStudentId);
}

function updateActiveStudentBanner() {
    if (!currentStudent) return;
    document.getElementById("activeStudentName").textContent = currentStudent.student_name;
    document.getElementById("activeStudentMeta").textContent = 
        `Roll: ${currentStudent.roll_no} • ${currentStudent.branch} • Admission Year: ${currentStudent.admission_year}`;
    document.getElementById("activeStudentInitial").textContent = 
        (currentStudent.student_name || "S").charAt(0).toUpperCase();

    // Fill CGPA calculator current inputs
    const cgpaInput = document.getElementById("calcCurrentCgpa");
    if (cgpaInput && !cgpaInput.value) {
        cgpaInput.value = "8.20";
    }
}

// Student Dashboard & Progression Data
async function loadStudentDashboard(studentId) {
    const statusLabel = document.getElementById("chartStatusText");
    statusLabel.textContent = "Loading academic records...";

    try {
        const res = await fetch(`/api/students/${studentId}/dashboard`);
        const data = await res.json();

        if (!data.success) throw new Error(data.message || "Failed to load dashboard");

        const progression = data.progression || [];
        const gapYears = data.gap_years || [];

        // Update Chart 1: Performance Line Trend
        const labels = progression.map(p => `Sem ${p.semester_number} (${p.academic_year})`);
        const sgpaData = progression.map(p => p.sgpa !== null ? Number(p.sgpa) : null);
        const cgpaData = progression.map(p => p.cgpa !== null ? Number(p.cgpa) : null);

        if (performanceChart) {
            performanceChart.data.labels = labels;
            performanceChart.data.datasets[0].data = sgpaData;
            performanceChart.data.datasets[1].data = cgpaData;
            performanceChart.update();
        }

        // Update Visual Charts with Analytics Data
        const analytics = data.analytics || {};

        // Chart 2: Grade Honours Distribution Pie Chart
        if (gradeDistChart && analytics.grade_distribution) {
            const gd = analytics.grade_distribution;
            gradeDistChart.data.datasets[0].data = [
                gd["Distinction"] || 0,
                gd["First Class"] || 0,
                gd["Higher Second"] || 0,
                gd["Pass Class"] || 0
            ];
            gradeDistChart.update();
        }

        // Chart 3: Theory vs Practical Doughnut Chart
        if (theoryLabPieChart && analytics.theory_lab_pie) {
            const tlp = analytics.theory_lab_pie;
            const theoryVal = tlp.find(item => item.subject_type === "Theory")?.avg_pct || 78;
            const labVal = tlp.find(item => item.subject_type === "Lab")?.avg_pct || 86;
            theoryLabPieChart.data.datasets[0].data = [theoryVal, labVal];
            theoryLabPieChart.update();
        }

        // Chart 4: Course Evaluation Marks Bar Chart
        if (courseMarksBarChart && analytics.subject_marks_chart) {
            const smc = analytics.subject_marks_chart;
            courseMarksBarChart.data.labels = smc.map(m => m.subject_code);
            courseMarksBarChart.data.datasets[0].data = smc.map(m => m.marks_obtained);
            courseMarksBarChart.data.datasets[1].data = smc.map(m => m.passing_marks);
            courseMarksBarChart.update();
        }

        // Chart 5: Attendance Compliance vs Threshold Bar Chart
        if (attComplianceBarChart && analytics.attendance_chart) {
            const att = analytics.attendance_chart;
            attComplianceBarChart.data.labels = att.map(a => a.subject_code);
            attComplianceBarChart.data.datasets[0].data = att.map(a => a.attendance_pct);
            attComplianceBarChart.data.datasets[0].backgroundColor = att.map(a => a.attendance_pct >= 75 ? "#10b981" : "#ef4444");
            attComplianceBarChart.update();
        }

        // Gap Year Indicator
        const gapBadge = document.getElementById("gapIndicatorBadge");
        if (data.has_gap) {
            gapBadge.innerHTML = `<span class="badge-tag badge-warning">⚠️ Academic Gap Year (${gapYears.length > 0 ? gapYears[0].reason_category : 'Detected'})</span>`;
        } else {
            gapBadge.innerHTML = `<span class="badge-tag badge-success">✓ Continuous Academic Progression</span>`;
        }

        // Summary Status
        statusLabel.textContent = progression.length > 0 
            ? `${progression.length} semester records loaded. Current CGPA: ${data.metrics.latest_cgpa.toFixed(2)}`
            : "No semester records found for this student.";

        // Render semester history table in Overview
        renderProgressionHistory(progression);

        // Update predictor fields
        if (progression.length > 0) {
            document.getElementById("calcCurrentCgpa").value = data.metrics.latest_cgpa.toFixed(2);
            document.getElementById("calcCompletedSems").value = progression.length;
        }

    } catch (err) {
        console.error("Dashboard loading error:", err);
        statusLabel.textContent = "Could not load performance records.";
    }
}

function renderProgressionHistory(records) {
    const container = document.getElementById("progressionHistoryTable");
    if (!container) return;

    if (records.length === 0) {
        container.innerHTML = '<tr><td colspan="7" class="text-center">No semester results recorded yet. Click "+ Add Semester Result" to add.</td></tr>';
        return;
    }

    container.innerHTML = "";
    records.forEach(r => {
        let statusBadge = `<span class="badge-tag badge-success">${r.result_status}</span>`;
        if (r.result_status === "ATKT") statusBadge = `<span class="badge-tag badge-warning">ATKT</span>`;
        if (r.result_status === "Fail") statusBadge = `<span class="badge-tag badge-danger">Fail</span>`;

        const row = document.createElement("tr");
        row.innerHTML = `
            <td><strong>Semester ${r.semester_number}</strong></td>
            <td>${r.academic_year}</td>
            <td><strong style="color: #2563eb;">${Number(r.sgpa).toFixed(2)}</strong></td>
            <td><strong style="color: #10b981;">${Number(r.cgpa).toFixed(2)}</strong></td>
            <td>${statusBadge}</td>
            <td>${r.backlog_count > 0 ? `<span class="badge-tag badge-danger">${r.backlog_count}</span>` : '0'}</td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="openSemesterMarksModal(${r.id}, ${r.semester_number})">View Marks</button>
                <button class="btn btn-sm btn-danger" onclick="deleteSemesterResult(${r.id})">Delete</button>
            </td>
        `;
        container.appendChild(row);
    });
}

function clearStudentView() {
    selectedStudentId = null;
    currentStudent = null;
    if (performanceChart) {
        performanceChart.data.labels = [];
        performanceChart.data.datasets[0].data = [];
        performanceChart.data.datasets[1].data = [];
        performanceChart.update();
    }
    if (gradeDistChart) {
        gradeDistChart.data.datasets[0].data = [0, 0, 0, 0];
        gradeDistChart.update();
    }
    if (theoryLabPieChart) {
        theoryLabPieChart.data.datasets[0].data = [0, 0];
        theoryLabPieChart.update();
    }
    if (courseMarksBarChart) {
        courseMarksBarChart.data.labels = [];
        courseMarksBarChart.data.datasets[0].data = [];
        courseMarksBarChart.data.datasets[1].data = [];
        courseMarksBarChart.update();
    }
    if (attComplianceBarChart) {
        attComplianceBarChart.data.labels = [];
        attComplianceBarChart.data.datasets[0].data = [];
        attComplianceBarChart.update();
    }
    document.getElementById("activeStudentName").textContent = "No Student Selected";
    document.getElementById("activeStudentMeta").textContent = "Select or register a student to view records";
}

// Student CRUD Modals
function openAddStudentModal() {
    document.getElementById("addStudentForm").reset();
    document.getElementById("addStudentModal").classList.add("open");
}

function closeAddStudentModal() {
    document.getElementById("addStudentModal").classList.remove("open");
}

async function submitAddStudent(event) {
    event.preventDefault();
    const payload = {
        student_name: document.getElementById("addStudentName").value.trim(),
        roll_no: document.getElementById("addStudentRoll").value.trim(),
        branch: document.getElementById("addStudentBranch").value.trim(),
        admission_year: parseInt(document.getElementById("addStudentYear").value),
        email: document.getElementById("addStudentEmail").value.trim()
    };

    try {
        const res = await fetch("/api/students", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (res.ok && result.success) {
            showToast(result.message, "success");
            closeAddStudentModal();
            await loadStudents();
            selectStudent(result.student_id);
            loadSystemStats();
        } else {
            showToast(result.message || "Failed to add student", "danger");
        }
    } catch (err) {
        showToast("Network error submitting student", "danger");
    }
}

async function openEditStudentModal(id) {
    try {
        const res = await fetch(`/api/students/${id}`);
        const data = await res.json();
        if (data.success) {
            const s = data.student;
            document.getElementById("editStudentId").value = s.student_id;
            document.getElementById("editStudentName").value = s.student_name;
            document.getElementById("editStudentRoll").value = s.roll_no;
            document.getElementById("editStudentBranch").value = s.branch;
            document.getElementById("editStudentYear").value = s.admission_year;
            document.getElementById("editStudentEmail").value = s.email || "";
            document.getElementById("editStudentStatus").value = s.current_status || "Active";
            document.getElementById("editStudentModal").classList.add("open");
        }
    } catch (e) {
        showToast("Could not load student for editing", "danger");
    }
}

function closeEditStudentModal() {
    document.getElementById("editStudentModal").classList.remove("open");
}

async function submitEditStudent(event) {
    event.preventDefault();
    const id = document.getElementById("editStudentId").value;
    const payload = {
        student_name: document.getElementById("editStudentName").value.trim(),
        roll_no: document.getElementById("editStudentRoll").value.trim(),
        branch: document.getElementById("editStudentBranch").value.trim(),
        admission_year: parseInt(document.getElementById("editStudentYear").value),
        email: document.getElementById("editStudentEmail").value.trim(),
        current_status: document.getElementById("editStudentStatus").value
    };

    try {
        const res = await fetch(`/api/students/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (res.ok && result.success) {
            showToast("Student profile updated successfully", "success");
            closeEditStudentModal();
            await loadStudents();
            selectStudent(id);
        } else {
            showToast(result.message || "Update failed", "danger");
        }
    } catch (e) {
        showToast("Error updating student profile", "danger");
    }
}

async function confirmDeleteStudent(id, name) {
    if (!confirm(`Are you sure you want to permanently delete student '${name}' (ID #${id}) and all associated academic, attendance, and portfolio records? This action cannot be undone.`)) {
        return;
    }

    try {
        const res = await fetch(`/api/students/${id}`, { method: "DELETE" });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast(result.message, "success");
            await loadStudents();
            loadSystemStats();
        } else {
            showToast(result.message || "Failed to delete student", "danger");
        }
    } catch (e) {
        showToast("Network error deleting student", "danger");
    }
}

// Academics Tab & Operations
async function loadAcademicsTab(studentId) {
    loadSchoolRecords(studentId);
    loadGapYears(studentId);
    loadStudentDashboard(studentId);
}

async function loadSchoolRecords(studentId) {
    const listEl = document.getElementById("schoolRecordsList");
    if (!listEl) return;
    try {
        const res = await fetch(`/api/students/${studentId}/school-records`);
        const data = await res.json();
        if (data.success) {
            const records = data.records;
            if (records.length === 0) {
                listEl.innerHTML = '<p class="text-muted">No SSC/HSC school records documented yet.</p>';
                return;
            }
            listEl.innerHTML = records.map(r => `
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${r.level}</strong> — ${r.board} (${r.passing_year})<br>
                        <small style="color: #64748b;">Marks: ${r.marks_obtained}/${r.marks_total} • Percentage: <strong>${r.percentage}%</strong></small>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deleteSchoolRecord(${r.id})">Delete</button>
                </div>
            `).join("");
        }
    } catch (e) {
        console.error("Error loading school records:", e);
    }
}

async function deleteSchoolRecord(id) {
    if (!confirm("Delete this school record?")) return;
    try {
        const res = await fetch(`/api/school-records/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast("School record removed", "success");
            loadSchoolRecords(selectedStudentId);
        }
    } catch (e) {
        showToast("Failed to delete record", "danger");
    }
}

function openAddSchoolRecordModal() {
    document.getElementById("addSchoolRecordForm").reset();
    document.getElementById("addSchoolRecordModal").classList.add("open");
}

function closeAddSchoolRecordModal() {
    document.getElementById("addSchoolRecordModal").classList.remove("open");
}

async function submitAddSchoolRecord(event) {
    event.preventDefault();
    if (!selectedStudentId) {
        showToast("Please select a student first", "warning");
        return;
    }

    const payload = {
        level: document.getElementById("schoolLevel").value,
        board: document.getElementById("schoolBoard").value.trim(),
        passing_year: parseInt(document.getElementById("schoolYear").value),
        marks_obtained: parseFloat(document.getElementById("schoolMarksObtained").value),
        marks_total: parseFloat(document.getElementById("schoolMarksTotal").value)
    };

    try {
        const res = await fetch(`/api/students/${selectedStudentId}/school-records`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast(result.message, "success");
            closeAddSchoolRecordModal();
            loadSchoolRecords(selectedStudentId);
        } else {
            showToast(result.message || "Failed to add school record", "danger");
        }
    } catch (e) {
        showToast("Error adding school record", "danger");
    }
}

// Semester Result CRUD
function openAddSemesterModal() {
    if (!selectedStudentId) {
        showToast("Please select a student first", "warning");
        return;
    }
    document.getElementById("addSemesterForm").reset();
    document.getElementById("addSemesterModal").classList.add("open");
}

function closeAddSemesterModal() {
    document.getElementById("addSemesterModal").classList.remove("open");
}

async function submitAddSemester(event) {
    event.preventDefault();
    const payload = {
        semester_number: parseInt(document.getElementById("semNumber").value),
        academic_year: document.getElementById("semYear").value.trim(),
        sgpa: parseFloat(document.getElementById("semSgpa").value),
        cgpa: parseFloat(document.getElementById("semCgpa").value),
        result_status: document.getElementById("semStatus").value,
        backlog_count: parseInt(document.getElementById("semBacklogs").value || 0),
        is_gap_after: document.getElementById("semGapAfter").checked
    };

    try {
        const res = await fetch(`/api/students/${selectedStudentId}/semester-results`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast(result.message, "success");
            closeAddSemesterModal();
            loadStudentDashboard(selectedStudentId);
            loadSystemStats();
        } else {
            showToast(result.message || "Failed to add semester result", "danger");
        }
    } catch (e) {
        showToast("Network error submitting result", "danger");
    }
}

async function deleteSemesterResult(id) {
    if (!confirm("Are you sure you want to delete this semester result and all related subject marks?")) return;
    try {
        const res = await fetch(`/api/semester-results/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Semester result deleted", "success");
            loadStudentDashboard(selectedStudentId);
            loadSystemStats();
        }
    } catch (e) {
        showToast("Error deleting semester result", "danger");
    }
}

// Semester Marks Modal
let currentResultIdForMarks = null;

async function openSemesterMarksModal(resultId, semNum) {
    currentResultIdForMarks = resultId;
    document.getElementById("marksModalTitle").textContent = `Semester ${semNum} Subject Marks`;
    await refreshSemesterMarks(resultId);
    await loadSubjectOptionsForMarks();
    document.getElementById("semesterMarksModal").classList.add("open");
}

function closeSemesterMarksModal() {
    document.getElementById("semesterMarksModal").classList.remove("open");
}

async function refreshSemesterMarks(resultId) {
    const tableBody = document.getElementById("marksTableBody");
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading subject marks...</td></tr>';

    try {
        const res = await fetch(`/api/semester-results/${resultId}/marks`);
        const data = await res.json();
        if (data.success) {
            const marks = data.marks;
            if (marks.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No subject marks recorded for this semester yet.</td></tr>';
                return;
            }
            tableBody.innerHTML = marks.map(m => `
                <tr>
                    <td><strong>${m.subject_code}</strong></td>
                    <td>${m.subject_name}</td>
                    <td><span class="badge-tag ${m.subject_type === 'Lab' ? 'badge-purple' : 'badge-blue'}">${m.subject_type}</span></td>
                    <td><strong>${m.marks_obtained}</strong> / ${m.marks_total}</td>
                    <td><span class="badge-tag ${m.pass_status === 'Pass' ? 'badge-success' : 'badge-danger'}">${m.pass_status}</span></td>
                    <td><button class="btn btn-sm btn-danger" onclick="deleteSubjectMark(${m.id})">Delete</button></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load marks.</td></tr>';
    }
}

async function loadSubjectOptionsForMarks() {
    const select = document.getElementById("markSubjectSelect");
    if (!select) return;
    try {
        const res = await fetch("/api/subjects");
        const data = await res.json();
        if (data.success) {
            select.innerHTML = '<option value="">-- Choose Subject --</option>' + 
                data.subjects.map(s => `<option value="${s.id}">${s.subject_code} - ${s.subject_name} (${s.subject_type})</option>`).join("");
        }
    } catch (e) {
        console.error("Could not load subjects:", e);
    }
}

async function submitAddSubjectMark(event) {
    event.preventDefault();
    if (!currentResultIdForMarks) return;

    const payload = {
        subject_id: parseInt(document.getElementById("markSubjectSelect").value),
        marks_obtained: parseFloat(document.getElementById("marksObtainedInput").value),
        marks_total: parseFloat(document.getElementById("marksTotalInput").value || 100),
        passing_marks: parseFloat(document.getElementById("passingMarksInput").value || 40),
        component: document.getElementById("markComponentSelect").value
    };

    try {
        const res = await fetch(`/api/semester-results/${currentResultIdForMarks}/marks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast("Mark recorded successfully", "success");
            document.getElementById("addMarkForm").reset();
            refreshSemesterMarks(currentResultIdForMarks);
        } else {
            showToast(result.message || "Failed to record mark", "danger");
        }
    } catch (e) {
        showToast("Error adding mark", "danger");
    }
}

async function deleteSubjectMark(markId) {
    if (!confirm("Delete this mark entry?")) return;
    try {
        const res = await fetch(`/api/marks/${markId}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Mark record removed", "success");
            refreshSemesterMarks(currentResultIdForMarks);
        }
    } catch (e) {
        showToast("Failed to delete mark", "danger");
    }
}

// Gap Years
async function loadGapYears(studentId) {
    const listEl = document.getElementById("gapYearsList");
    if (!listEl) return;
    try {
        const res = await fetch(`/api/students/${studentId}/gap-years`);
        const data = await res.json();
        if (data.success) {
            const gaps = data.gap_years;
            if (gaps.length === 0) {
                listEl.innerHTML = '<p class="text-muted">No academic gap years documented.</p>';
                return;
            }
            listEl.innerHTML = gaps.map(g => `
                <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #92400e;">Gap: ${g.start_year} - ${g.end_year}</strong> (${g.reason_category})<br>
                        <small style="color: #78350f;">${g.notes || 'No explanation specified'}</small>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deleteGapYear(${g.id})">Delete</button>
                </div>
            `).join("");
        }
    } catch (e) {
        console.error("Error loading gaps:", e);
    }
}

function openAddGapYearModal() {
    if (!selectedStudentId) {
        showToast("Please select a student first", "warning");
        return;
    }
    document.getElementById("addGapYearForm").reset();
    document.getElementById("addGapYearModal").classList.add("open");
}

function closeAddGapYearModal() {
    document.getElementById("addGapYearModal").classList.remove("open");
}

async function submitAddGapYear(event) {
    event.preventDefault();
    const payload = {
        start_year: parseInt(document.getElementById("gapStartYear").value),
        end_year: parseInt(document.getElementById("gapEndYear").value),
        reason_category: document.getElementById("gapCategory").value,
        notes: document.getElementById("gapNotes").value.trim()
    };

    try {
        const res = await fetch(`/api/students/${selectedStudentId}/gap-years`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast(result.message, "success");
            closeAddGapYearModal();
            loadGapYears(selectedStudentId);
            loadStudentDashboard(selectedStudentId);
        } else {
            showToast(result.message || "Failed to record gap year", "danger");
        }
    } catch (e) {
        showToast("Error adding gap year", "danger");
    }
}

async function deleteGapYear(id) {
    if (!confirm("Delete this gap year record?")) return;
    try {
        const res = await fetch(`/api/gap-years/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Gap year record deleted", "success");
            loadGapYears(selectedStudentId);
            loadStudentDashboard(selectedStudentId);
        }
    } catch (e) {
        showToast("Error deleting gap year", "danger");
    }
}

// Attendance & Analytics Tab
async function loadAttendanceTab(studentId) {
    const threshold = parseFloat(document.getElementById("attendanceThresholdInput").value || 75.0);
    loadAttendanceRecords(studentId, threshold);
    loadSubjectAnalytics(studentId);
    loadSubjectOptionsForAttendance();
}

async function loadAttendanceRecords(studentId, threshold) {
    const tableBody = document.getElementById("attendanceTableBody");
    tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Loading attendance metrics...</td></tr>';

    try {
        const res = await fetch(`/api/students/${studentId}/attendance?threshold=${threshold}`);
        const data = await res.json();
        if (data.success) {
            const summary = data.summary;
            document.getElementById("attTotalHeld").textContent = summary.total_held;
            document.getElementById("attTotalAttended").textContent = summary.total_attended;
            document.getElementById("attOverallPct").textContent = `${summary.overall_percentage}%`;
            document.getElementById("attWarningsCount").textContent = summary.warnings_count;

            const records = data.records;
            if (records.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No attendance records logged for this student.</td></tr>';
                return;
            }

            tableBody.innerHTML = records.map(a => {
                const pct = Number(a.attendance_percentage);
                let badge = `<span class="badge-tag badge-success">${pct}%</span>`;
                if (a.is_warning) {
                    badge = `<span class="badge-tag badge-danger">⚠️ ${pct}% (Below ${threshold}%)</span>`;
                }

                return `
                    <tr>
                        <td><strong>${a.subject_code}</strong></td>
                        <td>${a.subject_name}</td>
                        <td>${a.academic_year} (Sem ${a.semester_number})</td>
                        <td>${a.classes_held}</td>
                        <td>${a.classes_attended}</td>
                        <td>${badge}</td>
                        <td><button class="btn btn-sm btn-danger" onclick="deleteAttendanceRecord(${a.id})">Delete</button></td>
                    </tr>
                `;
            }).join("");
        }
    } catch (e) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error loading attendance.</td></tr>';
    }
}

async function loadSubjectAnalytics(studentId) {
    const breakdownEl = document.getElementById("theoryLabAnalytics");
    try {
        const res = await fetch(`/api/students/${studentId}/subject-analytics`);
        const data = await res.json();
        if (data.success) {
            document.getElementById("analyticsAvgPct").textContent = `${data.overall_average}%`;
            document.getElementById("analyticsFailedAttempts").textContent = data.failed_attempts;

            const breakdown = data.type_breakdown;
            breakdownEl.innerHTML = breakdown.map(b => `
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: ${b.subject_type === 'Theory' ? '#2563eb' : '#8b5cf6'};">${b.subject_type} Courses</strong>
                        <span class="badge-tag ${b.subject_type === 'Theory' ? 'badge-blue' : 'badge-purple'}">${b.avg_percentage}% Avg</span>
                    </div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                        Evaluations: ${b.total_evaluations} • Marks: ${b.total_marks_obtained}/${b.total_marks_possible} • Failed Attempts: ${b.failed_attempts}
                    </div>
                </div>
            `).join("");
        }
    } catch (e) {
        console.error("Analytics error:", e);
    }
}

async function loadSubjectOptionsForAttendance() {
    const select = document.getElementById("attSubjectSelect");
    if (!select) return;
    try {
        const res = await fetch("/api/subjects");
        const data = await res.json();
        if (data.success) {
            select.innerHTML = '<option value="">-- Choose Subject --</option>' +
                data.subjects.map(s => `<option value="${s.id}">${s.subject_code} - ${s.subject_name}</option>`).join("");
        }
    } catch (e) {
        console.error(e);
    }
}

function openAddAttendanceModal() {
    if (!selectedStudentId) {
        showToast("Please select a student first", "warning");
        return;
    }
    document.getElementById("addAttendanceForm").reset();
    document.getElementById("addAttendanceModal").classList.add("open");
}

function closeAddAttendanceModal() {
    document.getElementById("addAttendanceModal").classList.remove("open");
}

async function submitAddAttendance(event) {
    event.preventDefault();
    const payload = {
        subject_id: parseInt(document.getElementById("attSubjectSelect").value),
        academic_year: document.getElementById("attYear").value.trim(),
        semester_number: parseInt(document.getElementById("attSemester").value),
        classes_held: parseInt(document.getElementById("attHeld").value),
        classes_attended: parseInt(document.getElementById("attAttended").value)
    };

    try {
        const res = await fetch(`/api/students/${selectedStudentId}/attendance`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast("Attendance logged successfully", "success");
            closeAddAttendanceModal();
            loadAttendanceTab(selectedStudentId);
        } else {
            showToast(result.message || "Attendance validation failed", "danger");
        }
    } catch (e) {
        showToast("Error saving attendance", "danger");
    }
}

async function deleteAttendanceRecord(id) {
    if (!confirm("Delete this attendance entry?")) return;
    try {
        const res = await fetch(`/api/attendance/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Attendance entry deleted", "success");
            loadAttendanceTab(selectedStudentId);
        }
    } catch (e) {
        showToast("Error deleting attendance", "danger");
    }
}

// Portfolio: Activities, Seminars & Certificates Tab
let currentPortfolioSubTab = "activities";

function setPortfolioSubTab(subTab) {
    currentPortfolioSubTab = subTab;
    document.querySelectorAll(".portfolio-subtab-btn").forEach(btn => {
        if (btn.getAttribute("data-subtab") === subTab) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    document.getElementById("portfolio-activities-section").style.display = subTab === "activities" ? "block" : "none";
    document.getElementById("portfolio-seminars-section").style.display = subTab === "seminars" ? "block" : "none";
    document.getElementById("portfolio-certificates-section").style.display = subTab === "certificates" ? "block" : "none";

    if (selectedStudentId) {
        if (subTab === "activities") loadActivities(selectedStudentId);
        if (subTab === "seminars") loadSeminars(selectedStudentId);
        if (subTab === "certificates") loadCertificates(selectedStudentId);
    }
}

function loadPortfolioTab(studentId) {
    setPortfolioSubTab(currentPortfolioSubTab);
}

// Activities CRUD
async function loadActivities(studentId, filterType = "") {
    const container = document.getElementById("activitiesListContainer");
    container.innerHTML = '<p class="text-center">Loading student activities...</p>';
    try {
        const url = filterType ? `/api/students/${studentId}/activities?type=${encodeURIComponent(filterType)}` : `/api/students/${studentId}/activities`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            const list = data.activities;
            if (list.length === 0) {
                container.innerHTML = '<p class="text-muted">No activity records logged.</p>';
                return;
            }
            container.innerHTML = list.map(a => `
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="badge-tag badge-blue">${a.activity_type}</span>
                        <h4 style="margin: 6px 0 2px; font-size: 15px;">${a.title}</h4>
                        <div style="font-size: 13px; color: #64748b;">${a.organization || 'Independent'} • ${a.activity_date || 'Date N/A'}</div>
                        <p style="font-size: 13px; margin-top: 6px; color: #334155;">${a.description || ''}</p>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deleteActivity(${a.id})">Delete</button>
                </div>
            `).join("");
        }
    } catch (e) {
        container.innerHTML = '<p class="text-danger">Failed to load activities.</p>';
    }
}

function openAddActivityModal() {
    if (!selectedStudentId) {
        showToast("Please select a student first", "warning");
        return;
    }
    document.getElementById("addActivityForm").reset();
    document.getElementById("addActivityModal").classList.add("open");
}

function closeAddActivityModal() {
    document.getElementById("addActivityModal").classList.remove("open");
}

async function submitAddActivity(event) {
    event.preventDefault();
    const payload = {
        title: document.getElementById("actTitle").value.trim(),
        activity_type: document.getElementById("actType").value,
        organization: document.getElementById("actOrg").value.trim(),
        activity_date: document.getElementById("actDate").value,
        description: document.getElementById("actDesc").value.trim()
    };

    try {
        const res = await fetch(`/api/students/${selectedStudentId}/activities`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast("Activity recorded", "success");
            closeAddActivityModal();
            loadActivities(selectedStudentId);
            loadSystemStats();
        } else {
            showToast(result.message || "Failed to record activity", "danger");
        }
    } catch (e) {
        showToast("Network error submitting activity", "danger");
    }
}

async function deleteActivity(id) {
    if (!confirm("Delete this activity record?")) return;
    try {
        const res = await fetch(`/api/activities/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Activity removed", "success");
            loadActivities(selectedStudentId);
            loadSystemStats();
        }
    } catch (e) {
        showToast("Error deleting activity", "danger");
    }
}

// Seminars CRUD
async function loadSeminars(studentId) {
    const container = document.getElementById("seminarsListContainer");
    container.innerHTML = '<p class="text-center">Loading seminar presentations...</p>';
    try {
        const res = await fetch(`/api/students/${studentId}/seminars`);
        const data = await res.json();
        if (data.success) {
            const list = data.seminars;
            if (list.length === 0) {
                container.innerHTML = '<p class="text-muted">No seminar records logged.</p>';
                return;
            }
            container.innerHTML = list.map(s => `
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="badge-tag ${s.seminar_scope === 'Internal' ? 'badge-blue' : 'badge-purple'}">${s.seminar_scope} Seminar</span>
                        <h4 style="margin: 6px 0 2px; font-size: 15px;">${s.title}</h4>
                        <div style="font-size: 13px; color: #64748b;">Organizer: ${s.organizer || 'Academic Faculty'} • Date: ${s.seminar_date || 'N/A'}</div>
                        ${s.certificate_url ? `<div style="margin-top: 6px;"><a href="${s.certificate_url}" target="_blank" style="color: #2563eb; font-size: 12.5px; text-decoration: underline;">🔗 View Seminar Credential / Certificate</a></div>` : ''}
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deleteSeminar(${s.id})">Delete</button>
                </div>
            `).join("");
        }
    } catch (e) {
        container.innerHTML = '<p class="text-danger">Failed to load seminars.</p>';
    }
}

function openAddSeminarModal() {
    if (!selectedStudentId) {
        showToast("Please select a student first", "warning");
        return;
    }
    document.getElementById("addSeminarForm").reset();
    document.getElementById("addSeminarModal").classList.add("open");
}

function closeAddSeminarModal() {
    document.getElementById("addSeminarModal").classList.remove("open");
}

async function submitAddSeminar(event) {
    event.preventDefault();
    const payload = {
        title: document.getElementById("semTitle").value.trim(),
        seminar_scope: document.getElementById("semScope").value,
        organizer: document.getElementById("semOrganizer").value.trim(),
        seminar_date: document.getElementById("semDate").value,
        certificate_url: document.getElementById("semCertUrl").value.trim()
    };

    try {
        const res = await fetch(`/api/students/${selectedStudentId}/seminars`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast("Seminar logged", "success");
            closeAddSeminarModal();
            loadSeminars(selectedStudentId);
            loadSystemStats();
        } else {
            showToast(result.message || "Failed to add seminar", "danger");
        }
    } catch (e) {
        showToast("Error saving seminar", "danger");
    }
}

async function deleteSeminar(id) {
    if (!confirm("Delete this seminar entry?")) return;
    try {
        const res = await fetch(`/api/seminars/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Seminar removed", "success");
            loadSeminars(selectedStudentId);
            loadSystemStats();
        }
    } catch (e) {
        showToast("Error deleting seminar", "danger");
    }
}

// Certificates CRUD
async function loadCertificates(studentId, filterCat = "") {
    const container = document.getElementById("certificatesListContainer");
    container.innerHTML = '<p class="text-center">Loading certificates...</p>';
    try {
        const url = filterCat ? `/api/students/${studentId}/certificates?category=${encodeURIComponent(filterCat)}` : `/api/students/${studentId}/certificates`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            const list = data.certificates;
            if (list.length === 0) {
                container.innerHTML = '<p class="text-muted">No certificates logged.</p>';
                return;
            }
            container.innerHTML = list.map(c => `
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="badge-tag badge-purple">${c.category}</span>
                        <h4 style="margin: 6px 0 2px; font-size: 15px;">${c.title}</h4>
                        <div style="font-size: 13px; color: #64748b;">Issued by: <strong>${c.issuer}</strong> • Date: ${c.issue_date || 'N/A'}</div>
                        ${c.notes ? `<p style="font-size: 13px; margin-top: 4px; color: #475569;">${c.notes}</p>` : ''}
                        ${c.credential_url ? `<div style="margin-top: 6px;"><a href="${c.credential_url}" target="_blank" style="color: #2563eb; font-size: 12.5px; text-decoration: underline;">🔗 Verify Credential</a></div>` : ''}
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deleteCertificate(${c.id})">Delete</button>
                </div>
            `).join("");
        }
    } catch (e) {
        container.innerHTML = '<p class="text-danger">Failed to load certificates.</p>';
    }
}

function openAddCertificateModal() {
    if (!selectedStudentId) {
        showToast("Please select a student first", "warning");
        return;
    }
    document.getElementById("addCertificateForm").reset();
    document.getElementById("addCertificateModal").classList.add("open");
}

function closeAddCertificateModal() {
    document.getElementById("addCertificateModal").classList.remove("open");
}

async function submitAddCertificate(event) {
    event.preventDefault();
    const payload = {
        title: document.getElementById("certTitle").value.trim(),
        issuer: document.getElementById("certIssuer").value.trim(),
        category: document.getElementById("certCategory").value,
        issue_date: document.getElementById("certDate").value,
        credential_url: document.getElementById("certUrl").value.trim(),
        notes: document.getElementById("certNotes").value.trim()
    };

    try {
        const res = await fetch(`/api/students/${selectedStudentId}/certificates`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok && result.success) {
            showToast("Certificate added", "success");
            closeAddCertificateModal();
            loadCertificates(selectedStudentId);
            loadSystemStats();
        } else {
            showToast(result.message || "Failed to add certificate", "danger");
        }
    } catch (e) {
        showToast("Error adding certificate", "danger");
    }
}

async function deleteCertificate(id) {
    if (!confirm("Delete this certificate record?")) return;
    try {
        const res = await fetch(`/api/certificates/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Certificate removed", "success");
            loadCertificates(selectedStudentId);
            loadSystemStats();
        }
    } catch (e) {
        showToast("Error deleting certificate", "danger");
    }
}

// CGPA Target Predictor
async function calculateCgpaPrediction() {
    const payload = {
        current_cgpa: parseFloat(document.getElementById("calcCurrentCgpa").value),
        completed_sems: parseInt(document.getElementById("calcCompletedSems").value),
        total_sems: parseInt(document.getElementById("calcTotalSems").value || 8),
        desired_cgpa: parseFloat(document.getElementById("calcDesiredCgpa").value)
    };

    const resultBox = document.getElementById("calcResultBox");
    resultBox.style.display = "block";
    resultBox.innerHTML = '<p>Computing target required performance...</p>';

    try {
        const res = await fetch("/api/predict-cgpa", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            let statusColor = "#10b981";
            let statusTitle = "Target Achievable";
            if (data.status === "IMPOSSIBLE") {
                statusColor = "#ef4444";
                statusTitle = "Mathematically Impossible";
            } else if (data.status === "ALREADY_ACHIEVED") {
                statusColor = "#3b82f6";
                statusTitle = "Target Already Met / Exceeded";
            } else if (data.status === "COMPLETED") {
                statusColor = "#f59e0b";
                statusTitle = "Programme Finished";
            }

            resultBox.innerHTML = `
                <div style="border-left: 4px solid ${statusColor}; padding-left: 14px;">
                    <div style="color: ${statusColor}; font-weight: 700; font-size: 15px; margin-bottom: 4px;">
                        ${statusTitle}
                    </div>
                    <div style="font-size: 26px; font-weight: 800; margin: 8px 0;">
                        ${data.required_sgpa !== null ? `Required SGPA: ${data.required_sgpa.toFixed(2)}` : 'N/A'}
                    </div>
                    <div style="font-size: 14px; margin-bottom: 8px;">
                        ${data.advice}
                    </div>
                    <div class="calc-formula-display">
                        Formula: ${data.formula || 'N/A'}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; font-style: italic; margin-top: 10px;">
                        ⚠️ Note: ${data.assumptions}
                    </div>
                </div>
            `;
        } else {
            resultBox.innerHTML = `<div class="text-danger">⚠️ ${data.message}</div>`;
        }
    } catch (e) {
        resultBox.innerHTML = '<div class="text-danger">Error computing CGPA prediction.</div>';
    }
}

// Google Sheets Synchronization
async function loadSheetsStatus() {
    try {
        const res = await fetch("/api/sync/google-sheets/status");
        const data = await res.json();
        if (data.success) {
            document.getElementById("sheetIdDisplay").textContent = data.sheet_id;
            document.getElementById("serviceAccountDisplay").textContent = data.service_account_file;
            
            const last = data.last_sync;
            const badge = document.getElementById("syncStatusBadge");
            if (last.status === "SUCCESS") {
                badge.innerHTML = `<span class="badge-tag badge-success">✓ Synchronized (${last.last_sync_time})</span>`;
            } else if (last.status === "BLOCKED") {
                badge.innerHTML = `<span class="badge-tag badge-warning">⚠️ Sync Blocked (Credentials Required)</span>`;
            } else if (last.status === "FAILED") {
                badge.innerHTML = `<span class="badge-tag badge-danger">❌ Sync Failed: ${last.error || ''}</span>`;
            } else {
                badge.innerHTML = `<span class="badge-tag badge-purple">Idle • Ready</span>`;
            }
        }
    } catch (e) {
        console.error("Sheets status error:", e);
    }
}

async function triggerGoogleSheetsSync() {
    const btn = document.getElementById("syncNowBtn");
    const resultBox = document.getElementById("syncResultContainer");
    
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Syncing to Google Sheets API v4...`;
    resultBox.style.display = "block";
    resultBox.innerHTML = '<div class="p-3 bg-light rounded text-muted">Initiating authentic one-way sync from MySQL tables to Google Sheets tabs...</div>';

    try {
        const res = await fetch("/api/sync/google-sheets", { method: "POST" });
        const data = await res.json();

        if (res.ok && data.success) {
            showToast("Google Sheets synchronization completed successfully!", "success");
            let tablesHtml = (data.tables || []).map(t => 
                `<tr><td>${t.tab}</td><td>${t.table}</td><td><span class="badge-tag badge-success">${t.rows} rows</span></td></tr>`
            ).join("");

            resultBox.innerHTML = `
                <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 18px;">
                    <h4 style="color: #065f46; margin-bottom: 8px;">✅ Google Sheets Synchronized Successfully</h4>
                    <p style="font-size: 13.5px; color: #047857; margin-bottom: 12px;">${data.message}</p>
                    <table class="data-table" style="background: white; border-radius: 6px; overflow: hidden;">
                        <thead>
                            <tr><th>Worksheet Tab</th><th>MySQL Table</th><th>Rows Synced</th></tr>
                        </thead>
                        <tbody>${tablesHtml}</tbody>
                    </table>
                </div>
            `;
        } else {
            showToast(data.message || "Synchronization blocked", "warning");
            resultBox.innerHTML = `
                <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 18px;">
                    <h4 style="color: #92400e; margin-bottom: 8px;">⚠️ Google Sheets Synchronization Blocked</h4>
                    <p style="font-size: 13.5px; color: #78350f;">${data.message}</p>
                    <div style="font-size: 12.5px; color: #92400e; margin-top: 10px; background: rgba(254, 243, 199, 0.5); padding: 10px; border-radius: 6px;">
                        <strong>Configuration Checklist:</strong><br>
                        1. Provide a Google Cloud Service Account JSON file path in <code>GOOGLE_SERVICE_ACCOUNT_FILE</code>.<br>
                        2. Provide the destination Google Sheet ID in <code>GOOGLE_SHEET_ID</code>.<br>
                        3. Share the Google Sheet with the service account client email address.
                    </div>
                </div>
            `;
        }
        loadSheetsStatus();
    } catch (e) {
        showToast("Error triggering synchronization", "danger");
        resultBox.innerHTML = `<div class="text-danger">Network error connecting to sync API.</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `Sync via Service Account API v4`;
    }
}

async function triggerGoogleSheetsWebAppSync() {
    const btn = document.getElementById("syncWebAppBtn");
    const resultBox = document.getElementById("syncResultContainer");

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Transmitting to Web App...`;
    resultBox.style.display = "block";
    resultBox.innerHTML = '<div class="p-3 bg-light rounded text-muted">Reading MySQL database and pushing 1,000 students to Google Apps Script Web App...</div>';

    try {
        const res = await fetch("/api/sync/google-sheets-webapp", { method: "POST" });
        const data = await res.json();

        if (res.ok && data.success) {
            showToast("Successfully transmitted data to Google Sheets Web App!", "success");
            resultBox.innerHTML = `
                <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 18px;">
                    <h4 style="color: #065f46; margin-bottom: 8px;">✅ Transmitted to Google Sheets Web App</h4>
                    <p style="font-size: 13.5px; color: #047857; margin-bottom: 8px;">
                        Successfully delivered <strong>${data.students_synced} students</strong> and <strong>${data.semesters_synced} semester evaluations</strong>.
                    </p>
                    <div style="font-size: 12.5px; color: #065f46; font-family: monospace; background: #d1fae5; padding: 8px; border-radius: 4px;">
                        Web App Endpoint: ${data.webapp_url}
                    </div>
                </div>
            `;
        } else {
            showToast(data.message || "Sync to Web App completed with notice", "warning");
            resultBox.innerHTML = `
                <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 18px;">
                    <h4 style="color: #92400e; margin-bottom: 8px;">⚠️ Synchronization Response</h4>
                    <p style="font-size: 13.5px; color: #78350f;">${data.message || 'Data transmitted. Ensure Code.gs is updated and deployed as New Version in Google Sheets.'}</p>
                </div>
            `;
        }
        loadSheetsStatus();
    } catch (e) {
        showToast("Error transmitting to Web App", "danger");
        resultBox.innerHTML = `<div class="text-danger">Network error connecting to Flask backend.</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `⚡ Push to Apps Script Web App`;
    }
}

