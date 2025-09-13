import re

import aiohttp


async def clean_up_title(title: str) -> str:
    """
    Clean up the album or song title to get the actual name.
    Examples: High 'N' Dry (Remastered 2018), Time to Break Up (Bonus Track)
    Returns: High 'N' Dry, Time to Break Up

    Args:
        title (str): The title to clean up.

    Returns:
        str: The cleaned up title.
    """
    filter_words = {
        'remaster',
        'bonus',
        'extended',
        'anniversary',
        'edit',
        'deluxe',
        'reissue',
        'explicit',
        'album version'
    }

    pattern = r'\([^)]*(?:{})[^)]*\)|\[[^]]*(?:{})[^]]*\]'.format(
        '|'.join(filter_words), '|'.join(filter_words)
    )

    clean_title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

    return clean_title


async def internet(timeout=3):
    """
    Check internet connectivity by making HTTP requests to reliable endpoints.
    """
    test_urls = [
        "https://httpbin.org/status/200",
        "https://www.google.com"
    ]

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        for url in test_urls:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return True
            except Exception:
                continue

    return False


def lastfm_friendly(input: str) -> str:
    # Last.fm API has issues with '+' in artist/track/album names
    # Because '+' is interpreted as a space, we need to encode it as '%2B'.
    return input.replace("+", "%2B")

