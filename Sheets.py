import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime, date
from google.oauth2.service_account import Credentials as SA_Credentials
from google.oauth2.credentials import Credentials as OAuth_Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --- Global Variables ---
load_dotenv()

GOOGLE_CREDS = os.getenv("GOOGLE_CREDS") # Rename to path of service account .json
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GOOGLE_TOKEN = os.getenv("GOOGLE_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive.file']


# Creates Sheets & Drive Serivces
def build_services(credentials, scopes, account="SA"):
    if account == "SA":
        creds = SA_Credentials.from_service_account_file(credentials, scopes=scopes)
    elif account == "OAUTH":
        creds = OAuth_Credentials.from_authorized_user_file(credentials, scopes=scopes)

    sheet_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    return sheet_service, drive_service

# Creates new Spreadsheet
def create_spreadsheet(title: str):

    scopes = ['https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive']

    sheet_service, drive_service = build_services(GOOGLE_TOKEN, scopes, account="OAUTH")

    try:
        spreadsheet = {"properties": {"title": title}}
        spreadsheet = (
        sheet_service.spreadsheets()
        .create(body=spreadsheet, fields="spreadsheetId")
        .execute()
        )

        spreadsheet_id = spreadsheet.get('spreadsheetId')

        print("Created (Drive) spreadsheetId:", spreadsheet_id)
        
        # Share with a specific user

        with open(GOOGLE_CREDS, "r") as f:
            SA_EMAIL = json.load(f)["client_email"]

        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={"type":"user","role":"writer","emailAddress": SA_EMAIL}, 
            sendNotificationEmail=False).execute()
        
        return spreadsheet_id
    
    except HttpError as e:
        print("STATUS:", e.status_code)
        print(e)

# Checks if SPREADSHEET_ID exists
#TODO: Update for Github Actions
def check_spreadsheet_id(spreadsheet_id: str | None, title) -> str:
    if not spreadsheet_id:
        spreadsheet_id = create_spreadsheet(title)  # your function that calls Google API
        # also write to .env so future runs see it
        with open(".env", "a") as f:
            f.write(f"SPREADSHEET_ID={spreadsheet_id}\n")
    return spreadsheet_id

def get_sheet_id(sheet_service, spreadsheet_id, sheet_title):

    sheet = sheet_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(sheetId,title))"
    ).execute()
     
    for s in sheet["sheets"]:
        p = s["properties"]
        if p["title"] == sheet_title:
            return p["sheetId"]
    raise ValueError(f"Sheet '{sheet_title}' not found")

def get_row_count(sheets_service, spreadsheet_id: str, sheet_id: int) -> int:
    sheet = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(sheetId,gridProperties(rowCount)))"
    ).execute()

    for sheet in sheet["sheets"]:
        props = sheet["properties"]
        if props["sheetId"] == sheet_id:
            return props["gridProperties"].get("rowCount", 0)

def get_column_count(sheet_service, spreadsheet_id, sheet_id):
    sheet = sheet_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(sheetId,gridProperties(columnCount)))"
    ).execute()
    
    for sheet in sheet["sheets"]:
        props = sheet["properties"]
        if props["sheetId"] == sheet_id:
            return props["gridProperties"].get("columnCount", 0)

