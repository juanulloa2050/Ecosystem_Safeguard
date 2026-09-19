from __future__ import annotations

import time
import json
import csv
import shutil
import os
import sys
from pathlib import Path
from typing import Dict, Optional, List, Callable, Any

# Force CPU execution before Ultralytics imports torch.  This matters in the
# packaged app because the build environment has a CUDA-enabled torch install.
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")

import cv2
from ultralytics import YOLO

from PIL import Image
from PIL.ExifTags import GPSTAGS

# Formatos RAW (los DJI guardan DNG). OpenCV/Ultralytics no los leen, hay que
# revelarlos con rawpy (LibRaw).
RAW_EXT = {".dng"}


def _load_raw_bgr(image_path: Path):
    """Revela un RAW a un array BGR de 8 bits (formato que espera Ultralytics).

    half_size=True: 8192x4608 -> 4096x2304. Es 4x mas rapido y no pierde nada
    util, porque el modelo redimensiona la entrada a img_size de todos modos.
    """
    import rawpy  # import perezoso: solo hace falta si hay RAW en la carpeta

    with rawpy.imread(str(image_path)) as raw:
        rgb = raw.postprocess(use_camera_wb=True, half_size=True,
                              no_auto_bright=False, output_bps=8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


BASE_DIR = _runtime_base_dir()


def resolve_model_path(ruta_modelo: Optional[str] = None) -> Path:
    candidates: List[Path] = []
    if ruta_modelo:
        candidates.append(Path(ruta_modelo).expanduser().resolve())

    candidates += [
        (BASE_DIR / "models" / "best.pt").resolve(),
        (BASE_DIR / "best.pt").resolve(),
    ]

    for p in candidates:
        if p.exists():
            return p

    raise FileNotFoundError(
        "Model file not found. Place best.pt in 'models/best.pt' or pass ruta_modelo."
    )


def _rational_to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        pass
    if isinstance(x, tuple) and len(x) == 2:
        num, den = x
        den = float(den)
        return float(num) / den if den != 0 else None
    if hasattr(x, "numerator") and hasattr(x, "denominator"):
        den = float(x.denominator)
        return float(x.numerator) / den if den != 0 else None
    return None

def _dms_to_deg(dms: Any) -> Optional[float]:
    if not dms or len(dms) != 3:
        return None
    d = _rational_to_float(dms[0])
    m = _rational_to_float(dms[1])
    s = _rational_to_float(dms[2])
    if d is None or m is None or s is None:
        return None
    return d + (m / 60.0) + (s / 3600.0)

def _as_ref_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bytes):
        v = v.decode(errors="ignore")
    return str(v).strip().upper()

def _as_int(v: Any, default=0) -> int:
    if v is None:
        return default
    if isinstance(v, (bytes, bytearray)):
        return int(v[0]) if len(v) else default
    try:
        return int(v)
    except Exception:
        return default

def extract_gps_from_image(image_path: Path) -> Dict:
    """
    Returns:
      {"lat": float|None, "lon": float|None, "alt_m": float|None, "datetime": str|None}
    """
    out = {"lat": None, "lon": None, "alt_m": None, "datetime": None}

    try:
        img = Image.open(str(image_path))
        exif = img.getexif()
        if not exif:
            return out

        # DateTimeOriginal
        dt = exif.get(36867, None)
        if dt:
            out["datetime"] = str(dt)

        # GPSInfo
        try:
            gps_info = exif.get_ifd(34853)
        except Exception:
            gps_info = None

        if not gps_info:
            return out

        gps = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}

        lat = gps.get("GPSLatitude")
        lat_ref = _as_ref_str(gps.get("GPSLatitudeRef"))
        lon = gps.get("GPSLongitude")
        lon_ref = _as_ref_str(gps.get("GPSLongitudeRef"))

        if lat and lon and lat_ref and lon_ref:
            lat_deg = _dms_to_deg(lat)
            lon_deg = _dms_to_deg(lon)
            if lat_deg is not None and lon_deg is not None:
                if lat_ref == "S":
                    lat_deg = -lat_deg
                if lon_ref == "W":
                    lon_deg = -lon_deg
                out["lat"] = lat_deg
                out["lon"] = lon_deg

        alt = gps.get("GPSAltitude")
        alt_ref = _as_int(gps.get("GPSAltitudeRef", 0), default=0)
        alt_m = _rational_to_float(alt) if alt is not None else None
        if alt_m is not None:
            if alt_ref == 1:
                alt_m = -alt_m
            out["alt_m"] = alt_m

        return out

    except Exception as e:
        print("GPS error en", image_path, "->", repr(e))
        return out


