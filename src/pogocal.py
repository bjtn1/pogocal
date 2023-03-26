from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

green_check_mark = "\U00002705"
red_cross_mark = "\U0000274C"

current_year = datetime.now().year


def parse_date(date: str) -> str:
    """Converts string in the format `Monday, January 13, at 09:00 PM` to the
    following format `2023-01-13 21:00:00`, then returns it"""
    date_format = "%A, %B %d, at %I:%M %p"

    datetime_obj = datetime.strptime(date, date_format)

    day = datetime_obj.strftime("%d")
    month = datetime_obj.strftime("%m")
    time = datetime_obj.strftime("%H:%M")

    parsed_date = f"{current_year}-{month}-{day} {time}:00"

    return parsed_date


def event_ends_next_year(start_date: str, end_date: str):
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

    return (
        start_month_and_day == end_month_and_day
        and start_time == "00:00:00"
        and end_time == "23:59:00"
    )


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
                "start": {"date": self.start_time},
                "end": {"date": self.end_time},
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
                "start": {"dateTime": self.start_time, "timeZone": "UTC-5"},
                "end": {"dateTime": self.end_time, "timeZone": "UTC-5"},
            }

        else:
            metadata = {
                "summary": self.summary,
                "description": self.description,
                "start": {"dateTime": self.start_time, "timeZone": "UTC-5"},
                "end": {"dateTime": self.end_time, "timeZone": "UTC-5"},
            }

        return metadata

    def __str__(self):
        return str(self.to_dict())


def main():
    events = defaultdict()
    driver = webdriver.Firefox()
    url = "https://leekduck.com/events"

    # Go to `url`
    driver.get(url)

    # Save the `url`'s html to be parsed later'
    soup = BeautifulSoup(driver.page_source, "html5lib")

    soup = soup.find_all("div", class_="current-events")[0]  # noqa This is the html of everything under within <div class="events-list" "current-events">
    soup = soup.find_all(
        "span",
        class_="event-header-item-wrapper"
    )  # This is a list of all the spans under <div class="events-list" "current-events">

    links = set()

    # Span refers to each html block containing the <a> tag we're looking for
    for span in soup:
        link = f"https://leekduck.com{span.find('a').get('href')}"
        links.add(link)

    # fix all of this pls thx
    driver.quit()
    exit(0)

    # Get the html of all <div>'s whose css-selector is "events-list"
    soup = soup.find("div", class_="events-list.current-events")

    # Get the html of all <span> tags within the <div> tags whose css-selector is "events-list"
    event_spans = soup.find_all("span")  # type: ignore

    # Create a set to store event links in
    event_links = set()

    # get the `href`'s value from all the <a> tags within <div><span></span></div> from before and store them in the set
    for span in event_spans:
        links = span.find_all("a")
        for link in links:
            event_link = url + link["href"].replace("/events", "")
            event_links.add(event_link)

    # Go to every link, get the end and start dates of the event
    for link in event_links:
        if "unannounced" in link:
            continue

        driver.get(link)
        soup = BeautifulSoup(driver.page_source, "html5lib")

        title = soup.find("h1").text.strip()  # type: ignore

        # Get the event date and start time. Wait 10 secs after going to the website to allow it to load the necessary elements
        start_date = (
            WebDriverWait(driver, 10)
            .until(EC.presence_of_element_located((By.ID, "event-date-start")))
            .text.strip()
            .rstrip(",")
            .replace("  ", " ")
        )
        start_time = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "event-time-start"))
        ).text.split("M")[0] + "M".replace("  ", " ")

        complete_start_date = f"{start_date}, {start_time}"

        end_date = (
            WebDriverWait(driver, 10)
            .until(EC.presence_of_element_located((By.ID, "event-date-end")))
            .text.strip()
            .rstrip(",")
            .replace("  ", " ")
        )
        end_time = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "event-time-end"))
        ).text.split("M")[0] + "M".replace("  ", " ")

        complete_end_date = f"{end_date}, {end_time}"

        print(f"{link}: {complete_end_date}")

        if start_date != "None":
            parsed_start_date = parse_date(complete_start_date)
            parsed_end_date = parse_date(complete_end_date)

            new_event = Event(parsed_start_date, parsed_end_date, title, link)
            events[link] = new_event

    for event in events:
        print(event.to_dict())

    driver.quit()


if __name__ == "__main__":
    main()