def intitialize_sheet(sheet_service, spreadsheet_id=None):

    
    spreadsheet_id = check_spreadsheet_id(spreadsheet_id, "Canvas Assignment Database")

    try:
        
        spreadsheet = sheet_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        sheet_id = get_sheet_id(sheet_service, spreadsheet_id, "Sheet1")

        col_count = get_column_count(sheet_service,spreadsheet_id, sheet_id)
        row_count = get_row_count(sheet_service, spreadsheet_id, sheet_id)

        # Header row text (A1:G1) via Values API
        header = [["Assignment","Course","Due Date","Priority","Status","Submitted","Notes"]]
        sheet_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A1:G1",
            valueInputOption="USER_ENTERED",
            body={"values": header}
        ).execute()

        requests = [
        # Rename first tab → "Upcoming"
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "title": "Assignments"},
                "fields": "title"
            }
        },

        # WHOLE SHEET → Century Gothic
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Century Gothic"}}},
                "fields": "userEnteredFormat.textFormat.fontFamily"
            }
        },

        # Freeze Row 1
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount"
            }
        },

        # Header bold
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold"
            }
        },

        # Base column widths A:G = 150 px
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 7},
                "properties": {"pixelSize": 150},
                "fields": "pixelSize"
            }
        },

        # Wrap all cells
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                "fields": "userEnteredFormat.wrapStrategy"
            }
        },

        # Center + middle alignment for entire sheet
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)"
            }
        },

        # Column C (rows 2+) → DateTime format
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 2, "endColumnIndex": 3},
                "cell": {"userEnteredFormat": {"numberFormat": {
                    "type": "DATE_TIME", "pattern": "m/d/yyyy h:mm AM/PM"}}},
                "fields": "userEnteredFormat.numberFormat"
            }
        },

        # Column D (rows 2+) → Priority dropdown
        {
            "setDataValidation": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 3, "endColumnIndex": 4},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": [
                        {"userEnteredValue": "High"},
                        {"userEnteredValue": "Medium"},
                        {"userEnteredValue": "Low"},
                        {"userEnteredValue": "Optional"},
                    ]},
                    "strict": True, "showCustomUi": True
                }
            }
        },

        # Column E (rows 2+) → Status dropdown
        {
            "setDataValidation": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 4, "endColumnIndex": 5},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": [
                        {"userEnteredValue": "Non Started"},
                        {"userEnteredValue": "Started"},
                        {"userEnteredValue": "Near Completion"},
                        {"userEnteredValue": "Completed"},
                    ]},
                    "strict": True, "showCustomUi": True
                }
            }
        },

        # Column F (rows 2+) → Yes/No dropdown
        {
            "setDataValidation": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 5, "endColumnIndex": 6},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": [
                        {"userEnteredValue": "Yes"},
                        {"userEnteredValue": "No"},
                    ]},
                    "strict": True, "showCustomUi": True
                }
            }
        },

        # Delete columns H+ (H = index 7)
        {
            "deleteDimension": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                          "startIndex": 7, "endIndex": col_count}
            }
        },

        # Column A width = 250 px
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 250},
                "fields": "pixelSize"
            }
        },

        # Column G width = 300 px
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7},
                "properties": {"pixelSize": 300},
                "fields": "pixelSize"
            }
        },

        # Header background = light blue
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.80, "green": 0.90, "blue": 1.0}}},
                "fields": "userEnteredFormat.backgroundColor"
            }
        },

        # Borders: all borders on header A1:G1
        {
            "updateBorders": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": 7},
                "top":    {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "bottom": {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "left":   {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "right":  {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "innerHorizontal": {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "innerVertical":   {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
            }
        },

        # Borders: outer per-row A2:G(last) (no inner verticals)
        {
            "updateBorders": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count,
                          "startColumnIndex": 0, "endColumnIndex": 7},
                "top":    {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "bottom": {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "left":   {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "right":  {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "innerHorizontal": {"style": "SOLID", "width": 1, "color": {"red":0,"green":0,"blue":0}},
                "innerVertical":   {"style": "NONE"}
            }
        },

        # 0–3 days => light red
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1, "endRowIndex": row_count,
                            "startColumnIndex": 0, "endColumnIndex": 7
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": "=AND($C2<>\"\", $C2-TODAY()>=0, $C2-TODAY()<=3)"}]
                            },
                            "format": {"backgroundColor": {"red": 1.0, "green": 0.85, "blue": 0.85}}
                        }
                    },
                    "index": 0
                }
            },
            # 4–7 days => yellow
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1, "endRowIndex": row_count,
                            "startColumnIndex": 0, "endColumnIndex": 7
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": "=AND($C2<>\"\", $C2-TODAY()>3, $C2-TODAY()<=7)"}]
                            },
                            "format": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.6}}
                        }
                    },
                    "index": 1
                }
            },
            # >7 days => green
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1, "endRowIndex": row_count,
                            "startColumnIndex": 0, "endColumnIndex": 7
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": "=AND($C2<>\"\", $C2-TODAY()>7)"}]
                            },
                            "format": {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}}
                        }
                    },
                    "index": 2
                }
            },
            # 15) Add Filter View "Upcoming" on Assignments (Submitted = No; sort by Due Date asc)
            {
                "addFilterView": {
                    "filter": {
                        "title": "Upcoming",
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,                 # include header
                            "endRowIndex": row_count,      # future-proof buffer
                            "startColumnIndex": 0,              # A
                            "endColumnIndex": col_count                 # G (exclusive)
                        },
                        "sortSpecs": [{
                            "dimensionIndex": 2,                # C = Due Date
                            "sortOrder": "ASCENDING"
                        }],
                        "filterSpecs": [{
                            "columnIndex": 5,                   # F = Submitted
                            "filterCriteria": {
                                "condition": {
                                    "type": "TEXT_EQ",
                                    "values": [{"userEnteredValue": "No"}]
                                }
                            }
                        }]
                    }
                }
            }

        ]

        # Execute pre-CF batch
        sheet_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()


        return

    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


