"""
usage: python -m scripts.sandbox_lastfm

Simple script to test/debug the LastFmService
"""
import asyncio

from pylast import Artist, Album, Track

from services.lastfm_service import LastFmService


async def main():
    lastfm_service = LastFmService()

    artist: Artist = lastfm_service.network.get_artist("NOFX")

    album: Album = lastfm_service.network.get_album("NOFX", "Punk in Drublic")

    track: Track = lastfm_service.network.get_track("NOFX", "Linoleum")


if __name__ == "__main__":
    asyncio.run(main())

