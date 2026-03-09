import sys
import json
import time
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QPropertyAnimation, QSize
from PyQt6.QtGui import QPixmap, QIcon, QGuiApplication, QPainter, QColor
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QMessageBox, QProgressBar, QFrame, QSizePolicy,
    QListWidget, QListWidgetItem, QSpacerItem
)
# Importamos QWebEngineProfile para configurar el User-Agent
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

import folium
from folium.plugins import MarkerCluster

# Intentar importar el detector, si falla usar dummy para pruebas
try:
    from detector_ganado import procesar_carpeta_imagenes
except ImportError:
    def procesar_carpeta_imagenes(**kwargs):
        time.sleep(1)
        if kwargs.get("progress_cb"):
            kwargs["progress_cb"](1, 1, "Simulacion.jpg", 1)


# --- ESTILOS VISUALES ---
APP_QSS = """
QWidget {
    background: #F8FAFC;
    color: #1E293B;
    font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
    font-size: 13px;
}
QLabel#H1 {
    font-size: 22px;
    font-weight: 800;
    color: #0F172A;
    margin-bottom: 4px;
}
QLabel#Muted {
    color: #64748B;
    font-size: 13px;
}
QLabel#Chip {
    background: #DCFCE7;
    color: #166534;
    border: 1px solid #86EFAC;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 11px;
}
QFrame[role="card"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
}
QLineEdit {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    padding: 10px;
    font-size: 13px;
    selection-background-color: #22C55E;
}
QLineEdit:focus {
    border: 2px solid #22C55E;
}
QPushButton {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 600;
    color: #334155;
}
QPushButton:hover {
    background: #F1F5F9;
    border-color: #94A3B8;
}
QPushButton:pressed {
    background: #E2E8F0;
}
QPushButton#PrimaryButton {
    background: #16A34A;
    color: #FFFFFF;
    border: 1px solid #15803D;
}
QPushButton#PrimaryButton:hover {
    background: #15803D;
}
QPushButton#PrimaryButton:pressed {
    background: #14532D;
}
QPushButton:disabled {
    background: #F1F5F9;
    color: #CBD5E1;
    border-color: #E2E8F0;
}
QProgressBar {
    background: #E2E8F0;
    border-radius: 8px;
    height: 10px;
    text-align: center;
}
QProgressBar::chunk {
    background: #22C55E;
    border-radius: 8px;
}
QWidget#ImageCanvas {
    background: #0F172A;
    border-radius: 12px;
    border: 1px solid #334155;
}
QListWidget {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    outline: none;
}
QListWidget::item {
    padding: 8px;
    margin: 3px;
    border-radius: 8px;
    color: #334155;
}
QListWidget::item:selected {
    background: #DCFCE7;
    color: #14532D;
    border: 1px solid #86EFAC;
}
QFrame#LogoBar {
    background: transparent;
    border-top: 1px solid #E2E8F0;
    margin-top: 8px;
}
"""

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def load_manifest(output_root: Path) -> dict:
    p = output_root / "cattle_detection_manifest.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def fade_in(widget: QWidget, duration_ms: int = 200):
    eff = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.start()
    widget._fade_anim = anim

