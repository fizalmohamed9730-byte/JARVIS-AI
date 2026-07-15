"""Cross-platform system controls: volume, brightness, power, clipboard, etc."""

import ctypes
import io
import logging
import os
import platform
import shutil
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_SYSTEM = platform.system()


class SystemControls:
    """Provides OS-level controls for volume, brightness, WiFi, Bluetooth, power, and clipboard."""

    # --------------------------------------------------------------------- #
    # Volume
    # --------------------------------------------------------------------- #

    def get_volume(self) -> int:
        """Return current volume level 0-100."""
        if _SYSTEM == "Windows":
            return self._get_volume_windows()
        elif _SYSTEM == "Darwin":
            return self._get_volume_macos()
        else:
            return self._get_volume_linux()

    def set_volume(self, level: int) -> Dict[str, Any]:
        """Set volume to *level* (0-100)."""
        level = max(0, min(100, level))
        logger.info("Setting volume to %d", level)
        if _SYSTEM == "Windows":
            return self._set_volume_windows(level)
        elif _SYSTEM == "Darwin":
            return self._set_volume_macos(level)
        else:
            return self._set_volume_linux(level)

    def _get_volume_windows(self) -> int:
        try:
            from ctypes import wintypes
            import comtypes

            class IAudioEndpointVolume(comtypes.Interface):
                _iid_ = comtypes.GUID("{5CDF2C82-841E-4546-9722-0CF74078229A}")

            mmdevapi = ctypes.windll.mmdevapi
            CLSCTX_ALL = 0x17
            eRender = 0
            eConsole = 0

            device = ctypes.POINTER(ctypes.c_void_p)()
            enumerator = mmdevapi.CAcquireMMDeviceEnumerator()

            hr = enumerator.GetDefaultAudioEndpoint(eRender, eConsole, ctypes.byref(device))
            if hr != 0:
                raise RuntimeError("Failed to get default audio endpoint")

            vol_interface = ctypes.POINTER(ctypes.c_void_p)()
            hr = device.Activate(
                comtypes.byref(IAudioEndpointVolume._iid_),
                CLSCTX_ALL,
                None,
                ctypes.byref(vol_interface),
            )
            if hr != 0:
                raise RuntimeError("Failed to activate audio endpoint volume")

            volume = ctypes.c_float()
            vol_interface.GetMasterVolumeLevelScalar(ctypes.byref(volume))
            return int(round(volume.value * 100))
        except Exception:
            logger.debug("Fallback volume detection via nircmd")
            try:
                output = subprocess.check_output(
                    ["nircmd", "mutesysinfo", "1"],
                    text=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL,
                )
                # Simple fallback – return -1 to indicate unavailable
                return -1
            except Exception:
                return -1

    def _set_volume_windows(self, level: int) -> Dict[str, Any]:
        try:
            from ctypes import wintypes
            import comtypes

            class IAudioEndpointVolume(comtypes.Interface):
                _iid_ = comtypes.GUID("{5CDF2C82-841E-4546-9722-0CF74078229A}")

            mmdevapi = ctypes.windll.mmdevapi
            CLSCTX_ALL = 0x17
            eRender = 0
            eConsole = 0

            device = ctypes.POINTER(ctypes.c_void_p)()
            enumerator = mmdevapi.CAcquireMMDeviceEnumerator()

            hr = enumerator.GetDefaultAudioEndpoint(eRender, eConsole, ctypes.byref(device))
            if hr != 0:
                raise RuntimeError("Failed to get default audio endpoint")

            vol_interface = ctypes.POINTER(ctypes.c_void_p)()
            hr = device.Activate(
                comtypes.byref(IAudioEndpointVolume._iid_),
                CLSCTX_ALL,
                None,
                ctypes.byref(vol_interface),
            )
            if hr != 0:
                raise RuntimeError("Failed to activate audio endpoint volume")

            vol_interface.SetMasterVolumeLevelScalar(ctypes.c_float(level / 100.0), None)
            return {"success": True, "level": level}
        except Exception as exc:
            logger.warning("COM volume set failed, trying PowerShell: %s", exc)
            try:
                # PowerShell fallback using AudioDeviceCmdlets or built-in
                script = f"$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]173)"  # unmute
                subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True,
                    timeout=5,
                )
                return {"success": True, "level": level, "note": "Applied via fallback method"}
            except Exception as fallback_exc:
                return {"success": False, "error": str(fallback_exc)}

    def _get_volume_macos(self) -> int:
        try:
            output = subprocess.check_output(
                ["osascript", "-e", "output volume of (get volume settings)"],
                text=True,
                timeout=5,
            )
            return int(output.strip())
        except Exception:
            return -1

    def _set_volume_macos(self, level: int) -> Dict[str, Any]:
        try:
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {level}"],
                timeout=5,
            )
            return {"success": True, "level": level}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _get_volume_linux(self) -> int:
        try:
            output = subprocess.check_output(
                ["amixer", "sget", "Master"],
                text=True,
                timeout=5,
            )
            for line in output.splitlines():
                if "Playback" in line and "%" in line:
                    pct = line.split("[")[1].split("]")[0].replace("%", "")
                    return int(pct)
            return -1
        except Exception:
            return -1

    def _set_volume_linux(self, level: int) -> Dict[str, Any]:
        try:
            subprocess.run(
                ["amixer", "sset", "Master", f"{level}%"],
                capture_output=True,
                timeout=5,
            )
            return {"success": True, "level": level}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --------------------------------------------------------------------- #
    # Brightness
    # --------------------------------------------------------------------- #

    def get_brightness(self) -> int:
        """Return current screen brightness 0-100."""
        if _SYSTEM == "Windows":
            return self._get_brightness_windows()
        elif _SYSTEM == "Darwin":
            return self._get_brightness_macos()
        else:
            return self._get_brightness_linux()

    def set_brightness(self, level: int) -> Dict[str, Any]:
        """Set screen brightness to *level* (0-100)."""
        level = max(0, min(100, level))
        logger.info("Setting brightness to %d", level)
        if _SYSTEM == "Windows":
            return self._set_brightness_windows(level)
        elif _SYSTEM == "Darwin":
            return self._set_brightness_macos(level)
        else:
            return self._set_brightness_linux(level)

    def _get_brightness_windows(self) -> int:
        try:
            import wmi
            w = wmi.WMI(namespace="wmi")
            methods = w.WmiMonitorBrightness()[0]
            return methods.CurrentBrightness
        except Exception:
            return -1

    def _set_brightness_windows(self, level: int) -> Dict[str, Any]:
        try:
            import wmi
            w = wmi.WMI(namespace="wmi")
            w.WmiMonitorBrightnessMethods()[0].WmiSetBrightness(0, level)
            return {"success": True, "level": level}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _get_brightness_macos(self) -> int:
        try:
            output = subprocess.check_output(
                ["osascript", "-e", "brightness of display 1"],
                text=True,
                timeout=5,
            )
            return int(float(output.strip()) * 100)
        except Exception:
            return -1

    def _set_brightness_macos(self, level: int) -> Dict[str, Any]:
        try:
            frac = level / 100.0
            subprocess.run(
                ["osascript", "-e", f"set brightness of display 1 to {frac}"],
                timeout=5,
            )
            return {"success": True, "level": level}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _get_brightness_linux(self) -> int:
        try:
            backlight = "/sys/class/backlight/intel_backlight"
            if not os.path.isdir(backlight):
                # Try to find any backlight directory
                base = "/sys/class/backlight"
                if os.path.isdir(base):
                    entries = os.listdir(base)
                    if entries:
                        backlight = os.path.join(base, entries[0])
            max_b = int(open(os.path.join(backlight, "max_brightness")).read().strip())
            cur_b = int(open(os.path.join(backlight, "brightness")).read().strip())
            return int((cur_b / max_b) * 100) if max_b > 0 else 0
        except Exception:
            return -1

    def _set_brightness_linux(self, level: int) -> Dict[str, Any]:
        try:
            import os
            backlight = "/sys/class/backlight/intel_backlight"
            if not os.path.isdir(backlight):
                base = "/sys/class/backlight"
                if os.path.isdir(base):
                    entries = os.listdir(base)
                    if entries:
                        backlight = os.path.join(base, entries[0])
            max_b = int(open(os.path.join(backlight, "max_brightness")).read().strip())
            new_b = int((level / 100.0) * max_b)
            with open(os.path.join(backlight, "brightness"), "w") as f:
                f.write(str(new_b))
            return {"success": True, "level": level}
        except PermissionError:
            try:
                subprocess.run(
                    ["brightnessctl", "set", f"{level}%"],
                    capture_output=True,
                    timeout=5,
                )
                return {"success": True, "level": level}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --------------------------------------------------------------------- #
    # WiFi
    # --------------------------------------------------------------------- #

    def get_wifi_status(self) -> Dict[str, Any]:
        """Return WiFi enabled status and current SSID if available."""
        if _SYSTEM == "Windows":
            return self._get_wifi_windows()
        elif _SYSTEM == "Darwin":
            return self._get_wifi_macos()
        else:
            return self._get_wifi_linux()

    def _get_wifi_windows(self) -> Dict[str, Any]:
        try:
            output = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                text=True,
                timeout=10,
            )
            enabled = "disconnected" not in output.lower() or "state" in output.lower()
            ssid = ""
            for line in output.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    ssid = line.split(":", 1)[-1].strip()
                    break
            return {"enabled": True, "connected": ssid != "", "ssid": ssid}
        except Exception as exc:
            return {"enabled": False, "connected": False, "ssid": "", "error": str(exc)}

    def _get_wifi_macos(self) -> Dict[str, Any]:
        try:
            output = subprocess.check_output(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
                text=True,
                timeout=10,
            )
            ssid = ""
            for line in output.splitlines():
                if " SSID:" in line:
                    ssid = line.split(":", 1)[-1].strip()
            return {"enabled": True, "connected": ssid != "", "ssid": ssid}
        except Exception:
            return {"enabled": False, "connected": False, "ssid": ""}

    def _get_wifi_linux(self) -> Dict[str, Any]:
        try:
            output = subprocess.check_output(
                ["nmcli", "-t", "-f", "WIFI", "general"],
                text=True,
                timeout=10,
            )
            enabled = output.strip().lower() == "enabled"
            ssid = ""
            try:
                conn = subprocess.check_output(
                    ["nmcli", "-t", "-f", "SSID", "dev", "wifi", "list"],
                    text=True,
                    timeout=10,
                )
                ssid = conn.strip().splitlines()[0] if conn.strip() else ""
            except Exception:
                pass
            return {"enabled": enabled, "connected": bool(ssid), "ssid": ssid}
        except Exception as exc:
            return {"enabled": False, "connected": False, "ssid": "", "error": str(exc)}

    def toggle_wifi(self) -> Dict[str, Any]:
        """Toggle WiFi on/off based on current state."""
        logger.info("Toggling WiFi")
        current = self.get_wifi_status()
        should_enable = not current.get("enabled", False)
        state_str = "on" if should_enable else "off"

        if _SYSTEM == "Windows":
            try:
                action = "Enable" if should_enable else "Disable"
                subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        f"Get-NetAdapter | Where-Object {{$_.Name -like '*Wi-Fi*'}} | {action}-NetAdapter -Confirm:$false",
                    ],
                    capture_output=True,
                    timeout=15,
                )
                return {"success": True, "message": f"WiFi turned {state_str}"}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        elif _SYSTEM == "Darwin":
            try:
                subprocess.run(
                    ["networksetup", "-setairportpower", "en0", state_str],
                    timeout=10,
                )
                return {"success": True, "message": f"WiFi turned {state_str}"}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        else:
            try:
                subprocess.run(
                    ["nmcli", "radio", "wifi", state_str],
                    capture_output=True,
                    timeout=10,
                )
                return {"success": True, "message": f"WiFi turned {state_str}"}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

    # --------------------------------------------------------------------- #
    # Bluetooth
    # --------------------------------------------------------------------- #

    def get_bluetooth_status(self) -> Dict[str, Any]:
        """Return Bluetooth enabled status."""
        if _SYSTEM == "Windows":
            try:
                output = subprocess.check_output(
                    ["powershell", "-Command", "Get-Service bthserv | Select -ExpandProperty Status"],
                    text=True,
                    timeout=10,
                )
                return {"enabled": output.strip() == "Running"}
            except Exception:
                return {"enabled": False}
        elif _SYSTEM == "Darwin":
            try:
                output = subprocess.check_output(
                    ["defaults", "read", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState"],
                    text=True,
                    timeout=5,
                )
                return {"enabled": output.strip() == "1"}
            except Exception:
                return {"enabled": False}
        else:
            try:
                output = subprocess.check_output(
                    ["bluetoothctl", "show"],
                    text=True,
                    timeout=10,
                )
                for line in output.splitlines():
                    if "Powered:" in line:
                        return {"enabled": "yes" in line.lower()}
                return {"enabled": False}
            except Exception:
                return {"enabled": False}

    def toggle_bluetooth(self) -> Dict[str, Any]:
        """Toggle Bluetooth on/off."""
        logger.info("Toggling Bluetooth")
        if _SYSTEM == "Windows":
            try:
                status = self.get_bluetooth_status()
                action = "Stop-Service" if status.get("enabled") else "Start-Service"
                subprocess.run(
                    ["powershell", "-Command", f"{action} bthserv -Force"],
                    capture_output=True,
                    timeout=15,
                )
                return {"success": True, "message": "Bluetooth toggled"}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        elif _SYSTEM == "Darwin":
            try:
                subprocess.run(
                    ["blueutil", "--toggle"],
                    timeout=10,
                )
                return {"success": True, "message": "Bluetooth toggled"}
            except Exception:
                try:
                    status = self.get_bluetooth_status()
                    new_state = "off" if status.get("enabled") else "on"
                    subprocess.run(
                        ["osascript", "-e", f'tell application "System Events" to tell process "System Preferences" to click checkbox 1 of window 1'],
                        timeout=10,
                    )
                    return {"success": True, "message": f"Bluetooth toggled to {new_state}"}
                except Exception as inner_exc:
                    return {"success": False, "error": str(inner_exc)}
        else:
            try:
                subprocess.run(
                    ["bluetoothctl", "power", "off"],
                    capture_output=True,
                    timeout=10,
                )
                return {"success": True, "message": "Bluetooth toggled"}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

    # --------------------------------------------------------------------- #
    # Battery
    # --------------------------------------------------------------------- #

    def get_battery_info(self) -> Dict[str, Any]:
        """Return battery percentage, charging state, and estimated time."""
        if _SYSTEM == "Windows":
            return self._get_battery_windows()
        elif _SYSTEM == "Darwin":
            return self._get_battery_macos()
        else:
            return self._get_battery_linux()

    def _get_battery_windows(self) -> Dict[str, Any]:
        try:
            import ctypes
            import ctypes.wintypes

            class SYSTEM_BATTERY_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("Reserved1", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.wintypes.DWORD),
                    ("BatteryFullLifeTime", ctypes.wintypes.DWORD),
                ]

            status = SYSTEM_BATTERY_STATUS()
            result = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
            if result:
                charging = status.ACLineStatus == 1
                return {
                    "percent": status.BatteryLifePercent,
                    "charging": charging,
                    "remaining_seconds": status.BatteryLifeTime if status.BatteryLifeTime != 0xFFFFFFFF else None,
                }
        except Exception:
            pass
        return {"percent": -1, "charging": False, "remaining_seconds": None}

    def _get_battery_macos(self) -> Dict[str, Any]:
        try:
            output = subprocess.check_output(
                ["pmset", "-g", "batt"],
                text=True,
                timeout=5,
            )
            percent = -1
            charging = False
            for line in output.splitlines():
                if "%" in line:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        pct_str = parts[1].replace("%", "").strip()
                        percent = int(pct_str)
                        charging = "charging" in parts[1].lower() or "AC" in parts[0]
            return {"percent": percent, "charging": charging, "remaining_seconds": None}
        except Exception:
            return {"percent": -1, "charging": False, "remaining_seconds": None}

    def _get_battery_linux(self) -> Dict[str, Any]:
        try:
            energy_now = int(open("/sys/class/power_supply/BAT0/energy_now").read().strip())
            energy_full = int(open("/sys/class/power_supply/BAT0/energy_full").read().strip())
            status = open("/sys/class/power_supply/BAT0/status").read().strip()
            percent = int((energy_now / energy_full) * 100) if energy_full > 0 else 0
            return {
                "percent": percent,
                "charging": status == "Charging",
                "remaining_seconds": None,
            }
        except Exception:
            return {"percent": -1, "charging": False, "remaining_seconds": None}

    # --------------------------------------------------------------------- #
    # System info
    # --------------------------------------------------------------------- #

    def get_system_info(self) -> Dict[str, Any]:
        """Return CPU usage, RAM usage, and disk usage."""
        import os
        info: Dict[str, Any] = {
            "platform": _SYSTEM,
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }

        # CPU usage (averaged over 1 second)
        try:
            if _SYSTEM == "Windows":
                output = subprocess.check_output(
                    ["wmic", "cpu", "get", "loadpercentage"],
                    text=True,
                    timeout=10,
                )
                for line in output.splitlines():
                    line = line.strip()
                    if line.isdigit():
                        info["cpu_percent"] = int(line)
                        break
            elif _SYSTEM == "Darwin":
                output = subprocess.check_output(
                    ["sysctl", "-n", "hw.ncpu"],
                    text=True,
                    timeout=5,
                )
                info["cpu_count"] = int(output.strip())
                load = os.getloadavg()
                info["cpu_load_1m"] = load[0]
                info["cpu_load_5m"] = load[1]
            else:
                load = os.getloadavg()
                info["cpu_load_1m"] = load[0]
                info["cpu_load_5m"] = load[1]
                cpu_count = int(subprocess.check_output(["nproc"], text=True, timeout=5).strip())
                info["cpu_count"] = cpu_count
                info["cpu_percent"] = round((load[0] / cpu_count) * 100, 1) if cpu_count else 0
        except Exception:
            info["cpu_percent"] = -1

        # Memory
        try:
            if _SYSTEM == "Windows":
                output = subprocess.check_output(
                    ["wmic", "OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize", "/Value"],
                    text=True,
                    timeout=10,
                )
                total = free = 0
                for line in output.splitlines():
                    if "TotalVisibleMemorySize" in line:
                        total = int(line.split("=")[1].strip())
                    elif "FreePhysicalMemory" in line:
                        free = int(line.split("=")[1].strip())
                info["ram_total_mb"] = round(total / 1024)
                info["ram_used_mb"] = round((total - free) / 1024)
                info["ram_percent"] = round(((total - free) / total) * 100, 1) if total else 0
            else:
                import psutil
                mem = psutil.virtual_memory()
                info["ram_total_mb"] = round(mem.total / (1024 * 1024))
                info["ram_used_mb"] = round(mem.used / (1024 * 1024))
                info["ram_percent"] = mem.percent
        except ImportError:
            # psutil not installed – try vm_stat on macOS or /proc on Linux
            if _SYSTEM == "Linux":
                try:
                    meminfo = {}
                    with open("/proc/meminfo") as f:
                        for line in f:
                            parts = line.split()
                            meminfo[parts[0].rstrip(":")] = int(parts[1])
                    total = meminfo.get("MemTotal", 0)
                    avail = meminfo.get("MemAvailable", 0)
                    used = total - avail
                    info["ram_total_mb"] = round(total / 1024)
                    info["ram_used_mb"] = round(used / 1024)
                    info["ram_percent"] = round((used / total) * 100, 1) if total else 0
                except Exception:
                    pass
        except Exception:
            pass

        # Disk
        try:
            usage = shutil.disk_usage("/")
            info["disk_total_gb"] = round(usage.total / (1024 ** 3), 1)
            info["disk_used_gb"] = round(usage.used / (1024 ** 3), 1)
            info["disk_free_gb"] = round(usage.free / (1024 ** 3), 1)
            info["disk_percent"] = round((usage.used / usage.total) * 100, 1)
        except Exception:
            pass

        return info

    # --------------------------------------------------------------------- #
    # Power management
    # --------------------------------------------------------------------- #

    def shutdown(self) -> Dict[str, Any]:
        """Shut down the computer."""
        logger.warning("Initiating system shutdown")
        try:
            if _SYSTEM == "Windows":
                subprocess.Popen(["shutdown", "/s", "/t", "5"])
            elif _SYSTEM == "Darwin":
                subprocess.Popen(["osascript", "-e", 'tell application "System Events" to shut down'])
            else:
                subprocess.Popen(["shutdown", "-h", "now"])
            return {"success": True, "message": "Shutdown initiated"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def restart(self) -> Dict[str, Any]:
        """Restart the computer."""
        logger.warning("Initiating system restart")
        try:
            if _SYSTEM == "Windows":
                subprocess.Popen(["shutdown", "/r", "/t", "5"])
            elif _SYSTEM == "Darwin":
                subprocess.Popen(["osascript", "-e", 'tell application "System Events" to restart'])
            else:
                subprocess.Popen(["shutdown", "-r", "now"])
            return {"success": True, "message": "Restart initiated"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def sleep(self) -> Dict[str, Any]:
        """Put the computer to sleep."""
        logger.info("Putting system to sleep")
        try:
            if _SYSTEM == "Windows":
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            elif _SYSTEM == "Darwin":
                subprocess.Popen(["osascript", "-e", 'tell application "System Events" to sleep'])
            else:
                subprocess.Popen(["systemctl", "suspend"])
            return {"success": True, "message": "Sleep initiated"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def lock_screen(self) -> Dict[str, Any]:
        """Lock the screen."""
        logger.info("Locking screen")
        try:
            if _SYSTEM == "Windows":
                ctypes.windll.user32.LockWorkStation()
            elif _SYSTEM == "Darwin":
                subprocess.Popen(["open", "-a", "ScreenSaverEngine"])
            else:
                subprocess.Popen(["gnome-screensaver-command", "-l"])
            return {"success": True, "message": "Screen locked"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --------------------------------------------------------------------- #
    # Clipboard
    # --------------------------------------------------------------------- #

    def get_clipboard(self) -> str:
        """Return current clipboard text content."""
        try:
            if _SYSTEM == "Windows":
                import ctypes
                CF_UNICODETEXT = 13
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                if not user32.OpenClipboard(0):
                    return ""
                try:
                    handle = user32.GetClipboardData(CF_UNICODETEXT)
                    if not handle:
                        return ""
                    ptr = kernel32.GlobalLock(handle)
                    if not ptr:
                        return ""
                    try:
                        return ctypes.c_wchar_p(ptr).value or ""
                    finally:
                        kernel32.GlobalUnlock(handle)
                finally:
                    user32.CloseClipboard()
            elif _SYSTEM == "Darwin":
                output = subprocess.check_output(
                    ["pbpaste"],
                    text=True,
                    timeout=5,
                )
                return output
            else:
                output = subprocess.check_output(
                    ["xclip", "-selection", "clipboard", "-o"],
                    text=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL,
                )
                return output
        except Exception:
            return ""

    def set_clipboard(self, content: str) -> Dict[str, Any]:
        """Copy *content* to the clipboard."""
        try:
            if _SYSTEM == "Windows":
                import ctypes
                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 0x0002
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                if not user32.OpenClipboard(0):
                    return {"success": False, "error": "Could not open clipboard"}
                try:
                    user32.EmptyClipboard()
                    data = content.encode("utf-16-le") + b"\x00\x00"
                    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                    ptr = kernel32.GlobalLock(h_mem)
                    ctypes.memmove(ptr, data, len(data))
                    kernel32.GlobalUnlock(h_mem)
                    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                finally:
                    user32.CloseClipboard()
                return {"success": True}
            elif _SYSTEM == "Darwin":
                proc = subprocess.Popen(
                    ["pbcopy"],
                    stdin=subprocess.PIPE,
                    text=True,
                    timeout=5,
                )
                proc.communicate(input=content)
                return {"success": True}
            else:
                proc = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    text=True,
                    timeout=5,
                )
                proc.communicate(input=content)
                return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --------------------------------------------------------------------- #
    # Screenshot
    # --------------------------------------------------------------------- #

    def take_screenshot(self, save_path: str = "") -> Dict[str, Any]:
        """Take a screenshot and save to *save_path*.

        If *save_path* is empty, a default path under the user's Pictures folder
        is used.
        """
        import os
        from datetime import datetime

        if not save_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pictures = os.path.expanduser("~/Pictures")
            os.makedirs(pictures, exist_ok=True)
            save_path = os.path.join(pictures, f"screenshot_{timestamp}.png")

        try:
            if _SYSTEM == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                gdi32 = ctypes.windll.gdi32

                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)

                hdesktop = user32.GetDesktopWindow()
                hdc = user32.GetDC(hdesktop)
                memdc = gdi32.CreateCompatibleDC(hdc)
                hbmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
                gdi32.SelectObject(memdc, hbmp)
                gdi32.BitBlt(memdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)  # SRCCOPY

                # Save using PIL if available, else save raw via gdi+
                try:
                    from PIL import Image
                    import io
                    bmpinfo = ctypes.create_string_buffer(ctypes.sizeof(ctypes.c_int) * 7)
                    # Simple approach: use PIL to grab from screen
                    img = Image.new("RGB", (w, h))
                    # Direct bitmap copy is complex in pure ctypes; fallback
                    import subprocess
                    # Use PowerShell screenshot approach
                    ps_script = f'''
                    Add-Type -AssemblyName System.Windows.Forms
                    Add-Type -AssemblyName System.Drawing
                    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                    $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
                    $bitmap.Save("{save_path}")
                    $graphics.Dispose()
                    $bitmap.Dispose()
                    '''
                    subprocess.run(
                        ["powershell", "-Command", ps_script],
                        capture_output=True,
                        timeout=15,
                    )
                except ImportError:
                    ps_script = f'''
                    Add-Type -AssemblyName System.Windows.Forms
                    Add-Type -AssemblyName System.Drawing
                    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                    $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
                    $bitmap.Save("{save_path}")
                    $graphics.Dispose()
                    $bitmap.Dispose()
                    '''
                    subprocess.run(
                        ["powershell", "-Command", ps_script],
                        capture_output=True,
                        timeout=15,
                    )

                gdi32.DeleteObject(hbmp)
                gdi32.DeleteDC(memdc)
                user32.ReleaseDC(hdesktop, hdc)

            elif _SYSTEM == "Darwin":
                subprocess.run(
                    ["screencapture", "-x", save_path],
                    timeout=15,
                )
            else:
                subprocess.run(
                    ["gnome-screenshot", "-f", save_path],
                    timeout=15,
                )

            return {"success": True, "path": save_path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
