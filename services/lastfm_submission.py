"""Signed single-scrobble submission with explicit Last.fm acceptance checking.

Protocol: https://www.last.fm/api/show/track.scrobble
Signatures: https://www.last.fm/api/authspec (section 8).
"""
from dataclasses import dataclass
from hashlib import md5
from xml.etree import ElementTree

import httpx

LASTFM_SUBMISSION_URL = 'https://ws.audioscrobbler.com/2.0/'


class SubmissionError(ValueError):
    """The service returned an API error or an unverifiable response."""


@dataclass(frozen=True)
class SubmissionResult:
    accepted: bool
    message: str = ''


def parse_submission_response(body: str) -> SubmissionResult:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        raise SubmissionError('Invalid Last.fm submission response.') from error
    if root.tag != 'lfm' or root.get('status') != 'ok':
        error = root.find('error')
        message = error.text if error is not None else None
        raise SubmissionError(message or 'Last.fm rejected the submission request.')
    scrobbles = root.find('scrobbles')
    if scrobbles is None:
        raise SubmissionError('Last.fm did not confirm submission acceptance.')
    entries = scrobbles.findall('scrobble')
    if len(entries) != 1:
        raise SubmissionError('Unexpected Last.fm submission count.')
    ignored = entries[0].find('ignoredMessage')
    if ignored is None or ignored.get('code') is None:
        raise SubmissionError('Last.fm did not provide a submission result.')
    accepted = (scrobbles.get('accepted') == '1'
                and scrobbles.get('ignored') == '0'
                and ignored.get('code') == '0')
    message = ignored.text or f"Last.fm ignored the scrobble (code {ignored.get('code')})."
    return SubmissionResult(accepted, '' if accepted else message)


async def submit_scrobble(
    *, api_key: str, api_secret: str, session_key: str, artist: str,
    title: str, timestamp: int, album: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SubmissionResult:
    if not api_key or not api_secret or not session_key:
        raise SubmissionError('Last.fm submission credentials are unavailable.')
    params = {
        'method': 'track.scrobble', 'api_key': api_key, 'sk': session_key,
        'artist': artist, 'track': title, 'timestamp': str(timestamp),
    }
    if album:
        params['album'] = album
    signature = ''.join(key + params[key] for key in sorted(params)) + api_secret
    params['api_sig'] = md5(signature.encode('utf-8')).hexdigest()
    # No format parameter requests the documented XML response. Credentials stay
    # in the POST body; HTTPS is intentional even when legacy reads use HTTP.
    async with httpx.AsyncClient(timeout=15, transport=transport) as client:
        response = await client.post(LASTFM_SUBMISSION_URL, data=params)
        response.raise_for_status()
    return parse_submission_response(response.text)