# --- LOGO BAR ---
def create_logo_bar(parent=None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("LogoBar")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(0, 10, 0, 5)
    layout.setSpacing(20)
    layout.addStretch(1)

    logo_dir = app_dir() / "Logos"
    images = []

    if logo_dir.exists():
        patterns = ["*.png", "*.jpg", "*.jpeg", "*.svg",
                    "*.PNG", "*.JPG", "*.JPEG", "*.SVG"]
        for pat in patterns:
            images.extend(list(logo_dir.glob(pat)))

    images = sorted(list(set(images)))
    images = images[:4]

    for img_path in images:
        lbl = QLabel()
        pix = QPixmap(str(img_path))
        if not pix.isNull():
            pix = pix.scaled(130, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl.setPixmap(pix)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)

    layout.addStretch(1)
    return frame

# --- FUNCIONES DE MAPA ---

def create_message_map_html(output_root: Path, message: str) -> Path:
    """Crea un mapa limpio sin marcadores si no hay GPS"""
    html_path = output_root / "_map_message.html"
    # Centrado general (Colombia aprox), sin Marker
    m = folium.Map(location=[4.0, -73.0], zoom_start=5, tiles="OpenStreetMap", control_scale=True)
    # NO AGREGAMOS MARKER AQUI
    m.save(str(html_path))
    return html_path

def create_single_point_map_html(output_root: Path, lat, lon, title="Location") -> Path:
    html_path = output_root / "_map_current.html"
    if lat is None or lon is None:
        return create_message_map_html(output_root, "No GPS metadata found.")
    
    m = folium.Map(location=[lat, lon], zoom_start=18, tiles="OpenStreetMap", control_scale=True)
    folium.CircleMarker([lat, lon], radius=10, weight=3, color="#16A34A", fill=True).add_to(m)
    folium.Marker([lat, lon], popup=title, tooltip=title).add_to(m)
    m.save(str(html_path))
    return html_path

def create_all_points_map_html(output_root: Path, items: list[dict]) -> Path:
    html_path = output_root / "_map_summary.html"
    valid = [it for it in items if it.get("gps", {}).get("lat") is not None]
    if not valid:
        return create_message_map_html(output_root, "No valid GPS points found.")

    lat0 = valid[0]["gps"]["lat"]
    lon0 = valid[0]["gps"]["lon"]
    m = folium.Map(location=[lat0, lon0], zoom_start=10, tiles="OpenStreetMap", control_scale=True)
    cluster = MarkerCluster().add_to(m)
    for it in valid:
        lat = it["gps"]["lat"]
        lon = it["gps"]["lon"]
        fn = it.get("filename", "img")
        folium.Marker([lat, lon], tooltip=fn).add_to(cluster)
    m.save(str(html_path))
    return html_path

def copy_outputs_for_user(output_root: Path, dest_folder: Path):
    safe_mkdir(dest_folder)
    csv_src = output_root / "cattle_points.csv"
    if csv_src.exists():
        shutil.copy2(str(csv_src), str(dest_folder / csv_src.name))
    for folder_name in ["originales", "boxes"]:
        src = output_root / folder_name
        if src.exists():
            dst = dest_folder / folder_name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

# --- WORKER & HELPERS ---
class ProcessingWorker(QThread):
    done = pyqtSignal(Path)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)

    def __init__(self, input_folder: Path, output_root: Path):
        super().__init__()
        self.input_folder = input_folder
        self.output_root = output_root

    def run(self):
        try:
            def _cb(idx, total, filename, _det=0):
                self.progress.emit(int(idx), int(total), str(filename))

            # INTENTO PASAR PARAMETROS PARA OCULTAR CONFIANZA
            # Nota: Esto depende de que tu 'detector_ganado.py' acepte estos argumentos.
            # Si usa YOLOv8 estandar, 'conf=False' o 'save_conf=False' suele funcionar.
            procesar_carpeta_imagenes(
                ruta_carpeta_imagenes=str(self.input_folder),
                ruta_salida=str(self.output_root),
                confianza=0.75, 
                iou=0.45, 
                img_size=960,
                copiar_originales=True, 
                guardar_boxes=True,
                exportar_manifest=True, 
                exportar_csv=True,
                clean_output=True, 
                progress_cb=_cb,
                # Argumentos extras comunes para no pintar confianza
                hide_conf=True,   
                save_conf=False
            )
            self.done.emit(self.output_root)
        except TypeError:
            # Si falla por argumentos desconocidos, reintentamos sin ellos
            # y el usuario tendrá que editar detector_ganado.py manualmente
            try:
                def _cb(idx, total, filename, _det=0):
                    self.progress.emit(int(idx), int(total), str(filename))
                    
                procesar_carpeta_imagenes(
                    ruta_carpeta_imagenes=str(self.input_folder),
                    ruta_salida=str(self.output_root),
                    confianza=0.75, iou=0.45, img_size=960,
                    copiar_originales=True, guardar_boxes=True,
                    exportar_manifest=True, exportar_csv=True,
                    clean_output=True, progress_cb=_cb
                )
                self.done.emit(self.output_root)
            except Exception as e:
                self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(str(e))

