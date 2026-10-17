import unittest
from datetime import datetime
from types import SimpleNamespace

from textual.app import App
from textual.widgets import SelectionList

from library.textual_widgets import IpodReviewAction, IpodReviewScreen

PLAYS = [
    SimpleNamespace(id=10, track_name="Filler", artist_name="Minor Threat", album_name="Complete Discography",
                    played_at=datetime(2026, 10, 17, 18, 30).astimezone(), played_at_estimated=False),
    SimpleNamespace(id=11, track_name="I Don't Wanna Hear It", artist_name="Minor Threat", album_name=None,
                    played_at=datetime(2026, 10, 17, 18, 32).astimezone(), played_at_estimated=True),
]


class ReviewApp(App):
    def __init__(self):
        super().__init__()
        self.result = "not dismissed"

    def on_mount(self) -> None:
        self.push_screen(IpodReviewScreen(PLAYS), callback=self.set_result)

    def set_result(self, result) -> None:
        self.result = result


class IpodReviewScreenTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_plays_selected_by_default(self):
        app = ReviewApp()
        async with app.run_test() as pilot:
            await pilot.click("#ipod-scrobble")
        self.assertEqual(app.result, (IpodReviewAction.SCROBBLE, [10, 11]))

    async def test_scrobble_only_checked_plays(self):
        app = ReviewApp()
        async with app.run_test() as pilot:
            app.screen.query_one(SelectionList).deselect(11)
            await pilot.click("#ipod-scrobble")
        self.assertEqual(app.result, (IpodReviewAction.SCROBBLE, [10]))

    async def test_discard_checked_plays(self):
        app = ReviewApp()
        async with app.run_test() as pilot:
            app.screen.query_one(SelectionList).deselect(10)
            await pilot.click("#ipod-discard")
        self.assertEqual(app.result, (IpodReviewAction.DISCARD, [11]))

    async def test_escape_defers_review(self):
        app = ReviewApp()
        async with app.run_test() as pilot:
            await pilot.press("escape")
        self.assertIsNone(app.result)


if __name__ == "__main__":
    unittest.main()
