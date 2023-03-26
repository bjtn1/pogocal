from __future__ import print_function

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium import webdriver

from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

current_year = datetime.now().year


def setup_driver() -> webdriver.Firefox:
    """Returns a webdriver.Firefox instance to be used to navigate to the desired URL"""

    return driver


def get_event_info(website: str, driver: webdriver.Firefox , events: defaultdict):
    """Parses `website` containing one(1) event by obtaining its start and end date and time. Function then makes a new Event object and adds it to `events` dict()"""
    driver.get(website)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Get title of event
    title = soup.find("h1").text.strip()

    # Get the event date and start time. Wait 10 secs after going to the website to allow it to load the necessary elements
    start_date = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-date-start"))).text.strip().rstrip(",").replace("  ", " ")
    start_time = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-time-start"))).text.split("M")[0] + "M".replace("  ", " ")

    complete_start_date = f"{start_date}, {start_time}"

    end_date = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-date-end"))).text.strip().rstrip(",").replace("  ", " ")
    end_time = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-time-end"))).text.split("M")[0] + "M".replace("  ", " ")

    complete_end_date = f"{end_date}, {end_time}"

    # If the event has a start and end time, reformat them, then create a new event object, then add it to `events` dict()
    if start_date != "None":
        parsed_start_date = parse_date(complete_start_date)
        parsed_end_date = parse_date(complete_end_date)

        new_event = Event(parsed_start_date, parsed_end_date, title, website)
        events[website] = new_event

    driver.quit()


def parse_date(date: str) -> str:
    """Converts string in the format `Monday, January 13, at 09:00 PM` to the following format `2023-01-13 21:00:00`, then returns it"""
    date_format = "%A, %B %d, at %I:%M %p"

    datetime_obj = datetime.strptime(date, date_format)

    day = datetime_obj.strftime("%d")
    month = datetime_obj.strftime("%m")
    time = datetime_obj.strftime("%H:%M")

    parsed_date = f"{current_year}-{month}-{day} {time}:00"

    return parsed_date


def event_ends_next_year(start_date: str, end_date:str):
    """Returns true if an event with `start_date` and `end_date` ends next year (starts in December and ends after December)"""
    start_month = start_date[5:7]
    end_month = end_date[5:7]
    return int(start_month) == 12 and int(end_month) < 12


def is_all_day_event(start_date: str, end_date: str):
    """Returns true if an event with `start_date` and `end_date` is an all day event (starts at 00:00:00 and ends at 23:59:00 on the same day)"""
    start_month_and_day = start_date[5:10]
    end_month_and_day = end_date[5:10]
    start_time = start_date[11:]
    end_time = end_date[11:]

    return start_month_and_day == end_month_and_day and start_time == "00:00:00" and end_time == "23:59:00"


def convert_to_rfc3339(date: str):
    """Converts a string to the rfc3339 format, then returns it"""
    rfc3339_format = "%Y-%m-%dT%H:%M:%S"
    date_object = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    return date_object.strftime(rfc3339_format)


def convert_to_yyy_mm_dd(date: str):
    """Returns a string converted to the YYY-MM-DD format"""
    yyy_mm_dd_format = "%Y-%m-%d"
    date_object = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    return date_object.strftime(yyy_mm_dd_format)


@dataclass
class Event:
    start_time: str = field(compare=False)
    end_time: str = field(compare=False)
    summary: str
    description: str

    def to_dict(self):
        if is_all_day_event(self.start_time, self.end_time):

            self.start_time = convert_to_yyy_mm_dd(self.start_time)
            self.end_time = convert_to_yyy_mm_dd(self.end_time)

            metadata = {
                "summary": self.summary,
                "description": self.description,
                "start": {
                    "date": self.start_time
                },
                "end": {
                    "date": self.end_time
                }
            }

        elif event_ends_next_year(self.start_time, self.end_time):

            self.start_time = convert_to_rfc3339(self.start_time)

            # add one to end_time's year

            end_time_date_object = datetime.strptime(self.end_time, "%Y-%m-%d %H:%M:%S")
            end_time_date_object = end_time_date_object + relativedelta(year=1)

            self.end_time = end_time_date_object.strftime("%Y-%m-%d %H:%M:%S")
            self.end_time = convert_to_rfc3339(self.end_time)

            metadata = {
                "summary": self.summary,
                "description": self.description,
                "start": {
                    "dateTime": self.start_time,
                    "timeZone": "UTC-5"
                },
                "end": {
                    "dateTime": self.end_time,
                    "timeZone": "UTC-5"
                }
            }

        else:
            metadata = {
                "summary": self.summary,
                "description": self.description,
                "start": {
                    "dateTime": self.start_time,
                    "timeZone": "UTC-5"
                },
                "end": {
                    "dateTime": self.end_time,
                    "timeZone": "UTC-5"
                }
            }

        return metadata

    def __str__(self):
        return str(self.to_dict())


