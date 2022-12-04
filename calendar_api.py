from __future__ import print_function

import datetime
from traceback import print_stack
import pandas as pd
import os.path
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']
ZurichTZ = pytz.timezone('Europe/Zurich')


def get_events(service, start_time, end_time) -> pd.DataFrame:
    ''' Return events between then time fram (max 100). Ordered on start time'''
    events_result = service.events().list(calendarId='primary',
            timeMin=start_time,
            timeMax=end_time,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    print(start_time, " ---", end_time)
    events = events_result.get('items', [])
    print("Found :", len(events))

    # Prints the start and name of the next 10 events
    columns = ["start", "end", "summary"]
    parsed_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        summary = event['summary']
        parsed_events.append( [start, end, summary] )

    df = pd.DataFrame(data=parsed_events, columns=columns)
    df['start'] = pd.to_datetime(df.start)
    df['end'] = pd.to_datetime(df.end)
    return df

def create_event(
    service,
    event_summary:str,
    start:str,
    end:str,
    attendee=None,
    attendee_email=None
) -> str:
    ''' Create an event and returns the link in the calendar. If failed, returns None '''
    event_template = {
        'summary':  f'Medical Appointment with {attendee}' if attendee else 'Medical Appointment',
        'location': 'Route de praz Veguey',
        'description': f'Medical Appointment with {attendee}' if attendee else 'Medical Appointment',
        'start': {
            'dateTime': start,
            'timeZone': 'Europe/Zurich',
        },
        'end': {
            'dateTime': end,
            'timeZone': 'Europe/Zurich',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
            {'method': 'email', 'minutes': 24 * 60},
            {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    if attendee_email:
        event_template.update({
            'attendees': [
                {'email': attendee_email}
            ]
        })

    event_hlink = None
    try:
        event = service.events().insert(calendarId='primary', body=event_template).execute()
        print('Event created: %s' % (event.get('htmlLink')))
        event_hlink = event.get('htmlLink')
    except Exception as e:
        print("We got an error:", e)
        print_stack()

    return event_hlink


def get_credentials():
    ''' Get credentials to use the calendar api '''
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def date_to_str(date):
    return date.astimezone(ZurichTZ).isoformat()
    # return date.isoformat()


def main():
    """
    """
    creds = get_credentials()

    try:
        service = build('calendar', 'v3', credentials=creds)

        # First the current time
        now = datetime.datetime.now()  # 'Z' indicates UTC time
        end_date = datetime.datetime.now() + datetime.timedelta(days=2)
        df = get_events(service, date_to_str(now), date_to_str(end_date))
        print(df.head())

        # Create event
        start = datetime.datetime.now()
        end = start + datetime.timedelta(hours=1)
        event_hlink = create_event(service, "Appointment", date_to_str(start), date_to_str(end), None, None)
        if event_hlink == None:
            print("Failed to create event")

        # Get the appointments again
        df = get_events(service, date_to_str(now), date_to_str(end_date))
        print(df.head())

    except HttpError as error:
        print('An error occurred: %s' % error)


if __name__ == '__main__':
    main()