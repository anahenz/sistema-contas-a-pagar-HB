import sys
from pathlib import Path


def set_windows_startup(enabled):
    if sys.platform != "win32":
        raise ValueError("O início automático está disponível no Windows.")
    import winreg

    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}" --tray'
    else:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        executable = pythonw if pythonw.exists() else Path(sys.executable)
        main = Path(__file__).resolve().parents[2] / "main.py"
        command = f'"{executable}" "{main}" --tray'
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, "ContasPagar", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "ContasPagar")
            except FileNotFoundError:
                pass
