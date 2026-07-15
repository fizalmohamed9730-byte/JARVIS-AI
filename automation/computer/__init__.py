"""Computer automation sub-package providing cross-platform system controls."""

from automation.computer.apps import ApplicationManager
from automation.computer.system import SystemControls


class ComputerManager:
    """Facade combining application and system controls for the automation engine."""

    def __init__(self) -> None:
        self._apps = ApplicationManager()
        self._system = SystemControls()

    # Application methods
    def open_application(self, name: str) -> dict:
        return self._apps.open_application(name)

    def close_application(self, name: str) -> dict:
        return self._apps.close_application(name)

    def get_running_apps(self) -> list:
        return self._apps.get_running_apps()

    def search_applications(self, query: str) -> list:
        return self._apps.search_applications(query)

    # System methods
    def get_volume(self) -> int:
        return self._system.get_volume()

    def set_volume(self, level: int) -> dict:
        return self._system.set_volume(level)

    def get_brightness(self) -> int:
        return self._system.get_brightness()

    def set_brightness(self, level: int) -> dict:
        return self._system.set_brightness(level)

    def get_wifi_status(self) -> dict:
        return self._system.get_wifi_status()

    def toggle_wifi(self) -> dict:
        return self._system.toggle_wifi()

    def get_bluetooth_status(self) -> dict:
        return self._system.get_bluetooth_status()

    def toggle_bluetooth(self) -> dict:
        return self._system.toggle_bluetooth()

    def get_battery_info(self) -> dict:
        return self._system.get_battery_info()

    def get_system_info(self) -> dict:
        return self._system.get_system_info()

    def shutdown(self) -> dict:
        return self._system.shutdown()

    def restart(self) -> dict:
        return self._system.restart()

    def sleep(self) -> dict:
        return self._system.sleep()

    def lock_screen(self) -> dict:
        return self._system.lock_screen()

    def get_clipboard(self) -> str:
        return self._system.get_clipboard()

    def set_clipboard(self, content: str) -> dict:
        return self._system.set_clipboard(content)

    def take_screenshot(self, save_path: str = "") -> dict:
        return self._system.take_screenshot(save_path)
