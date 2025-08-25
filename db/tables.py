from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Scrobble(Base):
    __tablename__ = "scrobbles"

    id = Column(Integer, primary_key=True, index=True)
    track_name = Column(String, index=True, nullable=False)
    artist_name = Column(String, index=True, nullable=False)
    album_name = Column(String, nullable=True)
    scrobbled_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Scrobble(track_name='{self.track_name}', artist_name='{self.artist_name}')>"
