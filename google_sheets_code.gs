/**
 * ==============================================================================
 * ScholarTrack Academic Progression DBMS — Google Apps Script
 * Direct MySQL <--> Google Sheets Bi-Directional Integration
 * ==============================================================================
 * Web App URL:
 * https://script.google.com/macros/s/AKfycbxyHpAyj2hBfcMtcFGTbzBb-PnJfcy1O1ydX2q_h-HcWVSkjENeRUdjIa3mC0NbSHas/exec
 * 
 * INSTRUCTIONS:
 * 1. Open your Google Sheet.
 * 2. Click "Extensions" > "Apps Script".
 * 3. Delete any default code in Code.gs and paste this ENTIRE file.
 * 4. Click the "Save" disk icon.
 * 5. DEPLOY AS WEB APP (Crucial step):
 *    - Click "Deploy" (top right) > "Manage deployments".
 *    - Click the Edit (pencil) icon next to your active deployment.
 *    - Under "Version", choose "New version".
 *    - Under "Execute as", select "Me (your email)".
 *    - Under "Who has access", select "Anyone".
 *    - Click "Deploy".
 * 6. Refresh your Google Sheet tab. You will now see a custom menu:
 *    "🎓 ScholarTrack DBMS" in the top menu bar!
 * ==============================================================================
 */

// ==============================================================================
// 1. DEFAULT MYSQL CONFIGURATION (For Direct JDBC Pull)
// ==============================================================================
var DEFAULT_MYSQL = {
  // If connecting directly via Google Apps Script Jdbc, Google's cloud servers
  // need a reachable IP/domain (e.g. ngrok TCP tunnel host, e.g. "0.tcp.in.ngrok.io"):
  host: "127.0.0.1", 
  port: "3306",
  database: "student_ledger",
  user: "root",
  password: "Pravin@_123"
};


// ==============================================================================
// 2. CUSTOM MENU CREATION ON SHEET OPEN
// ==============================================================================
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("🎓 ScholarTrack DBMS")
    .addItem("⚡ Pull from MySQL Directly (JDBC)", "syncDirectFromMySqlJdbc")
    .addItem("📊 Show Database Summary", "showDatabaseSummaryDialog")
    .addSeparator()
    .addItem("⚙️ Configure MySQL Connection (Host/Port/DB)", "configureMySqlConnection")
    .addItem("🧹 Format & Style Current Sheets", "formatExistingSheets")
    .addToUi();
}


// ==============================================================================
// 3. WEB APP HTTP POST HANDLER (Receives data pushed from Python/MySQL)
// ==============================================================================
/**
 * Receives JSON payload sent from local Python script or Flask backend
 * and automatically populates the Google Sheet tabs!
 */
function doPost(e) {
  var lock = LockService.getScriptLock();
  // Wait up to 30 seconds for concurrent writes to clear
  var hasLock = lock.tryLock(30000);
  if (!hasLock) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: "Server is busy with another synchronization. Please retry."
    })).setMimeType(ContentService.MimeType.JSON);
  }

  try {
    var rawContent = e.postData ? e.postData.contents : "";
    if (!rawContent) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "No POST body received."
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var payload = JSON.parse(rawContent);
    var action = payload.action || "sync_all";
    var ss = getTargetSpreadsheet(payload.spreadsheet_id);

    var responseData = {
      status: "success",
      action: action,
      timestamp: new Date().toISOString(),
      tabs_updated: []
    };

    // ACTION: Ping test
    if (action === "ping") {
      responseData.message = "ScholarTrack Web App Webhook is active and connected to Google Sheets!";
      return ContentService.createTextOutput(JSON.stringify(responseData))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // ACTION: Sync Students Directory (1,000 students)
    if (payload.students && Array.isArray(payload.students)) {
      var count = writeStudentsTab(ss, payload.students);
      responseData.tabs_updated.push({ tab: "Students", row_count: count });
    }

    // ACTION: Sync Semester Results / Performance
    if (payload.semester_results && Array.isArray(payload.semester_results)) {
      var semCount = writeSemesterResultsTab(ss, payload.semester_results);
      responseData.tabs_updated.push({ tab: "Semester_Results", row_count: semCount });
    }

    // ACTION: Sync General/Custom Tables
    if (payload.tables && typeof payload.tables === "object") {
      for (var tableName in payload.tables) {
        if (payload.tables.hasOwnProperty(tableName)) {
          var tableData = payload.tables[tableName];
          if (tableData && tableData.rows) {
            var tCount = writeGenericTab(ss, tableData.tab_name || tableName, tableData.headers, tableData.rows);
            responseData.tabs_updated.push({ tab: tableData.tab_name || tableName, row_count: tCount });
          }
        }
      }
    }

    // ACTION: Write Overview & Metrics Tab
    if (payload.metrics) {
      writeOverviewMetricsTab(ss, payload.metrics);
      responseData.tabs_updated.push({ tab: "Overview_Metrics", row_count: 10 });
    }

    responseData.message = "Successfully synchronized MySQL data to Google Sheets!";
    return ContentService.createTextOutput(JSON.stringify(responseData))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString(),
      stack: err.stack
    })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}


