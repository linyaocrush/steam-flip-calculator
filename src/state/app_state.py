from typing import Callable, Dict, Any, Optional
from models import Settings
from services.database import get_settings as get_db_settings, save_settings
from threading import Lock


class AppState:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AppState, cls).__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._settings = None
        self._subscribers = []

    def get_settings(self) -> Settings:
        if self._settings is None:
            self._settings = get_db_settings()
        return self._settings

    def update_settings(self, partial_settings: Dict[str, Any]) -> Settings:
        current = self.get_settings()
        
        for key, value in partial_settings.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        saved = save_settings(current)
        self._settings = saved
        self._notify_subscribers()
        return saved

    def subscribe(self, callback: Callable[[Settings], None]) -> Callable[[], None]:
        self._subscribers.append(callback)
        
        def unsubscribe():
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        return unsubscribe

    def _notify_subscribers(self):
        for callback in self._subscribers:
            try:
                callback(self._settings)
            except Exception as e:
                print(f"Error notifying subscriber: {e}")

    def refresh(self):
        self._settings = get_db_settings()
        self._notify_subscribers()


app_state = AppState()