from __future__ import print_function

import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# NOTE when the token expires, just go to the credentials tab in google cloud projects, delete the old OAuth 2.0 client ID, create a new credential, and change the port to 8000 then back to 0

POKEMON_CALENDAR_ID = os.environ.get("POKEMON_CALENDAR_ID")

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main():
    creds = None
    # The file token.json stores the user"s access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # "Z" indicates UTC time

        events_result = service.events().list(calendarId=POKEMON_CALENDAR_ID, timeMin=now, singleEvents=True, orderBy="startTime").execute()

        # We're just gonna use the title of the event to compare it to the list of events we want to add
        calendar_events = [event["summary"] for event in events_result.get("items", [])]  

        if not calendar_events:
            print("No upcoming events found.")
            return

        # Go through each event currently in calendar
        for event in calendar_events:
            print(event)

    except HttpError as error:
        print("An error occurred: %s" % error)


if __name__ == "__main__":
    main()