// ==============================================================================
// 4. WEB APP HTTP GET HANDLER (Status check in browser)
// ==============================================================================
function doGet(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetName = ss ? ss.getName() : "Unknown Spreadsheet";

  var statusObj = {
    service: "ScholarTrack DBMS — Google Apps Script Integration",
    status: "ONLINE",
    spreadsheet_name: sheetName,
    available_actions: [
      "POST: action='ping'",
      "POST: action='sync_all' (with students, semester_results, metrics)",
      "GET: status check"
    ],
    timestamp: new Date().toISOString()
  };

  return ContentService.createTextOutput(JSON.stringify(statusObj, null, 2))
    .setMimeType(ContentService.MimeType.JSON);
}


// ==============================================================================
// 5. TAB WRITERS & STYLING ENGINE
// ==============================================================================

/**
 * Gets or binds the target spreadsheet
 */
function getTargetSpreadsheet(spreadsheetId) {
  if (spreadsheetId) {
    try {
      return SpreadsheetApp.openById(spreadsheetId);
    } catch (e) {}
  }
  var active = SpreadsheetApp.getActiveSpreadsheet();
  if (active) return active;

  var savedId = PropertiesService.getScriptProperties().getProperty("SPREADSHEET_ID");
  if (savedId) {
    return SpreadsheetApp.openById(savedId);
  }
  throw new Error("No active Google Spreadsheet found. Please pass spreadsheet_id or open the script from inside Google Sheets.");
}

/**
 * Populates the 'Students' worksheet tab
 */
function writeStudentsTab(ss, studentsList) {
  var tabName = "Students";
  var sheet = getOrCreateTab(ss, tabName);

  var headers = [
    "Student ID",
    "Full Name",
    "Roll No",
    "Branch / Department",
    "Admission Year",
    "Institutional Email",
    "Status"
  ];

  var rows = [headers];
  for (var i = 0; i < studentsList.length; i++) {
    var s = studentsList[i];
    rows.push([
      s.student_id != null ? s.student_id : (i + 1),
      s.student_name || s.name || "",
      s.roll_no != null ? s.roll_no : "",
      s.branch || "",
      s.admission_year != null ? s.admission_year : "",
      s.email || "",
      s.current_status || s.status || "Active"
    ]);
  }

  // Clear sheet and write all values in single high-speed batch
  sheet.clear();
  var range = sheet.getRange(1, 1, rows.length, headers.length);
  range.setValues(rows);

  // Apply Professional Styling
  styleTableHeader(sheet, headers.length, "#1e3a8a"); // Navy Blue
  sheet.setFrozenRows(1);
  sheet.getRange(2, 1, rows.length - 1, headers.length).setFontFamily("Roboto").setFontSize(10);
  
  // Align numeric columns
  sheet.getRange(2, 1, rows.length - 1, 1).setHorizontalAlignment("center");
  sheet.getRange(2, 3, rows.length - 1, 1).setHorizontalAlignment("center");
  sheet.getRange(2, 5, rows.length - 1, 1).setHorizontalAlignment("center");

  // Auto-fit column widths
  for (var col = 1; col <= headers.length; col++) {
    sheet.autoResizeColumn(col);
  }

  return rows.length - 1;
}

/**
 * Populates the 'Semester_Results' worksheet tab
 */
