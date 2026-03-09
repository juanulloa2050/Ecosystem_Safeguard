"""
🐄 Detector de Ganado - Sistema Completo
Función 1: Procesar Videos | Función 2: Procesar Carpetas de Imágenes
Confianza profesional: 0.75

Este script contiene dos funciones principales para procesamiento profesional
de videos e imágenes con YOLO para detección de ganado.
"""

# ============================================================================
# 📦 IMPORTACIONES
# ============================================================================

from ultralytics import YOLO
import cv2
import os
from pathlib import Path
import time
import shutil
from typing import List, Tuple, Dict
import json

print("✅ Módulos importados correctamente")


# ============================================================================
# 🎬 FUNCIÓN 1: PROCESAR VIDEO CON YOLO
# ============================================================================

def procesar_video_yolo(
    ruta_modelo: str,
    ruta_video: str,
    ruta_salida: str = None,
    confianza: float = 0.85,
    iou: float = 0.45,
    img_size: int = 960,
    guardar_video: bool = True
) -> Dict:
    """
    Procesa un video con YOLO y devuelve estadísticas de detección.
    
    Parámetros:
    -----------
    ruta_modelo : str
        Ruta al archivo .pt del modelo YOLO entrenado
    ruta_video : str
        Ruta al video a procesar
    ruta_salida : str, opcional
        Ruta donde guardar el video procesado (None = carpeta runs/detect/)
    confianza : float, default=0.75
        Confianza mínima para detección (recomendado 0.75 para uso profesional)
    iou : float, default=0.45
        Umbral de IoU para NMS
    img_size : int, default=960
        Tamaño de imagen para inferencia
    guardar_video : bool, default=True
        Si se debe guardar el video con detecciones
        
    Retorna:
    --------
    dict : Diccionario con estadísticas del procesamiento
    """
    
    print("\n" + "="*80)
    print("🎥 FUNCIÓN 1: PROCESAMIENTO DE VIDEO CON YOLO")
    print("="*80)
    
    # Validar archivos
    if not os.path.exists(ruta_modelo):
        raise FileNotFoundError(f"❌ Modelo no encontrado: {ruta_modelo}")
    if not os.path.exists(ruta_video):
        raise FileNotFoundError(f"❌ Video no encontrado: {ruta_video}")
    
    print(f"✅ Modelo: {os.path.basename(ruta_modelo)}")
    print(f"✅ Video: {os.path.basename(ruta_video)}")
    
    # Obtener info del video
    cap = cv2.VideoCapture(ruta_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    
    print(f"\n📹 Información del video:")
    print(f"   - Resolución: {width}x{height}")
    print(f"   - FPS: {fps}")
    print(f"   - Frames: {frame_count}")
    print(f"   - Duración: {duration:.2f}s ({duration/60:.2f} min)")
    
    # Cargar modelo
    print(f"\n🤖 Cargando modelo YOLO...")
    model = YOLO(ruta_modelo)
    print(f"✅ Modelo cargado - Clases: {model.names}")
    
    # Configurar salida
    if ruta_salida is None:
        project_dir = "runs/detect"
        name_dir = f"video_{Path(ruta_video).stem}"
    else:
        project_dir = os.path.dirname(ruta_salida)
        name_dir = Path(ruta_salida).stem
    
    print(f"\n⚙️  Parámetros:")
    print(f"   - Confianza: {confianza}")
    print(f"   - IoU: {iou}")
    print(f"   - Tamaño inferencia: {img_size}px")
    print("="*80 + "\n")
    
    # Procesar video
    start_time = time.time()
    frame_number = 0
    detection_count = 0
    frames_with_detections = 0
    detecciones_por_frame = []
    
    results_generator = model.predict(
        source=ruta_video,
        conf=confianza,
        iou=iou,
        imgsz=img_size,
        stream=True,
        save=guardar_video,
        project=project_dir,
        name=name_dir,
        exist_ok=True,
        show_labels=True,
        show_conf=True,
        line_width=2,
        verbose=False
    )
    
    print("🔄 Procesando video...\n")
    
    for result in results_generator:
        frame_number += 1
        num_detections = len(result.boxes)
        detection_count += num_detections
        
        if num_detections > 0:
            frames_with_detections += 1
        
        detecciones_por_frame.append(num_detections)
        
        if frame_number % 30 == 0:
            elapsed = time.time() - start_time
            fps_processing = frame_number / elapsed
            print(f"Frame {frame_number:5d}/{frame_count} | "
                  f"Detecciones: {num_detections:3d} | "
                  f"FPS: {fps_processing:.1f} | "
                  f"Tiempo: {elapsed:.1f}s")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Estadísticas
    estadisticas = {
        'frames_procesados': frame_number,
        'frames_con_detecciones': frames_with_detections,
        'porcentaje_frames_con_detecciones': (frames_with_detections/frame_number*100) if frame_number > 0 else 0,
        'total_detecciones': detection_count,
        'promedio_detecciones_por_frame': detection_count/frame_number if frame_number > 0 else 0,
        'tiempo_procesamiento_segundos': total_time,
        'tiempo_procesamiento_minutos': total_time/60,
        'fps_procesamiento': frame_number/total_time if total_time > 0 else 0,
        'ruta_salida': os.path.join(project_dir, name_dir) if guardar_video else None
    }
    
    print("\n" + "="*80)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("="*80)
    print(f"📊 Estadísticas:")
    print(f"   - Frames procesados: {estadisticas['frames_procesados']}")
    print(f"   - Frames con detecciones: {estadisticas['frames_con_detecciones']} "
          f"({estadisticas['porcentaje_frames_con_detecciones']:.1f}%)")
    print(f"   - Total detecciones: {estadisticas['total_detecciones']}")
    print(f"   - Promedio detecciones/frame: {estadisticas['promedio_detecciones_por_frame']:.2f}")
    print(f"   - Tiempo total: {estadisticas['tiempo_procesamiento_segundos']:.2f}s "
          f"({estadisticas['tiempo_procesamiento_minutos']:.2f} min)")
    print(f"   - FPS procesamiento: {estadisticas['fps_procesamiento']:.2f}")
    
    if guardar_video:
        print(f"\n💾 Video guardado en: {estadisticas['ruta_salida']}")
    
    print("="*80)
    
    return estadisticas


# ============================================================================
# 📸 FUNCIÓN 2: PROCESAR CARPETA DE IMÁGENES
# ============================================================================

def procesar_carpeta_imagenes(
    ruta_modelo: str,
    ruta_carpeta_imagenes: str,
    ruta_salida: str,
    confianza: float = 0.75,
    iou: float = 0.45,
    img_size: int = 960,
    copiar_imagenes: bool = True,
    guardar_coordenadas: bool = True
) -> Dict:
    """
    Procesa una carpeta de imágenes y devuelve solo aquellas con ganado detectado.
    
    Parámetros:
    -----------
    ruta_modelo : str
        Ruta al archivo .pt del modelo YOLO entrenado
    ruta_carpeta_imagenes : str
        Ruta a la carpeta con imágenes a procesar
    ruta_salida : str
        Ruta donde guardar las imágenes con detecciones
    confianza : float, default=0.75
        Confianza mínima para detección
    iou : float, default=0.45
        Umbral de IoU para NMS
    img_size : int, default=960
        Tamaño de imagen para inferencia
    copiar_imagenes : bool, default=True
        Si se deben copiar las imágenes originales con detecciones
    guardar_coordenadas : bool, default=True
        Si se debe guardar un archivo JSON con las coordenadas
        
    Retorna:
    --------
    dict : Diccionario con resultados por imagen
    """
    
    print("\n" + "="*80)
    print("📸 FUNCIÓN 2: PROCESAMIENTO DE CARPETA DE IMÁGENES")
    print("="*80)
    
    # Validar archivos
    if not os.path.exists(ruta_modelo):
        raise FileNotFoundError(f"❌ Modelo no encontrado: {ruta_modelo}")
    if not os.path.exists(ruta_carpeta_imagenes):
        raise FileNotFoundError(f"❌ Carpeta no encontrada: {ruta_carpeta_imagenes}")
    
    print(f"✅ Modelo: {os.path.basename(ruta_modelo)}")
    print(f"✅ Carpeta: {ruta_carpeta_imagenes}")
    
    # Crear carpeta de salida
    os.makedirs(ruta_salida, exist_ok=True)
    print(f"✅ Carpeta salida: {ruta_salida}")
    
    # Obtener lista de imágenes
    extensiones_validas = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    imagenes = []
    
    for archivo in os.listdir(ruta_carpeta_imagenes):
        if Path(archivo).suffix.lower() in extensiones_validas:
            imagenes.append(os.path.join(ruta_carpeta_imagenes, archivo))
    
    if len(imagenes) == 0:
        print("❌ No se encontraron imágenes en la carpeta")
        return {}
    
    print(f"📊 Imágenes encontradas: {len(imagenes)}")
    
    # Cargar modelo
    print(f"\n🤖 Cargando modelo YOLO...")
    model = YOLO(ruta_modelo)
    print(f"✅ Modelo cargado - Clases: {model.names}")
    
    print(f"\n⚙️  Parámetros:")
    print(f"   - Confianza: {confianza}")
    print(f"   - IoU: {iou}")
    print(f"   - Tamaño inferencia: {img_size}px")
    print("="*80 + "\n")
    
    # Procesar imágenes
    start_time = time.time()
    resultados = {}
    imagenes_con_detecciones = 0
    total_detecciones = 0
    
    print("🔄 Procesando imágenes...\n")
    
    for idx, ruta_imagen in enumerate(imagenes, 1):
        nombre_imagen = os.path.basename(ruta_imagen)
        
        # Procesar imagen
        results = model.predict(
            source=ruta_imagen,
            conf=confianza,
            iou=iou,
            imgsz=img_size,
            verbose=False
        )
        
        result = results[0]
        num_detecciones = len(result.boxes)
        
        # Si hay detecciones, guardar información
        if num_detecciones > 0:
            imagenes_con_detecciones += 1
            total_detecciones += num_detecciones
            
            # Extraer coordenadas y detalles
            detecciones = []
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                clase_nombre = model.names[cls]
                
                detecciones.append({
                    'clase': clase_nombre,
                    'confianza': round(conf, 3),
                    'coordenadas': {
                        'x1': int(x1),
                        'y1': int(y1),
                        'x2': int(x2),
                        'y2': int(y2)
                    },
                    'centro': {
                        'x': int((x1 + x2) / 2),
                        'y': int((y1 + y2) / 2)
                    },
                    'ancho': int(x2 - x1),
                    'alto': int(y2 - y1)
                })
            
            resultados[nombre_imagen] = {
                'num_detecciones': num_detecciones,
                'detecciones': detecciones,
                'ruta_original': ruta_imagen
            }
            
            # Copiar imagen si se solicita
            if copiar_imagenes:
                ruta_destino = os.path.join(ruta_salida, nombre_imagen)
                shutil.copy2(ruta_imagen, ruta_destino)
            
            print(f"[{idx:4d}/{len(imagenes)}] ✅ {nombre_imagen}: {num_detecciones} detección(es)")
        else:
            if idx % 10 == 0:
                print(f"[{idx:4d}/{len(imagenes)}] ⚪ Sin detecciones...")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Guardar coordenadas en JSON
    if guardar_coordenadas and len(resultados) > 0:
        json_path = os.path.join(ruta_salida, 'detecciones_coordenadas.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Coordenadas guardadas en: {json_path}")
    
    # Resumen
    print("\n" + "="*80)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("="*80)
    print(f"📊 Estadísticas:")
    print(f"   - Imágenes procesadas: {len(imagenes)}")
    print(f"   - Imágenes con ganado: {imagenes_con_detecciones} "
          f"({imagenes_con_detecciones/len(imagenes)*100:.1f}%)")
    print(f"   - Imágenes sin ganado: {len(imagenes) - imagenes_con_detecciones}")
    print(f"   - Total detecciones: {total_detecciones}")
    print(f"   - Promedio detecciones/imagen (con ganado): "
          f"{total_detecciones/imagenes_con_detecciones:.2f}" if imagenes_con_detecciones > 0 else "N/A")
    print(f"   - Tiempo total: {total_time:.2f}s ({total_time/60:.2f} min)")
    print(f"   - Tiempo promedio/imagen: {total_time/len(imagenes):.3f}s")
    print(f"\n📂 Imágenes guardadas en: {ruta_salida}")
    print("="*80)
    
    return resultados


# ============================================================================
# 🚀 EJEMPLOS DE USO
# ============================================================================

if __name__ == "__main__":
    
    print("\n" + "="*80)
    print("🐄 DETECTOR DE GANADO - SISTEMA COMPLETO")
    print("="*80)
    print("\nEste script contiene 2 funciones principales:")
    print("  1. procesar_video_yolo() - Procesar videos con YOLO")
    print("  2. procesar_carpeta_imagenes() - Filtrar imágenes con ganado")
    print("\nDescomenta el ejemplo que quieras ejecutar:\n")
    
    # ------------------------------------------------------------------------
    # EJEMPLO 1: PROCESAR VIDEO
    # ------------------------------------------------------------------------
    """
    # EJEMPLO 1: Procesar un video
    # Descomenta las siguientes líneas para ejecutar
    
    MODELO_PT = r"C:\Users\Alegu\Downloads\RESULTADOS´PRIMERENT\runs\detect\yolov8n_p2_960px_rtx3050\weights\best.pt"
    VIDEO_ENTRADA = r"C:\Users\Alegu\OneDrive\Desktop\ROBOTICA\PROYECTO SOPO\DETECTOR VACAS\PREPROCESSING\VIDEOS\DJI_0171.MP4"
    VIDEO_SALIDA = r"C:\Users\Alegu\Downloads\video_procesado_conf075.mp4"
    
    # Ejecutar función
    stats_video = procesar_video_yolo(
        ruta_modelo=MODELO_PT,
        ruta_video=VIDEO_ENTRADA,
        ruta_salida=VIDEO_SALIDA,
        confianza=0.75,  # Confianza profesional
        iou=0.45,
        img_size=960,
        guardar_video=True
    )
    
    print(f"\n📈 Resumen: {stats_video['total_detecciones']} detecciones en "
          f"{stats_video['tiempo_procesamiento_minutos']:.2f} minutos")
    """
    
    # ------------------------------------------------------------------------
    # EJEMPLO 2: PROCESAR CARPETA DE IMÁGENES
    # ------------------------------------------------------------------------
    """
    # EJEMPLO 2: Procesar carpeta de imágenes
    # Descomenta las siguientes líneas para ejecutar
    
    MODELO_PT = r"C:\Users\Alegu\Downloads\RESULTADOS´PRIMERENT\runs\detect\yolov8n_p2_960px_rtx3050\weights\best.pt"
    CARPETA_IMAGENES = r"C:\ruta\a\tu\carpeta\imagenes"  # ⬅️ CAMBIA ESTO
    CARPETA_SALIDA = r"C:\Users\Alegu\Downloads\imagenes_con_ganado"
    
    # Ejecutar función
    resultados_imagenes = procesar_carpeta_imagenes(
        ruta_modelo=MODELO_PT,
        ruta_carpeta_imagenes=CARPETA_IMAGENES,
        ruta_salida=CARPETA_SALIDA,
        confianza=0.75,  # Confianza profesional
        iou=0.45,
        img_size=960,
        copiar_imagenes=True,  # Copiar imágenes con detecciones
        guardar_coordenadas=True  # Guardar JSON con coordenadas
    )
    
    print(f"\n📈 Resumen: {len(resultados_imagenes)} imágenes con ganado detectado")
    
    # Ver coordenadas de las primeras 3 imágenes
    if resultados_imagenes:
        print("\n" + "="*80)
        print("📍 COORDENADAS PRECISAS DE DETECCIONES (3 primeras)")
        print("="*80)
        
        for idx, (nombre_imagen, info) in enumerate(list(resultados_imagenes.items())[:3], 1):
            print(f"\n🖼️  Imagen {idx}: {nombre_imagen}")
            print(f"   Total detecciones: {info['num_detecciones']}")
            
            for i, det in enumerate(info['detecciones'], 1):
                print(f"\n   🐄 Detección #{i}:")
                print(f"      - Clase: {det['clase']}")
                print(f"      - Confianza: {det['confianza']}")
                print(f"      - Coordenadas: ({det['coordenadas']['x1']}, {det['coordenadas']['y1']}) "
                      f"-> ({det['coordenadas']['x2']}, {det['coordenadas']['y2']})")
                print(f"      - Centro: ({det['centro']['x']}, {det['centro']['y']})")
                print(f"      - Tamaño: {det['ancho']}x{det['alto']} px")
    """
    
    print("\n💡 Para usar este script:")
    print("   1. Abre el archivo en un editor")
    print("   2. Ve a la sección '# EJEMPLOS DE USO'")
    print("   3. Descomenta el ejemplo que quieras ejecutar")
    print("   4. Modifica las rutas según tu configuración")
    print("   5. Ejecuta: python detector_ganado_funciones.py")
    print("\n" + "="*80)


# ============================================================================
# 📖 DOCUMENTACIÓN
# ============================================================================
"""
FUNCIÓN 1: procesar_video_yolo()
---------------------------------
Procesa un video completo con YOLO usando streaming eficiente.

Parámetros:
- ruta_modelo (str): Ruta al archivo .pt del modelo YOLO
- ruta_video (str): Ruta al video a procesar
- ruta_salida (str, opcional): Donde guardar el video procesado
- confianza (float, default=0.75): Confianza mínima para detección
- iou (float, default=0.45): Umbral IoU para NMS
- img_size (int, default=960): Tamaño de inferencia
- guardar_video (bool, default=True): Si guardar video con detecciones

Retorna: Diccionario con estadísticas completas del procesamiento

Ventajas:
- ✅ Procesa videos de cualquier duración
- ✅ Eficiente en memoria (streaming)
- ✅ Estadísticas detalladas en tiempo real
- ✅ Video de salida con visualizaciones


FUNCIÓN 2: procesar_carpeta_imagenes()
---------------------------------------
Procesa una carpeta de imágenes y devuelve solo las que tienen ganado detectado.

Parámetros:
- ruta_modelo (str): Ruta al archivo .pt del modelo YOLO
- ruta_carpeta_imagenes (str): Carpeta con imágenes a procesar
- ruta_salida (str): Donde guardar resultados
- confianza (float, default=0.75): Confianza mínima para detección
- iou (float, default=0.45): Umbral IoU para NMS
- img_size (int, default=960): Tamaño de inferencia
- copiar_imagenes (bool, default=True): Copiar imágenes con detecciones
- guardar_coordenadas (bool, default=True): Guardar JSON con coordenadas

Retorna: Diccionario con resultados por imagen (solo imágenes con detecciones)

Ventajas:
- ✅ Filtra automáticamente imágenes sin ganado
- ✅ Guarda coordenadas precisas en JSON
- ✅ Copia solo imágenes relevantes
- ✅ Información detallada por cada detección


RECOMENDACIONES:
----------------
Confianza 0.75:
- ⚖️ Balance óptimo precisión/recall
- ✅ Reduce falsos positivos significativamente
- 🎯 Ideal para alertas profesionales
- 📊 Ajustar según necesidad:
  - 0.5-0.6: Máximo recall (no perder ninguna vaca)
  - 0.75-0.80: Balance profesional
  - 0.85+: Máxima precisión (minimizar falsos positivos)
"""

