# Google Apps Script Setup & Sync Guide for ScholarTrack

This guide provides the complete instructions to link your **Google Sheet** to the **MySQL Database** (`student_ledger`).

---

## Your Active Web App Endpoint
- **Web App URL:**
  ```text
  https://script.google.com/macros/s/AKfycbxyHpAyj2hBfcMtcFGTbzBb-PnJfcy1O1ydX2q_h-HcWVSkjENeRUdjIa3mC0NbSHas/exec
  ```

---

## 1. Setup Instructions in Google Sheets

1. Open your target Google Sheet.
2. In the top navigation bar, click **Extensions** > **Apps Script**.
3. In the Apps Script code editor, delete any existing code inside `Code.gs`.
4. Open the local file [`google_sheets_code.gs`](file:///c:/Users/pt489/OneDrive/Desktop/Murthy/google_sheets_code.gs), copy the **entire** file contents, and paste them into `Code.gs`.
5. Click the **Save** disk icon (or press `Ctrl + S`).
6. **Deploy as Web App (Crucial Step):**
   - Click the blue **Deploy** button (top right) > select **Manage deployments**.
   - Click the **Edit (pencil icon)** next to your active deployment.
   - Under **Version**, click the dropdown and choose **New version**.
   - Under **Execute as**, select **Me (`your-email@gmail.com`)**.
   - Under **Who has access**, select **Anyone**.
   - Click **Deploy**.
7. Refresh your Google Sheet tab in your browser.
8. You will now see a custom menu in the top bar: **`🎓 ScholarTrack DBMS`**!

---

## 2. How to Synchronize MySQL Data into Google Sheets

### Method 1: Instant Python Push (Zero Tunneling Needed — Recommended)
Run the dedicated sync command from your terminal:
```powershell
C:\Python314\python.exe sync_to_google_sheet_webapp.py
```
Or directly from the web interface:
1. Open the web dashboard: `http://localhost:5000`.
2. Click **Google Sheets Sync** on the left menu.
3. Click the blue button: **`⚡ Push to Apps Script Web App`**.

**What happens:**
- Python queries MySQL (`student_ledger`) for all 1,000 students and 4,156 semester evaluations.
- Sends a single structured JSON payload to your Google Apps Script Web App.
- Google Apps Script creates and populates 3 formatted sheets:
  - **`Students`**: 1,000 rows, navy blue header, frozen row 1, auto-fit columns.
  - **`Semester_Results`**: 4,156 rows, emerald green header, formatted SGPA/CGPA.
  - **`Overview_Metrics`**: KPI card summary with institutional average CGPA and total counts.

---

### Method 2: Direct MySQL Pull via JDBC from Google Sheets
If you wish to pull data directly into Google Sheets using Google Apps Script's built-in `Jdbc` service:
1. Expose MySQL (running locally on port 3306) via an ngrok TCP tunnel:
   ```powershell
   npx ngrok tcp 3306
   ```
   Ngrok will show an address like `tcp://0.tcp.in.ngrok.io:12345`.
2. In Google Sheets, click the custom menu:
   - **`🎓 ScholarTrack DBMS`** > **`⚙️ Configure MySQL Connection`**.
   - Enter: `0.tcp.in.ngrok.io:12345`.
3. Click:
   - **`🎓 ScholarTrack DBMS`** > **`⚡ Pull from MySQL Directly (JDBC)`**.
4. The script executes the SQL query `SELECT * FROM students LIMIT 1000` via JDBC and populates the spreadsheet!
