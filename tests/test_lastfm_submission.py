import unittest
from datetime import UTC, datetime
from hashlib import md5
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs

import httpx

from models.schemas import Track
from services.lastfm_service import LastFmService
from services.lastfm_submission import SubmissionError, SubmissionResult, parse_submission_response, submit_scrobble


def response_xml(accepted='1', ignored='0', code='0', message=''):
    return (f'<lfm status="ok"><scrobbles accepted="{accepted}" ignored="{ignored}">'
            f'<scrobble><ignoredMessage code="{code}">{message}</ignoredMessage>'
            '</scrobble></scrobbles></lfm>')


class SubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_https_post_and_original_timestamp(self):
        def respond(request):
            self.assertEqual(request.method, 'POST')
            self.assertEqual(request.url.scheme, 'https')
            self.assertFalse(request.url.query)
            params = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
            signature = params.pop('api_sig')
            expected = 'albumRecordapi_keykeyartistBjörkmethodtrack.scrobblesksessiontimestamp1234567890trackSongsecret'
            self.assertEqual(signature, md5(expected.encode()).hexdigest())
            self.assertEqual(params['timestamp'], '1234567890')
            self.assertNotIn('format', params)
            return httpx.Response(200, text=response_xml())
        result = await submit_scrobble(api_key='key', api_secret='secret', session_key='session',
                                       artist='Björk', title='Song', album='Record', timestamp=1234567890,
                                       transport=httpx.MockTransport(respond))
        self.assertTrue(result.accepted)

    def test_rejected_and_ambiguous_responses_are_not_accepted(self):
        result = parse_submission_response(response_xml('0', '1', '3', 'Timestamp was too old'))
        self.assertFalse(result.accepted)
        self.assertEqual(result.message, 'Timestamp was too old')
        self.assertFalse(parse_submission_response(response_xml('1', '0', '3')).accepted)
        for body in ('not xml', '<lfm status="ok"/>', '<lfm status="failed"><error code="9">Invalid session</error></lfm>'):
            with self.assertRaises(SubmissionError):
                parse_submission_response(body)

    async def test_http_failure_propagates(self):
        with self.assertRaises(httpx.HTTPStatusError):
            await submit_scrobble(api_key='key', api_secret='secret', session_key='session',
                                   artist='Artist', title='Song', timestamp=1,
                                   transport=httpx.MockTransport(lambda _: httpx.Response(503)))

    async def test_service_acceptance_and_rejection_use_existing_auth(self):
        service = LastFmService.__new__(LastFmService)
        service._run_sync = AsyncMock(return_value='existing-session')
        track = Track(name='Song', clean_name='Song', artist='Artist', album='Album', clean_album='Album')
        started = datetime(2026, 9, 29, tzinfo=UTC)
        with patch('services.lastfm_service.submit_scrobble', new_callable=AsyncMock) as submit:
            submit.return_value = SubmissionResult(True)
            result = await service.scrobble(track, started)
            self.assertIsNotNone(result)
            self.assertEqual(int(result.scrobbled_at.timestamp()), int(started.timestamp()))
            self.assertEqual(submit.call_args.kwargs['timestamp'], int(started.timestamp()))
            self.assertEqual(submit.call_args.kwargs['session_key'], 'existing-session')
            service._run_sync.assert_awaited_once_with(service._get_session_key)
            submit.return_value = SubmissionResult(False, 'Timestamp was too old')
            self.assertIsNone(await service.scrobble(track, started))
            submit.side_effect = SubmissionError('Invalid response')
            self.assertIsNone(await service.scrobble(track, started))

    def test_auth_reuses_or_populates_pylast_session(self):
        service = LastFmService.__new__(LastFmService)
        service.network = SimpleNamespace(session_key='cached')
        with patch('services.lastfm_service.pylast.SessionKeyGenerator') as generator:
            self.assertEqual(service._get_session_key(), 'cached')
            generator.assert_not_called()
            service.network.session_key = None
            generator.return_value.get_session_key.return_value = 'new-session'
            self.assertEqual(service._get_session_key(), 'new-session')
            self.assertEqual(service.network.session_key, 'new-session')