def sync_assignments(sheet_service, spreadsheet_id, assignments, upcoming_title="Upcoming", completed_title="Completed"):
    """Send assignments to Upcoming/Completed tabs based on submission state."""
    true_markers = {"true", "yes", "y", "submitted", "1"}

    def normalize_submitted(value):
        if isinstance(value, str):
            return value.strip().lower() in true_markers
        return bool(value)

    def format_due_date(value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%m/%d/%Y %I:%M %p")
        if isinstance(value, date):
            return value.strftime("%m/%d/%Y")
        text = str(value).strip()
        if not text:
            return ""
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return str(value)
        return parsed.strftime("%m/%d/%Y %I:%M %p")

    upcoming_rows = []
    completed_rows = []

    for name, course, due_date, submitted in assignments or []:
        submitted_flag = normalize_submitted(submitted)
        row = [
            name,
            course,
            format_due_date(due_date),
            "",
            "",
            "Yes" if submitted_flag else "No",
            "",
        ]
        if submitted_flag:
            completed_rows.append(row)
        else:
            upcoming_rows.append(row)

    clear_body = {"ranges": [f"{upcoming_title}!A2:G", f"{completed_title}!A2:G"]}
    sheet_service.spreadsheets().values().batchClear(
        spreadsheetId=spreadsheet_id,
        body=clear_body,
    ).execute()

    data = []
    if upcoming_rows:
        data.append({"range": f"{upcoming_title}!A2:G", "values": upcoming_rows})
    if completed_rows:
        data.append({"range": f"{completed_title}!A2:G", "values": completed_rows})

    if data:
        sheet_service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()


sheet_service, drive_service = build_services(GOOGLE_CREDS, SCOPES)

sheet = sheet_service.spreadsheets().get(
    spreadsheetId=SPREADSHEET_ID,
    fields="sheets(properties(sheetId,title))"
).execute()

print([s["properties"]["title"] for s in sheet["sheets"]])

intitialize_sheet(sheet_service, spreadsheet_id=SPREADSHEET_ID)

print([s["properties"]["title"] for s in sheet["sheets"]])



#spreadsheet = sheet_service.spreadsheets().get(spreadsheetId="1HPWK-8Frb1nwhcHf9ghZqjrt-IDUJzVJxs1jNr_y-N0").execute()
#print(f"✅ Connected to Google Sheet: {spreadsheet['properties']['title']}")
