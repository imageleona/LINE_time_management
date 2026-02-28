import os
from datetime import datetime, timezone, date

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

SPREADSHEET_ID = os.environ["GOOGLE_SPREADSHEET_ID"]
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SHEET_NAME = "Sheet1"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_FILE, scopes=SCOPES
)
_service = build("sheets", "v4", credentials=_creds)
_sheet = _service.spreadsheets()


def _local_now() -> datetime:
    return datetime.now().astimezone()


def append_entry(user_id: str, task: str, start_time: datetime, end_time: datetime) -> None:
    duration_min = round((end_time - start_time).total_seconds() / 60, 2)
    local_start = start_time.astimezone()
    local_end = end_time.astimezone()

    row = [
        local_start.strftime("%Y-%m-%d"),
        local_start.strftime("%H:%M:%S"),
        local_end.strftime("%H:%M:%S"),
        duration_min,
        task,
        user_id,
    ]
    body = {"values": [row]}
    _sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:F",
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()


def get_today_entries(user_id: str) -> list[dict]:
    today_str = date.today().strftime("%Y-%m-%d")
    result = _sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:F",
    ).execute()

    rows = result.get("values", [])
    entries = []
    for row in rows[1:]:  # skip header
        if len(row) < 6:
            continue
        row_date, start_t, end_t, duration, task, row_user = row[:6]
        if row_date == today_str and row_user == user_id:
            entries.append({
                "date": row_date,
                "start_time": start_t,
                "end_time": end_t,
                "duration_min": float(duration),
                "task": task,
                "user_id": row_user,
            })
    return entries
