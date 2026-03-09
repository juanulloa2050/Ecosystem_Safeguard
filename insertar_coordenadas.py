import shutil
from fractions import Fraction
import piexif

def _to_rational(x, max_den=1000000):
    f = Fraction(x).limit_denominator(max_den)
    return (f.numerator, f.denominator)

def _deg_to_dms_rational(deg):
    deg_abs = abs(deg)
    d = int(deg_abs)
    m_float = (deg_abs - d) * 60
    m = int(m_float)
    s = (m_float - m) * 60
    return (_to_rational(d), _to_rational(m), _to_rational(s))

def write_gps_exif_jpeg(src_path, dst_path, lat, lon, alt_m=None):
    # Copia para no tocar el original
    shutil.copy2(src_path, dst_path)

    try:
        exif_dict = piexif.load(dst_path)
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    gps_ifd = exif_dict.get("GPS", {})

    gps_ifd[piexif.GPSIFD.GPSLatitudeRef]  = ("N" if lat >= 0 else "S").encode()
    gps_ifd[piexif.GPSIFD.GPSLatitude]     = _deg_to_dms_rational(lat)

    gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = ("E" if lon >= 0 else "W").encode()
    gps_ifd[piexif.GPSIFD.GPSLongitude]    = _deg_to_dms_rational(lon)

    if alt_m is not None:
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0  # 0 = sobre el nivel del mar
        gps_ifd[piexif.GPSIFD.GPSAltitude]    = _to_rational(float(alt_m))

    exif_dict["GPS"] = gps_ifd
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, dst_path)

# Ejemplo:
write_gps_exif_jpeg(
    src_path="vaca.jpg",
    dst_path="VACAS_con_gps.jpg",
    lat=4.7110,     # Bogotá aprox
    lon=-74.0721,
    alt_m=2600
)

print("Listo.")
