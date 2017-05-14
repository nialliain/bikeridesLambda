import json
import os
from datetime import date

import boto3
import requests
from googlemaps import Client
from twilio.rest import TwilioRestClient

s3 = boto3.resource('s3')


def run_poll(event, context):
    """ Update S3 with latest trackpoints from Spot. """
    s3_history = get_history_from_s3()
    s3_latest_timeStamp = s3_history[-1]['timeStamp']
    spot_new = get_history_from_spot( s3_latest_timeStamp )
    if spot_new:
        combined_history = s3_history + spot_new
        write_to_s3(combined_history)
        notify_by_text(s3_history[-1], combined_history[-1])
    else:
        pass


def latest_status():
    """ Return a textual summary of the latest trackpoint. """
    latest = get_history_from_s3()[-1]
    return '{}\'s last tracked location was {} at {}.'.format(latest['name'], latest['location'], latest['timeStamp'])


def is_newer_than(s3_latest_timeStamp, spot_message):
    return s3_latest_timeStamp < str(spot_message['dateTime'])


def get_history_from_spot(s3_latest_timeStamp):
    gmaps = _get_gmaps()
    def _build_track_point(spot_message):
        def _reverse_geocode(lat, lon):
            try:
                for addr in gmaps.reverse_geocode((lat, lon))[0]['address_components']:
                    if 'postal_town' in addr['types']:
                        return addr['long_name']
            except:
                return '[Reverse Geocode Error]'
        track_point = dict()
        track_point['lat'] = spot_message['latitude']
        track_point['lon'] = spot_message['longitude']
        track_point['timeStamp'] = str(spot_message['dateTime'])
        track_point['messageType'] = str(spot_message['messageType'])
        track_point['location'] = _reverse_geocode(spot_message['latitude'], spot_message['longitude'])
        track_point['name'] = str(spot_message['messengerName'])
        return track_point

    r = requests.get(
        'https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/0kh77fpkuvgEaVFm0LklfeKXetFB6Iqgr/message.json')
    track = [_build_track_point(msg) for msg in r.json()['response']['feedMessageResponse']['messages']['message'] if is_newer_than(s3_latest_timeStamp, msg)]
    track.reverse()
    return track


def get_history_from_s3():
    return json.loads(s3.Object('bikerid.es', 'track/history.json').get()['Body'].read())


def write_to_s3(history):
    def _write_file_to_s3( name, content ):
        s3.Object('bikerid.es', 'track/{}.json'.format(name)).put(Body=json.dumps(content),
                                                                  ContentType='application/json')
    _write_file_to_s3('latest',history[-1])
    _write_file_to_s3('history',history)


def notify_by_text(previous_trackpoint, trackpoint):
    if previous_trackpoint['timeStamp'].startswith(date.today().strftime('%Y-%m-%d')):
        return
    twilio = _get_twilio()
    message = 'New location: {} at {}.'.format(trackpoint['location'], trackpoint['timeStamp'])
    for number in os.environ.get('alerts.numbers', []):
        twilio.messages.create(body=message, to=number, from_='+441631402022')


def _get_twilio():
    return TwilioRestClient(os.environ['twilio.account'], os.environ['twilio.token'])


def _get_gmaps():
    return Client(key=os.environ.get('gmaps.key', None))

if __name__ == '__main__':
    run_poll(None, None)

