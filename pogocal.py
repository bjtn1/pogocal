"""
@author: Brandon Jose Tenorio Noguera
"""
import curses
from curses import wrapper
import requests
import json
from datetime import datetime, timezone

# TODO
# [ ] 1) Turn right_win into top_right_win
# [ ] 2) Add a banner at the top of top_right_win that says (Event info)
# [ ] 3) Add a bottom_right_win that has all the "added events"
# [ ] 4) Add a banner to bottom right window
# [ ] 5) Add a `?` button that displays navigation command and shit 
# [ ] 6) Add `a` to display a new window asking the user to confirm their event selection
# [ ] 7) Add functionality to turn desired_events into a .ics file
# [x] 8) Turn the printing of the event's info onto the right_win into its own function (we use it too much)
# [x] 9) Let's make the going down/going up thingie loop instead of coding a hard barrier

# NOTE
# 1) desired_events should store the name of the event (to be printed to bottom_right_win) and the index of the event in `events` to access it later

# FIX
# [x] 1) Start and end time seem to be the same for every event, why?

CHECK = u'\u2713'

def get_events():
    return requests.get("https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/events.json").json()

def get_lines_to_print(event_data):
    lines_to_print = []

    event_name = event_data["name"]
    event_link = event_data["link"]

    # if start or end time end in "Z", convert ISO8601 to UTC
    # otherwise, convert ISO8601 to user's local time

    event_start_time_str = event_data["start"]

    if event_start_time_str.endswith("Z") :
        event_start_time_dt = datetime.strptime(event_start_time_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    else:
        event_start_time_dt = datetime.strptime(event_start_time_str, "%Y-%m-%dT%H:%M:%S.%f")

    event_start_utc_dt = event_start_time_dt.astimezone(timezone.utc)
    event_start_timestamp = event_start_utc_dt.timestamp()
    event_start_formatted = datetime.fromtimestamp(event_start_timestamp).strftime("%Y-%m-%d %H:%M:%S")

    event_end_time_str = event_data["end"]

    if event_end_time_str.endswith("Z") :
        event_end_time_dt = datetime.strptime(event_end_time_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    else:
        event_end_time_dt = datetime.strptime(event_end_time_str, "%Y-%m-%dT%H:%M:%S.%f")

    event_end_utc_dt = event_end_time_dt.astimezone(timezone.utc)
    event_end_timestamp = event_end_utc_dt.timestamp()
    event_end_formatted = datetime.fromtimestamp(event_end_timestamp).strftime("%Y-%m-%d %H:%M:%S")

    lines_to_print.append(f"{event_name}")
    lines_to_print.append(f"{event_link}")
    lines_to_print.append(f"{event_start_formatted}")
    lines_to_print.append(f"{event_end_formatted}")

    return lines_to_print


def curse(stdscr):
    curses.curs_set(True)
    curses.use_default_colors()

    # Draw banner on stdscr
    stdscr.addstr(0, (curses.COLS // 2) - 10, "=" * 20)
    stdscr.addstr(1, (curses.COLS // 2) - 4, "POGOCAL")
    stdscr.addstr(2, (curses.COLS // 2) - 10, "=" * 20)
    stdscr.refresh()

    # get events
    events = get_events()

    # this is where we'll saved desired events
    desired_events = []

    start_y = 4
    win_height = curses.LINES - start_y
    win_width = curses.COLS // 2

    left_win = curses.newwin(win_height, win_width, start_y, 0)
    right_win = curses.newwin(win_height, win_width, start_y, win_width)

    left_win.keypad(True)
    # right_win.keypad(True)

    # draw border
    left_win.border()
    right_win.border()

    # draw events onto left window
    for i, e in enumerate(events):
        name_part = e["name"]
        left_win.addstr(i + 1, 1, f"[ ] {i+1:02d}: {name_part}")

    # refresh to see changes made
    left_win.refresh()
    right_win.refresh()

    # Start cursor at first event checkbox
    cursor_y = 1
    cursor_x = 2
    left_win.move(cursor_y, cursor_x)

    # print the 1st event
    # these lines print the event data onto right_win
    event_data = events[cursor_y - 1]

    lines_to_print = get_lines_to_print(event_data)

    # print the data onto the right window while staying within the border
    for i, line in enumerate(lines_to_print):
        # only print this line if it will fit inside the window without overwriting the bottom border
        if i + 1 < right_win.getmaxyx()[0] - 1:
            # print while avoiding overflow horizontally
            right_win.addstr(i + 1, 1, line[:right_win.getmaxyx()[1] - 2])

    lines_to_print.clear()

    right_win.refresh()

    while True:
        c = left_win.getch()

        if c == curses.KEY_UP or c == ord('k'):
            # loop the cursor if we're at the 1st event and hit KEY_UP
            if cursor_y == 1:
                cursor_y = len(events)
            else:
                cursor_y -= 1

            left_win.move(cursor_y, cursor_x)

            # print the event's info on the right window
            # cursor_y = 1 would print the 0th event in events
            # clear previous text without clearing border
            right_win.erase()
            right_win.border()

            # these lines print the event data onto right_win
            event_data = events[cursor_y - 1]

            lines_to_print = get_lines_to_print(event_data)

            # print the data onto the right window while staying within the border
            for i, line in enumerate(lines_to_print):
                # only print this line if it will fit inside the window without overwriting the bottom border
                if i + 1 < right_win.getmaxyx()[0] - 1:
                    # print while avoiding overflow horizontally
                    right_win.addstr(i + 1, 1, line[:right_win.getmaxyx()[1] - 2])

            lines_to_print.clear()

            right_win.refresh()

        elif c == curses.KEY_DOWN or c == ord('j'):
            # loop the cursor if we're at the last event and hit KEY_DOWN
            if cursor_y == len(events):
                cursor_y = 1
            else:
                cursor_y += 1

            left_win.move(cursor_y, cursor_x)

            # clear previous text without clearing border
            right_win.erase()
            right_win.border()

            # these lines print the event data onto right_win
            event_data = events[cursor_y - 1]

            lines_to_print = get_lines_to_print(event_data)

            # print the data onto the right window while staying within the border
            for i, line in enumerate(lines_to_print):
                # only print this line if it will fit inside the window without overwriting the bottom border
                if i + 1 < right_win.getmaxyx()[0] - 1:
                    # print while avoiding overflow horizontally
                    right_win.addstr(i + 1, 1, line[:right_win.getmaxyx()[1] - 2])

            lines_to_print.clear()

            right_win.refresh()

        # we do this bc sometimes enter gets interpreted as a 10 or 13
        elif c in (curses.KEY_ENTER, 10, 13):
            char_at_cursor = chr(left_win.inch(cursor_y,cursor_x))
            if char_at_cursor == " ":
                left_win.addch(cursor_y, cursor_x, CHECK)
                # add the event to desired_events
                desired_events.append(events[cursor_y - 1])
            elif char_at_cursor == CHECK:
                left_win.addch(cursor_y, cursor_x, " ")
        elif c == ord('q'):
            break

        left_win.move(cursor_y, cursor_x)
        left_win.refresh()


def main():
    events_endpoint = f"https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/events.json"
    response = requests.get(events_endpoint).json()
    print(f"Found {len(response)} events")

    # print name of each event (led by the number of the event)
    for i, r in enumerate(response):
        i += 1
        print(f"- {i:02d}: {r["name"]}")




if __name__ == "__main__":
    # main()
    wrapper(curse)