function writeSemesterResultsTab(ss, resultsList) {
  var tabName = "Semester_Results";
  var sheet = getOrCreateTab(ss, tabName);

  var headers = [
    "Result ID",
    "Student ID",
    "Semester",
    "Academic Year",
    "SGPA",
    "CGPA",
    "Status",
    "Backlogs"
  ];

  var rows = [headers];
  for (var i = 0; i < resultsList.length; i++) {
    var r = resultsList[i];
    rows.push([
      r.id != null ? r.id : (i + 1),
      r.student_id || "",
      r.semester_number != null ? r.semester_number : (r.semester || ""),
      r.academic_year || "",
      r.sgpa != null ? Number(r.sgpa) : 0.0,
      r.cgpa != null ? Number(r.cgpa) : 0.0,
      r.result_status || r.status || "Pass",
      r.backlog_count != null ? r.backlog_count : 0
    ]);
  }

  sheet.clear();
  var range = sheet.getRange(1, 1, rows.length, headers.length);
  range.setValues(rows);

  styleTableHeader(sheet, headers.length, "#065f46"); // Emerald Green
  sheet.setFrozenRows(1);
  sheet.getRange(2, 1, rows.length - 1, headers.length).setFontFamily("Roboto").setFontSize(10);

  // Number format for SGPA and CGPA
  sheet.getRange(2, 5, rows.length - 1, 2).setNumberFormat("0.00");

  for (var col = 1; col <= headers.length; col++) {
    sheet.autoResizeColumn(col);
  }

  return rows.length - 1;
}

/**
 * Populates the 'Overview_Metrics' worksheet tab with KPI cards
 */
function writeOverviewMetricsTab(ss, metrics) {
  var tabName = "Overview_Metrics";
  var sheet = getOrCreateTab(ss, tabName);
  sheet.clear();

  var rows = [
    ["🎓 SCHOLARTRACK ACADEMIC MANAGEMENT SYSTEM — SYSTEM KPI SUMMARY", ""],
    ["Synchronization Timestamp", new Date().toLocaleString()],
    ["Database Name", "student_ledger (MySQL 8.0)"],
    ["---------------------------------------------------", "------------------"],
    ["Total Registered Students", metrics.total_students || 0],
    ["Total Semester Evaluations", metrics.total_records || metrics.total_semesters || 0],
    ["Institutional Average CGPA", metrics.average_cgpa ? Number(metrics.average_cgpa).toFixed(2) : "0.00"],
    ["Pass Rate (%)", metrics.pass_rate ? metrics.pass_rate + "%" : "N/A"],
    ["Co-Curricular / Portfolio Records", metrics.total_activities || 0],
    ["Active Schema Normalization", "Third Normal Form (3NF) — 10 Tables"]
  ];

  var range = sheet.getRange(1, 1, rows.length, 2);
  range.setValues(rows);

  // Title row
  var title = sheet.getRange(1, 1, 1, 2);
  title.merge();
  title.setBackground("#0f172a");
  title.setFontColor("#f8fafc");
  title.setFontWeight("bold");
  title.setFontSize(13);

  // Metric keys bold
  sheet.getRange(2, 1, rows.length - 1, 1).setFontWeight("bold");
  sheet.autoResizeColumn(1);
  sheet.autoResizeColumn(2);
}

/**
 * Generic tab writer for any MySQL table
 */
function writeGenericTab(ss, tabName, headers, rowsData) {
  var sheet = getOrCreateTab(ss, tabName);
  var rows = [headers];
  for (var i = 0; i < rowsData.length; i++) {
    rows.push(rowsData[i]);
  }
  sheet.clear();
  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  styleTableHeader(sheet, headers.length, "#374151");
  sheet.setFrozenRows(1);
  for (var col = 1; col <= headers.length; col++) {
    sheet.autoResizeColumn(col);
  }
  return rows.length - 1;
}

/**
 * Helpers
 */
function getOrCreateTab(ss, tabName) {
  var sheet = ss.getSheetByName(tabName);
  if (!sheet) {
    sheet = ss.insertSheet(tabName);
  }
  return sheet;
}

function styleTableHeader(sheet, columnCount, bgColor) {
  var header = sheet.getRange(1, 1, 1, columnCount);
  header.setBackground(bgColor);
  header.setFontColor("#ffffff");
  header.setFontWeight("bold");
  header.setFontSize(11);
}


// ==============================================================================
// 6. DIRECT MYSQL JDBC INTEGRATION (Run inside Google Sheets)
// ==============================================================================
/**
 * Connects directly from Google Apps Script to MySQL using JDBC.
 * Note: Google's cloud servers require MySQL to have a public host
 * or an ngrok tunnel (e.g. `npx ngrok tcp 3306`).
 */
