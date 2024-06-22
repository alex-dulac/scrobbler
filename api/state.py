class AppState:
    def __init__(self):
        self.current_song = None
        self.is_scrobbling = False


app_state = AppState()


def get_app_state() -> AppState:
    return app_state