# ==========================
# Main function
# ==========================
def procesar_carpeta_imagenes(
    ruta_carpeta_imagenes: str,
    ruta_salida: str,
    ruta_modelo: Optional[str] = None,
    confianza: float = 0.5,
    iou: float = 0.45,
    img_size: int = 960,
    copiar_originales: bool = True,
    guardar_boxes: bool = True,
    exportar_manifest: bool = True,
    exportar_geojson: bool = True,
    exportar_csv: bool = True,
    recursive: bool = False,
    verbose: bool = False,
    incluir_sin_detecciones: bool = False,
    clean_output: bool = True,
    progress_cb: Optional[Callable[[int, int, str, int], None]] = None,
    **kwargs  # <--- IMPORTANTE: Acepta argumentos extra del main sin crashear
) -> Dict:
    """
    Outputs:
      output/
        originales/
        boxes/
        cattle_detection_manifest.json
        cattle_points.geojson
        cattle_points.csv
    """

    input_dir = Path(ruta_carpeta_imagenes).expanduser().resolve()
    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder not found: {input_dir}")

    model_pt = resolve_model_path(ruta_modelo)

    out_root = Path(ruta_salida).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    out_originales = out_root / "originales"
    out_boxes = out_root / "boxes"

    if clean_output:
        if out_originales.exists():
            shutil.rmtree(out_originales, ignore_errors=True)
        if out_boxes.exists():
            shutil.rmtree(out_boxes, ignore_errors=True)

    out_originales.mkdir(parents=True, exist_ok=True)
    out_boxes.mkdir(parents=True, exist_ok=True)

    valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"} | RAW_EXT
    if recursive:
        images = [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in valid_ext]
    else:
        images = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in valid_ext]
    images.sort(key=lambda p: p.name.lower())

    total = len(images)
    if total == 0:
        if exportar_manifest:
            (out_root / "cattle_detection_manifest.json").write_text(
                json.dumps({
                    "schema_version": "1.0",
                    "created_at_unix": int(time.time()),
                    "count_images_processed": 0,
                    "count_images_with_cattle": 0,
                    "images": []
                }, indent=2),
                encoding="utf-8"
            )
        if exportar_geojson:
            (out_root / "cattle_points.geojson").write_text(
                json.dumps({"type": "FeatureCollection", "features": []}, indent=2),
                encoding="utf-8"
            )
        if exportar_csv:
            with open(out_root / "cattle_points.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["filename", "lat", "lon", "alt_m", "datetime", "detections", "boxed_rel", "original_rel"])
                w.writeheader()
        return {}

    model = YOLO(str(model_pt))
    try:
        model.to("cpu")
    except Exception:
        pass

    manifest_items: List[Dict] = []
    geo_features: List[Dict] = []
    csv_rows: List[Dict] = []
    resultados: Dict = {}

    with_cattle = 0

    for idx, img_path in enumerate(images, 1):
        filename = img_path.name
        is_raw = img_path.suffix.lower() in RAW_EXT
        # Las imagenes derivadas de un RAW se guardan como JPG para poder verlas.
        view_name = img_path.stem + ".jpg" if is_raw else filename

        try:
            source = _load_raw_bgr(img_path) if is_raw else str(img_path)
        except Exception as e:
            print("No se pudo leer", img_path, "->", repr(e))
            if progress_cb:
                progress_cb(idx, total, filename, 0)
            continue

        preds = model.predict(
            source=source,
            conf=confianza,
            iou=iou,
            imgsz=img_size,
            device="cpu",
            verbose=False
        )
        r = preds[0]
        num_det = 0 if r.boxes is None else len(r.boxes)

        if progress_cb:
            progress_cb(idx, total, filename, int(num_det))

        if num_det <= 0 and not incluir_sin_detecciones:
            continue

        if num_det > 0:
            with_cattle += 1

        original_rel = None
        boxed_rel = None

        if copiar_originales:
            dst = out_originales / filename
            shutil.copy2(str(img_path), str(dst))
            original_rel = str(Path("originales") / filename).replace("\\", "/")

        if guardar_boxes:
            dst = out_boxes / view_name
            # El modelo tiene una sola clase, asi que la etiqueta no aporta y
            # en rebanos densos tapa por completo la imagen: solo cajas.
            img_annot = r.plot(conf=False, labels=False)
            cv2.imwrite(str(dst), img_annot)
            boxed_rel = str(Path("boxes") / view_name).replace("\\", "/")

        gps = extract_gps_from_image(img_path)

        item = {
            "filename": filename,
            "source_path": str(img_path),
            "original_rel": original_rel,
            "boxed_rel": boxed_rel,
            "gps": {"lat": gps["lat"], "lon": gps["lon"], "alt_m": gps["alt_m"]},
            "datetime": gps["datetime"],
            "detections": int(num_det),
        }
        manifest_items.append(item)

        if gps["lat"] is not None and gps["lon"] is not None:
            geo_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [gps["lon"], gps["lat"]],
                },
                "properties": {
                    "filename": filename,
                    "boxed_rel": boxed_rel,
                    "original_rel": original_rel,
                    "detections": int(num_det),
                    "datetime": gps["datetime"],
                    "alt_m": gps["alt_m"],
                }
            })

        csv_rows.append({
            "filename": filename,
            "lat": "" if gps["lat"] is None else gps["lat"],
            "lon": "" if gps["lon"] is None else gps["lon"],
            "alt_m": "" if gps["alt_m"] is None else gps["alt_m"],
            "datetime": "" if gps["datetime"] is None else gps["datetime"],
            "detections": int(num_det),
            "boxed_rel": "" if boxed_rel is None else boxed_rel,
            "original_rel": "" if original_rel is None else original_rel,
        })

        resultados[filename] = {"detections": int(num_det), "gps": gps}

    manifest_path = out_root / "cattle_detection_manifest.json"
    geojson_path = out_root / "cattle_points.geojson"
    csv_path = out_root / "cattle_points.csv"

    if exportar_manifest:
        payload = {
            "schema_version": "1.0",
            "created_at_unix": int(time.time()),
            "count_images_processed": total,
            "count_images_with_cattle": with_cattle,
            "images": manifest_items,
        }
        manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if exportar_geojson:
        geo = {"type": "FeatureCollection", "features": geo_features}
        geojson_path.write_text(json.dumps(geo, indent=2, ensure_ascii=False), encoding="utf-8")

    if exportar_csv:
        fieldnames = ["filename", "lat", "lon", "alt_m", "datetime", "detections", "boxed_rel", "original_rel"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in csv_rows:
                w.writerow(row)

    return resultados