class Card(QFrame):
    def __init__(self):
        super().__init__()
        self.setProperty("role", "card")
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(2)
        self.shadow.setColor(Qt.GlobalColor.lightGray)
        self.setGraphicsEffect(self.shadow)

class ImageCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        # Evita que el layout crezca infinitamente por la imagen
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setObjectName("ImageCanvas")

    def set_pixmap(self, pixmap: QPixmap):
        self.pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.pixmap:
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Image Loaded")
            return

        scaled_pix = self.pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        x = (self.width() - scaled_pix.width()) // 2
        y = (self.height() - scaled_pix.height()) // 2
        painter.drawPixmap(x, y, scaled_pix)

# --- PÁGINAS ---
class StartPage(QWidget):
    start_processing = pyqtSignal(Path)

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(15)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        title = QLabel("Cattle Detection App")
        title.setObjectName("H1")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Process drone imagery, detect cattle with AI, and visualize GPS distribution.")
        subtitle.setObjectName("Muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addLayout(header_layout)

        root.addStretch(1)

        card = Card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(25, 25, 25, 25)
        lay.setSpacing(15)

        lbl_instruct = QLabel("Select Input Source")
        lbl_instruct.setStyleSheet("font-weight: bold; font-size: 15px;")
        lay.addWidget(lbl_instruct)

        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select folder containing images...")
        self.path_edit.setMinimumHeight(40)

        btn_browse = QPushButton("Browse Folder")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setMinimumHeight(40)
        btn_browse.clicked.connect(self.browse_folder)

        row.addWidget(self.path_edit, 1)
        row.addWidget(btn_browse)
        lay.addLayout(row)

        self.btn_process = QPushButton("Start Processing")
        self.btn_process.setObjectName("PrimaryButton")
        self.btn_process.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_process.setMinimumHeight(45)
        self.btn_process.clicked.connect(self.on_process)
        lay.addWidget(self.btn_process)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(10)
        lay.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setObjectName("Muted")
        lay.addWidget(self.status)

        card_container = QHBoxLayout()
        card_container.addStretch(1)
        card_container.addWidget(card, 2)
        card_container.addStretch(1)

        root.addLayout(card_container)
        root.addStretch(1)

        root.addWidget(create_logo_bar(self))

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.path_edit.setText(folder)

    def on_process(self):
        p = self.path_edit.text().strip()
        if not p:
            QMessageBox.warning(self, "Warning", "Please select a folder.")
            return
        self.start_processing.emit(Path(p))

    def set_processing(self, running: bool):
        self.btn_process.setEnabled(not running)
        self.progress.setVisible(running)
        if running:
            self.status.setText("Initializing AI Models...")

    def set_progress(self, idx, total, filename):
        self.progress.setRange(0, total)
        self.progress.setValue(idx)
        self.status.setText(f"Processing {idx}/{total}: {filename}")

class ViewerPage(QWidget):
    go_to_summary = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.output_root = None
        self.items = []
        self.filtered = []

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # Top Bar
        top = QHBoxLayout()
        title = QLabel("Inspection View")
        title.setObjectName("H1")
        top.addWidget(title)
        top.addStretch()

        self.btn_summary = QPushButton("View Summary Report ▶")
        self.btn_summary.setObjectName("PrimaryButton")
        self.btn_summary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_summary.clicked.connect(self.go_to_summary.emit)
        top.addWidget(self.btn_summary)
        root.addLayout(top)

        # Main Content Layout
        content = QHBoxLayout()

        # 1. Left Sidebar
        side_layout = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter files...")
        self.search.textChanged.connect(self.apply_filter)
        side_layout.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(240) # Sidebar un poco mas angosta
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        side_layout.addWidget(self.list_widget)
        content.addLayout(side_layout)

        # 2. Center Image (Weight 2)
        img_card = Card()
        icl = QVBoxLayout(img_card)
        icl.setContentsMargins(0, 0, 0, 0)

        self.img_canvas = ImageCanvas()
        icl.addWidget(self.img_canvas)
        content.addWidget(img_card, 2)

        # 3. Right Info + Map (Weight 1)
        right_layout = QVBoxLayout()

        info_card = Card()
        il = QVBoxLayout(info_card)
        self.lbl_chip = QLabel("STATUS")
        self.lbl_chip.setObjectName("Chip")
        il.addWidget(self.lbl_chip, 0, Qt.AlignmentFlag.AlignLeft)
        self.lbl_info = QLabel("--")
        self.lbl_info.setWordWrap(True)
        il.addWidget(self.lbl_info)
        right_layout.addWidget(info_card)

        # Map Card
        map_card = Card()
        # FIX: Desactivar sombra solo en el mapa para evitar bugs visuales del WebEngine
        map_card.setGraphicsEffect(None)  
        ml = QVBoxLayout(map_card)
        ml.setContentsMargins(0, 0, 0, 0)

        self.map_view = QWebEngineView()
        self.map_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.map_view.setMinimumSize(250, 250)

        s = self.map_view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        ml.addWidget(self.map_view)
        right_layout.addWidget(map_card, 1)

        content.addLayout(right_layout, 1)
        root.addLayout(content, 1)

        # Navigation Bar
        nav = QHBoxLayout()
        nav.addStretch(1)
        self.btn_prev = QPushButton("◀ Previous")
        self.btn_prev.clicked.connect(self.prev_item)
        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self.next_item)
        self.lbl_count = QLabel("0 / 0")
        self.lbl_count.setStyleSheet("font-weight:bold; color: #64748B; margin: 0 15px;")

        nav.addWidget(self.btn_prev)
        nav.addWidget(self.lbl_count)
        nav.addWidget(self.btn_next)
        nav.addStretch(1)
        root.addLayout(nav)

        root.addWidget(create_logo_bar(self))

    def load_results(self, output_root: Path):
        self.output_root = output_root
        manifest = load_manifest(output_root)
        self.items = manifest.get("images", [])
        self.filtered = list(range(len(self.items)))

        self.populate_list()
        if self.items:
            self.list_widget.setCurrentRow(0)
        else:
            self.img_canvas.set_pixmap(None)

    def populate_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for idx in self.filtered:
            it = self.items[idx]
            name = it.get("filename", "Unknown")
            det = it.get("detections", 0)
            item = QListWidgetItem(f"{name} ({det})")
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

    def apply_filter(self, txt):
        txt = txt.lower()
        if not txt:
            self.filtered = list(range(len(self.items)))
        else:
            self.filtered = [i for i, it in enumerate(self.items) if txt in it.get("filename", "").lower()]
        self.populate_list()
        if self.filtered:
            self.list_widget.setCurrentRow(0)

    def on_row_changed(self, row):
        if row < 0 or row >= len(self.filtered):
            return
        real_idx = self.filtered[row]
        self.show_item(real_idx, row)

    def show_item(self, idx, row):
        data = self.items[idx]

        b_rel = data.get("boxed_rel")
        if b_rel and self.output_root:
            p = self.output_root / b_rel
            if p.exists():
                pix = QPixmap(str(p))
                self.img_canvas.set_pixmap(pix)
            else:
                self.img_canvas.set_pixmap(None)
        else:
            self.img_canvas.set_pixmap(None)

        gps = data.get("gps", {})
        self.lbl_info.setText(
            f"<b>File:</b> {data.get('filename')}<br>"
            f"<b>Detections:</b> {data.get('detections')}<br><br>"
            f"Lat: {gps.get('lat', 'N/A')}<br>"
            f"Lon: {gps.get('lon', 'N/A')}"
        )
        self.lbl_chip.setText(f"DETECTED: {data.get('detections')}")

        lat, lon = gps.get("lat"), gps.get("lon")
        mp = create_single_point_map_html(self.output_root, lat, lon, data.get("filename"))

        # Cargar HTML con URL base para asegurar assets
        html = mp.read_text(encoding="utf-8")
        base = QUrl.fromLocalFile(str(mp.parent.resolve()) + "/")
        self.map_view.setHtml(html, baseUrl=base)

        self.lbl_count.setText(f"{row + 1} / {len(self.filtered)}")

    def prev_item(self):
        r = self.list_widget.currentRow()
        if r > 0:
            self.list_widget.setCurrentRow(r - 1)

    def next_item(self):
        r = self.list_widget.currentRow()
        if r < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(r + 1)