def main():
    options = Options()
    options.add_argument("--headless")

    geckodriver = os.environ['GECKODRIVER_PATH']

    service = Service(executable_path=geckodriver)
    driver = webdriver.Firefox(service=service, options=options)

    events = defaultdict()

    url = "https://leekduck.com/events"

    driver.get(url)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    current_events_div = soup.find("div", class_="events-list current-events")
    current_events_spans = current_events_div.find_all("span")

    current_events_links = set()

    # Find all the links to current events and save them
    for span in current_events_spans:
        links = span.find_all("a")
        for link in links:
            event_link = url + link["href"].replace("/events", "")
            current_events_links.add(event_link)

    # # Check if any links have already been seen
    # with open("cache.txt", "r") as file:
    #     seen_links = set(file.read().splitlines())

    # # Remove events that we've already added to the calendar
    # current_events_links = current_events_links.difference(seen_links)

    # Parse each event's site
    for link in current_events_links:
        driver.get(link)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Get title of event
        title = soup.find("h1").text.strip()

        # Get the event date and start time. Wait 10 secs after going to the website to allow it to load the necessary elements
        start_date = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-date-start"))).text.strip().rstrip(",").replace("  ", " ")
        start_time = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-time-start"))).text.split("M")[0] + "M".replace("  ", " ")

        complete_start_date = f"{start_date}, {start_time}"

        end_date = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-date-end"))).text.strip().rstrip(",").replace("  ", " ")
        end_time = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "event-time-end"))).text.split("M")[0] + "M".replace("  ", " ")

        complete_end_date = f"{end_date}, {end_time}"

        # If the event has a start and end time, reformat them, then create a new event object, then add it to `events` dict()
        if start_date != "None":
            parsed_start_date = parse_date(complete_start_date)
            parsed_end_date = parse_date(complete_end_date)

            new_event = Event(parsed_start_date, parsed_end_date, title, link)
            events[link] = new_event

        driver.quit()

    
    for event in events:
        print(event.to_dict())


    # """Shows basic usage of the Google Calendar API.
    # Prints the start and name of the next 10 events on the user's calendar.
    # """
    # creds = None
    # # The file token.json stores the user's access and refresh tokens, and is
    # # created automatically when the authorization flow completes for the first
    # # time.
    # if os.path.exists('token.json'):
    #     creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # # If there are no (valid) credentials available, let the user log in.
    # if not creds or not creds.valid:
    #     if creds and creds.expired and creds.refresh_token:
    #         creds.refresh(Request())
    #     else:
    #         flow = InstalledAppFlow.from_client_secrets_file(
    #             'credentials.json', SCOPES)
    #         # I changed the port from 0 to 8000 and now it works. It works regardless of the port POG
    #         creds = flow.run_local_server(port=8000)
    #     # Save the credentials for the next run
    #     with open('token.json', 'w') as token:
    #         token.write(creds.to_json())

    # try:
    #     service = build('calendar', 'v3', credentials=creds)

    #     pokemon_calendar_id = os.environ.get("POKEMON_CALENDAR_ID")

    #     cache_file = open("cache.txt", "a")

    #     for event in events:
    #         new_event = service.events().insert(calendarId=pokemon_calendar_id, body=event.to_dict()).execute()
    #         new_event_link = new_event.get("htmlLink")
    #         if new_event_link:
    #             cache_file.write(f"{event.event_link}\n")
    #             print(f"\"{event.title}\" event successfully created \n\t({new_event_link})")
    #         else:
    #             print("Something went wrong while trying to add the event to the calendar")
    #     cache_file.close()

    # except HttpError as error:
    #     print('An error occurred: %s' % error)


if __name__ == '__main__':
    main()