function syncDirectFromMySqlJdbc() {
  var ui = SpreadsheetApp.getUi();
  var props = PropertiesService.getUserProperties();

  var host = props.getProperty("MYSQL_HOST") || DEFAULT_MYSQL.host;
  var port = props.getProperty("MYSQL_PORT") || DEFAULT_MYSQL.port;
  var db = props.getProperty("MYSQL_DB") || DEFAULT_MYSQL.database;
  var user = props.getProperty("MYSQL_USER") || DEFAULT_MYSQL.user;
  var pass = props.getProperty("MYSQL_PASS") || DEFAULT_MYSQL.password;

  if (host === "127.0.0.1" || host === "localhost") {
    var response = ui.alert(
      "Notice Regarding Direct JDBC",
      "Your MySQL host is set to '127.0.0.1' (localhost).\n\n" +
      "Because Google Apps Script runs in Google's Cloud, it cannot directly reach 'localhost' without a tunnel.\n\n" +
      "OPTIONS:\n" +
      "1. Recommended: Use the Python sync script (`sync_to_google_sheet_webapp.py`). It pushes directly to this Web App without any tunneling!\n" +
      "2. Or start an ngrok TCP tunnel (`npx ngrok tcp 3306`) and set the host here.\n\n" +
      "Would you like to configure your MySQL host now?",
      ui.ButtonSet.YES_NO
    );
    if (response == ui.Button.YES) {
      configureMySqlConnection();
    }
    return;
  }

  var jdbcUrl = "jdbc:mysql://" + host + ":" + port + "/" + db;
  SpreadsheetApp.getActiveSpreadsheet().toast("Connecting to " + jdbcUrl + "...", "MySQL JDBC", 10);

  try {
    var conn = Jdbc.getConnection(jdbcUrl, user, pass);
    var stmt = conn.createStatement();
    stmt.setMaxRows(1000);

    var rs = stmt.executeQuery(
      "SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status " +
      "FROM students ORDER BY student_id ASC LIMIT 1000;"
    );

    var students = [];
    while (rs.next()) {
      students.push({
        student_id: rs.getInt(1),
        student_name: rs.getString(2),
        roll_no: rs.getInt(3),
        branch: rs.getString(4),
        admission_year: rs.getInt(5),
        email: rs.getString(6),
        current_status: rs.getString(7)
      });
    }

    rs.close();
    stmt.close();
    conn.close();

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var count = writeStudentsTab(ss, students);

    ui.alert("✅ JDBC Sync Complete!", "Successfully pulled " + count + " student records from MySQL into the 'Students' sheet.", ui.ButtonSet.OK);

  } catch (err) {
    ui.alert("❌ JDBC Connection Failed", "Error connecting to MySQL:\n" + err.message, ui.ButtonSet.OK);
  }
}

/**
 * Configure MySQL parameters dialog
 */
function configureMySqlConnection() {
  var ui = SpreadsheetApp.getUi();
  var props = PropertiesService.getUserProperties();

  var currentHost = props.getProperty("MYSQL_HOST") || DEFAULT_MYSQL.host;
  var currentPort = props.getProperty("MYSQL_PORT") || DEFAULT_MYSQL.port;

  var promptResult = ui.prompt(
    "Configure MySQL Host & Port",
    "Enter host and port separated by a colon (e.g., 0.tcp.in.ngrok.io:12345 or your public IP):\nCurrent: " + currentHost + ":" + currentPort,
    ui.ButtonSet.OK_CANCEL
  );

  if (promptResult.getSelectedButton() == ui.Button.OK) {
    var text = promptResult.getResponseText().trim();
    if (text.indexOf(":") > -1) {
      var parts = text.split(":");
      props.setProperty("MYSQL_HOST", parts[0].trim());
      props.setProperty("MYSQL_PORT", parts[1].trim());
      ui.alert("Saved MySQL host as " + parts[0].trim() + " on port " + parts[1].trim());
    } else if (text.length > 0) {
      props.setProperty("MYSQL_HOST", text);
      ui.alert("Saved MySQL host as " + text);
    }
  }
}

/**
 * Shows quick database summary popup
 */
function showDatabaseSummaryDialog() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var studentsSheet = ss.getSheetByName("Students");
  var count = studentsSheet ? Math.max(0, studentsSheet.getLastRow() - 1) : 0;

  SpreadsheetApp.getUi().alert(
    "📊 ScholarTrack Database Status",
    "• Current Active Sheet: " + ss.getName() + "\n" +
    "• Synced Student Rows: " + count + " records\n" +
    "• Database Backend: MySQL 8.0 (student_ledger)\n" +
    "• Schema Normalization: 3NF Relational Architecture\n\n" +
    "To re-sync, run: python sync_to_google_sheet_webapp.py",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

/**
 * Auto-format existing sheets
 */
function formatExistingSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var sh = sheets[i];
    if (sh.getLastRow() > 0 && sh.getLastColumn() > 0) {
      styleTableHeader(sh, sh.getLastColumn(), "#1e3a8a");
      sh.setFrozenRows(1);
    }
  }
  SpreadsheetApp.getActiveSpreadsheet().toast("Applied headers and styling to all sheets!", "Formatting Done", 3);
}
