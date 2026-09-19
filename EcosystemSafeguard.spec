# -*- mode: python ; coding: utf-8 -*-
import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


datas = [
    ("models\\best.pt", "models"),
    ("assets", "assets"),
]
binaries = collect_dynamic_libs("rawpy")

# torchvision >= 0.29 renombro sus extensiones nativas (_C -> _C_stable,
# image -> image_stable) y las carga por ruta con torch.ops.load_library. El
# hook de PyInstaller aun busca "torchvision._C", asi que no las empaqueta y el
# .exe falla con "operator torchvision::nms does not exist". Se copian a mano.
_tv_dir = Path(importlib.util.find_spec("torchvision").origin).parent
for _f in list(_tv_dir.glob("*.pyd")) + list(_tv_dir.glob("*.dll")):
    binaries.append((str(_f), "torchvision"))
hiddenimports = [
    "rawpy",
    "rawpy._rawpy",
    "ultralytics.nn.tasks",
    "ultralytics.models.yolo.detect.predict",
    "ultralytics.utils.ops",
]

for package in ("ultralytics", "folium", "branca", "jinja2"):
    datas += collect_data_files(package)


a = Analysis(
    ["gui_app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["runtime_hook_cpu.py"],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EcosystemSafeguard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets\\app.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EcosystemSafeguard",
)
