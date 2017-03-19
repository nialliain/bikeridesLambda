from unittest import TestCase, main
from mock import Mock, patch
from datetime import date
import json

from load import latest_status, is_newer_than, notify_by_text, get_history_from_spot


class TestLoad(TestCase):


    @patch('load.get_history_from_s3')
    def test_latest_status(self, get_history_from_s3):
        get_history_from_s3.return_value = [{'name': 'Niall',
                                             'location': 'somewhere exotic',
                                             'timeStamp': 'high noon'}]
        status_text = latest_status()
        self.assertEqual('Niall\'s last tracked location was somewhere exotic at high noon.', status_text)

    def test_is_newer_than(self):
        self.assertTrue(is_newer_than('2017-03-15T12:10:06+0000', {'dateTime':'2017-03-15T14:10:06+0000'}))
        self.assertFalse(is_newer_than('2017-03-15T16:10:06+0000', {'dateTime':'2017-03-15T14:10:06+0000'}))

    @patch('load._get_twilio')
    def test_notify_by_text(self, _get_twilio):
        mock_twilio = Mock()
        _get_twilio.return_value = mock_twilio
        notify_by_text({'timeStamp': date.today().strftime('%Y-%m-%d')}, {'timeStamp': date.today().strftime('%Y-%m-%d')})
        mock_twilio.messages.create.assert_not_called()
        notify_by_text({'timeStamp': '2017-03-15T12:10:06+0000'}, {'timeStamp': date.today().strftime('%Y-%m-%d'), 'location':'Slough'})
        mock_twilio.messages.create.assert_called_with(body='New location: Slough at ' + date.today().strftime('%Y-%m-%d') + '.', from_='+441631402022', to='+447793055904')

    @patch('load._get_gmaps')
    @patch('requests.get')
    def test_get_history_from_spot(self, get, get_gmaps):
        sampleSpotResp = '''{"response":{"feedMessageResponse":{"count":2,"feed":{"id":"0kh77fpkuvgEaVFm0LklfeKXetFB6Iqgr","name":"poller","description":"poller","status":"ACTIVE","usage":0,"daysRange":7,"detailedMessageShown":true,"type":"SHARED_PAGE"},"totalCount":20,"activityCount":0,"messages":{"message":[{"@clientUnixTime":"0","id":709998376,"messengerId":"0-2533810","messengerName":"Niall","unixTime":1489587006,"messageType":"UNLIMITED-TRACK","latitude":56.44958,"longitude":-5.72681,"modelId":"SPOTTRACE","showCustomMsg":"Y","dateTime":"2017-03-15T14:10:06+0000","batteryState":"GOOD","hidden":0,"altitude":-103},{"@clientUnixTime":"0","id":709998429,"messengerId":"0-2533810","messengerName":"Niall","unixTime":1489586406,"messageType":"UNLIMITED-TRACK","latitude":56.44864,"longitude":-5.7378,"modelId":"SPOTTRACE","showCustomMsg":"Y","dateTime":"2017-03-15T14:00:06+0000","batteryState":"GOOD","hidden":0,"altitude":0}]}}}}'''
        spotResp = Mock()
        spotResp.json.return_value = json.loads(sampleSpotResp)
        get.return_value = spotResp
        gmaps = Mock()
        gmaps.reverse_geocode.return_value = [{'address_components': []}]
        get_gmaps.return_value = gmaps
        resp = get_history_from_spot('2017-03-15T12:10:06+0000')
        self.assertEqual(2, len(resp))
        resp = get_history_from_spot('2017-03-15T14:00:06+0000')
        self.assertEqual(1, len(resp))
        print(resp)
        self.assertEqual(resp[0]['name'], 'Niall')
        self.assertEqual(resp[0]['timeStamp'], '2017-03-15T14:10:06+0000')
        self.assertEqual(resp[0]['lat'], 56.44958)
        self.assertEqual(resp[0]['lon'], -5.72681)
        self.assertEqual(resp[0]['messageType'], 'UNLIMITED-TRACK')

if __name__ == "__main__":
    main()