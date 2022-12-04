import datetime
import pandas as pd

from googleapiclient.discovery import build

from calendar_api import create_event, get_events, get_credentials, date_to_str, ZurichTZ
from text_to_speech import text_to_speech
from speech_to_text import speech_to_text

#
#  parsing
#

date_specifier = "on the"

date_relativeness = ["today", "tomorrow"]
date_relativeness_delta = [0, 1]

event_durations = {
    "30 minute": {"hours": 0, "minutes": 30},
    "1 hour": {"hours": 1, "minutes": 0},
    "one hour": {"hours": 1, "minutes": 0},
    "2 hour": {"hours": 2, "minutes": 0},
    "two hour": {"hours": 2, "minutes": 0}
}

# time - duration
time_frame_definitions = {
    "morning": [datetime.time(hour=8, minute=0), 4],
    "noon": [datetime.time(hour=12, minute=0), 6],
    "evening": [datetime.time(hour=12, minute=0), 6],
    "afternoon": [datetime.time(hour=12, minute=0), 6],
    "night": [datetime.time(hour=18, minute=0), 4]
}


class EventRequest:
    date: str
    time: str
    duration: dict
    flex_duration_hours: int

    def __init__(self) -> None:
        self.duration = {"hours": 0, "minutes": 30}

    def __repr__(self) -> str:
        return f"{self.date} - {self.time} - {self.flex_duration_hours}"

    def is_well_defined(self):
        return self.flex_duration_hours == 0

def parse_event(text:str) -> EventRequest:
    event_req = EventRequest()
    text = text.lower()
    day_delta = 0

    # Check for date relativeness or specific date
    found_relativeness = [phrase in text for phrase in date_relativeness]
    if date_specifier in text:
        raise NotImplementedError(0)
    elif sum(found_relativeness) > 0:
        day_delta = date_relativeness_delta[found_relativeness.index(True)]
        event_req.date = datetime.datetime.now().date() + datetime.timedelta(days=day_delta)

    # Check for duration
    found_duration = [d for d in event_durations.keys() if d in text]
    if len(found_duration) > 0:
        event_req.duration = event_durations[found_duration[0]]
    print(event_req.duration)

    # Check for time frame
    found_timeframe = [tf for tf in time_frame_definitions.keys() if tf in text]
    if len(found_timeframe):
        event_req.time = time_frame_definitions[found_timeframe[0]][0]
        event_req.flex_duration_hours = time_frame_definitions[found_timeframe[0]][1]

    return event_req

#
# Comprehension pipeline
#

class EventBookingPipeline:

    def __init__(self) -> None:
        self.max_ping_pongs = 2
        self.api_cred = get_credentials()
        self.service = build('calendar', 'v3', credentials=self.api_cred)

    def yes_no_dialog(self, event_req: EventRequest, propose_time:datetime.datetime) -> EventRequest:
        time_format = "%I:%M %p"
        text_to_speech(f"Would {propose_time.strftime(time_format)} work for you?")

        answer = speech_to_text(duration=2)
        # answer = "yes"

        if "yes" in answer.lower():
            event_req.time = propose_time.time()
            event_req.flex_duration_hours = 0

        # Return event_req
        return event_req


    def handle_create_event(self, event_req: EventRequest, name = None):
        ''' Create an event with a specific event request '''
        start = datetime.datetime.combine(event_req.date, event_req.time)
        end = start + datetime.timedelta(hours=event_req.duration["hours"], minutes=event_req.duration["minutes"])
        create_event(self.service, "Appointment", date_to_str(start), date_to_str(end), attendee=name)


    def attempt_disambiguate_event_request(self, event_req: EventRequest):
        ''' Find a time in the given flexible time range provided by event_req and talk back to user. '''
        start = datetime.datetime.combine(event_req.date, event_req.time)
        end = start + datetime.timedelta(hours=event_req.flex_duration_hours)
        other_events = get_events(self.service, date_to_str(start), date_to_str(end))

        # find 1h spot between events
        prev_event_time = start.astimezone(ZurichTZ)
        for event in other_events.itertuples():
            diff_m = pd.Timedelta(event.start.astimezone(ZurichTZ) - prev_event_time).seconds / 60.0
            print(f'[Info] found event "{event.summary}" >> time diff:  {diff_m}')
            if diff_m >= event_req.duration["hours"]*60 + event_req.duration["minutes"]:
                break
            else:
                prev_event_time = event.end.astimezone(ZurichTZ)

        # run poss-neg communication dialog
        event_req = self.yes_no_dialog(event_req, prev_event_time)

        return event_req



    def run(self):
        text_to_speech("Hello. How may I assist you?")
        text = speech_to_text(duration=5)
        # text = "Book an appointment tomorrow morning"

        # parse event
        event_req = parse_event(text)

        # create or disambiguate
        if event_req.is_well_defined():
            self.handle_create_event(event_req)
        else:
            is_solved = self.attempt_disambiguate_event_request(event_req)
            if is_solved:
                text_to_speech("What's your name please?")
                text = speech_to_text(duration=2)
                self.handle_create_event(event_req, text.replace("My name is", "").strip())


        if not event_req.is_well_defined():
            text_to_speech("We could not handle your request. One of our assistants will call you shortly")
            return
        else:
            text_to_speech("Your appointment was booked successfully. Thank you.")
            return




p = EventBookingPipeline()
p.run()