class SummaryPage(QWidget):
    back_to_start = pyqtSignal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(15)

        title = QLabel("Session Summary")
        title.setObjectName("H1")
        root.addWidget(title)

        self.stat_card = Card()
        sl = QHBoxLayout(self.stat_card)
        self.lbl_total = QLabel("Processed: 0")
        self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.lbl_found = QLabel("With Cattle: 0")
        self.lbl_found.setStyleSheet("font-size: 18px; font-weight: bold; color: #16A34A;")
        sl.addWidget(self.lbl_total)
        sl.addSpacing(20)
        sl.addWidget(self.lbl_found)
        sl.addStretch()
        root.addWidget(self.stat_card)

        map_c = Card()
        map_c.setGraphicsEffect(None) # FIX
        ml = QVBoxLayout(map_c)
        ml.setContentsMargins(0, 0, 0, 0)

        self.map_view = QWebEngineView()
        self.map_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        s = self.map_view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        ml.addWidget(self.map_view)
        root.addWidget(map_c, 1)

        btns = QHBoxLayout()
        self.btn_export = QPushButton("Export Data to Folder...")
        self.btn_export.setObjectName("PrimaryButton")
        self.btn_export.setMinimumHeight(45)
        self.btn_export.clicked.connect(self.export_data)

        self.btn_home = QPushButton("Back to Home")
        self.btn_home.setMinimumHeight(45)
        self.btn_home.clicked.connect(self.back_to_start.emit)

        btns.addWidget(self.btn_export)
        btns.addStretch()
        btns.addWidget(self.btn_home)
        root.addLayout(btns)

        root.addWidget(create_logo_bar(self))

    def load(self, output_root: Path):
        self.output_root = output_root
        man = load_manifest(output_root)
        self.lbl_total.setText(f"Processed: {man.get('count_images_processed', 0)}")
        self.lbl_found.setText(f"With Cattle: {man.get('count_images_with_cattle', 0)}")

        mp = create_all_points_map_html(output_root, man.get("images", []))

        html = mp.read_text(encoding="utf-8")
        base = QUrl.fromLocalFile(str(mp.parent.resolve()) + "/")
        self.map_view.setHtml(html, baseUrl=base)

    def export_data(self):
        if not self.output_root:
            return
        dest = QFileDialog.getExistingDirectory(self, "Export Destination")
        if dest:
            try:
                t = time.strftime("%Y%m%d_%H%M%S")
                target = Path(dest) / f"Export_{t}"
                copy_outputs_for_user(self.output_root, target)
                QMessageBox.information(self, "Success", f"Data exported to:\n{target}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cattle Detection Dashboard")
        self.resize(1000, 680) # <--- TAMANO REDUCIDO
        self.center_window()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.page_start = StartPage()
        self.page_view = ViewerPage()
        self.page_sum = SummaryPage()

        self.stack.addWidget(self.page_start)
        self.stack.addWidget(self.page_view)
        self.stack.addWidget(self.page_sum)

        self.page_start.start_processing.connect(self.run_process)
        self.page_view.go_to_summary.connect(lambda: self.switch_page(2))
        self.page_sum.back_to_start.connect(lambda: self.switch_page(0))

    def center_window(self):
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def run_process(self, folder):
        self.output_dir = app_dir() / "output"
        safe_mkdir(self.output_dir)

        self.page_start.set_processing(True)
        self.worker = ProcessingWorker(folder, self.output_dir)
        self.worker.progress.connect(self.page_start.set_progress)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_fail)
        self.worker.start()

    def on_done(self, out_path):
        self.page_start.set_processing(False)
        self.page_view.load_results(out_path)
        self.page_sum.load(out_path)
        self.switch_page(1)

    def on_fail(self, msg):
        self.page_start.set_processing(False)
        QMessageBox.critical(self, "Error", msg)

    def switch_page(self, idx):
        self.stack.setCurrentIndex(idx)

def main():
    app = QApplication(sys.argv)
    
    # --- CONFIGURACIÓN CRÍTICA PARA EL MAPA ---
    # Esto engaña al servidor de mapas para que permita la descarga de imágenes
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36")
    # ------------------------------------------

    app.setStyleSheet(APP_QSS)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()