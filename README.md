# Ecosystem Safeguard

Aplicación de escritorio para la **detección de ganado bovino en imágenes aéreas** mediante inteligencia artificial, con visualización georreferenciada y exportación de resultados.

## Descripción general
Ecosystem Safeguard fue desarrollado para analizar imágenes capturadas por dron y detectar presencia de ganado bovino usando un modelo de visión por computador. La aplicación permite:

- procesar carpetas completas de imágenes,
- identificar automáticamente detecciones,
- visualizar las imágenes anotadas,
- extraer coordenadas GPS desde los metadatos EXIF,
- ubicar los hallazgos en un mapa,
- y exportar resultados visuales, tabulares y geoespaciales.

## Características principales
- Interfaz gráfica de escritorio
- Procesamiento por lotes de imágenes
- Detección de ganado con modelo YOLO
- Extracción de geolocalización desde metadata EXIF
- Vista de inspección individual por imagen
- Vista resumen con mapa interactivo
- Exportación de imágenes y archivos de resultados

## Flujo de uso
1. Abrir la aplicación.
2. Seleccionar una carpeta de entrada con imágenes usando **Browse Folder**.
3. Iniciar el análisis con **Start Processing**.
4. Revisar la vista de inspección con las imágenes detectadas.
5. Consultar el resumen en **View Summary Report**.
6. Exportar los resultados generados.

## Interfaz de la aplicación
La aplicación está organizada en tres vistas principales:

- **StartPage**: selección de carpeta de entrada e inicio del procesamiento.
- **ViewerPage**: visualización de imágenes procesadas, detecciones, ruta del archivo y mapa con geolocalización.
- **SummaryPage**: resumen de la sesión, conteo de imágenes procesadas y visualización global en mapa.

## Arquitectura del proyecto
El sistema se organiza en dos capas principales:

### 1. GUI (`gui_app.py`)
Responsable de:
- interacción con el usuario,
- navegación entre páginas,
- visualización de imágenes,
- renderizado de mapas.

Tecnologías asociadas:
- PyQt6
- QWebEngineView
- Folium

### 2. Detección (`detector_ganado.py`)
Responsable de:
- carga del modelo YOLO,
- inferencia sobre imágenes,
- extracción de coordenadas GPS,
- generación de resultados y archivos de salida.

Tecnologías asociadas:
- Ultralytics
- OpenCV
- Pillow

### 3. Modelo (`models/best.pt`)
Modelo entrenado para la detección de ganado bovino.

## Estructura esperada del proyecto
```text
Ecosystem-Safeguard/
├── gui_app.py
├── detector_ganado.py
├── models/
│   └── best.pt
├── Logos/
├── Installer/
├── output/
├── EcosystemSafeguard.spec
├── CattleDetection.spec
└── epics-ieee.yaml
