import os
from pathlib import Path


os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")


def _app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "EcosystemSafeguard"
    return Path.home() / "AppData" / "Local" / "EcosystemSafeguard"


root = _app_data_dir()
for env_name, folder_name in (
    ("YOLO_CONFIG_DIR", "ultralytics"),
    ("MPLCONFIGDIR", "matplotlib"),
    ("NUMBA_CACHE_DIR", "numba"),
):
    path = root / folder_name
    path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(env_name, str(path))
