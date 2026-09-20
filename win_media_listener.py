"""
win_media_listener.py – Background thread that polls Windows GSMTC
for currently-playing media metadata and emits Qt signals.

Runs its own asyncio event loop on a daemon thread so the Qt event
loop is never blocked.
"""

import asyncio
import threading
import io

from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtGui import QPixmap, QImage


class MediaListener(QObject):
    """Bridges WinRT GSMTC → Qt signals."""


    media_changed = Signal(str, str, bool, str)   # title, artist, is_playing, aumid
    thumbnail_changed = Signal(QPixmap)
    session_lost = Signal()                  # no active media session

    def __init__(self, poll_interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self._poll_ms = poll_interval_ms
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._timer.timeout.connect(self._on_tick)


        self._available = True
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager,
            )
        except ImportError:
            self._available = False

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._last_title = ""
        self._last_artist = ""


    def start(self):
        if not self._available:
            return

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._timer.start(self._poll_ms)

    def stop(self):
        self._timer.stop()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def try_play_pause(self):
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._send_play_pause(), self._loop)

    def try_next(self):
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._send_next(), self._loop)

    def try_prev(self):
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._send_prev(), self._loop)


    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()


    def _on_tick(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._poll(), self._loop)

    async def _poll(self):
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as Mgr,
                GlobalSystemMediaTransportControlsSessionPlaybackStatus as PBStatus,
            )
            sessions = await Mgr.request_async()
            session = sessions.get_current_session()
            if session is None:
                self.session_lost.emit()
                return

            info = await session.try_get_media_properties_async()
            title = info.title or ""
            artist = info.artist or ""
            aumid = session.source_app_user_model_id or ""
            pb = session.get_playback_info()
            is_playing = (pb.playback_status == PBStatus.PLAYING)

            self.media_changed.emit(title, artist, is_playing, aumid)


            if title != self._last_title or artist != self._last_artist:
                self._last_title = title
                self._last_artist = artist
                await self._fetch_thumbnail(info)
        except Exception:
            pass

    async def _fetch_thumbnail(self, info):
        try:
            ref = info.thumbnail
            if ref is None:
                self.thumbnail_changed.emit(QPixmap())
                return
            stream = await ref.open_read_async()
            size = stream.size
            from winrt.windows.storage.streams import DataReader
            reader = DataReader(stream)
            await reader.load_async(size)
            buf = bytearray(size)
            reader.read_bytes(buf)
            reader.close()
            stream.close()

            img = QImage()
            img.loadFromData(bytes(buf))
            if not img.isNull():
                self.thumbnail_changed.emit(QPixmap.fromImage(img))
            else:
                self.thumbnail_changed.emit(QPixmap())
        except Exception:
            self.thumbnail_changed.emit(QPixmap())

    async def _send_play_pause(self):
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as Mgr,
            )
            sessions = await Mgr.request_async()
            session = sessions.get_current_session()
            if session:
                await session.try_toggle_play_pause_async()
        except Exception:
            pass

    async def _send_next(self):
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as Mgr,
            )
            sessions = await Mgr.request_async()
            session = sessions.get_current_session()
            if session:
                await session.try_skip_next_async()
        except Exception:
            pass

    async def _send_prev(self):
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as Mgr,
            )
            sessions = await Mgr.request_async()
            session = sessions.get_current_session()
            if session:
                await session.try_skip_previous_async()
        except Exception:
            pass
