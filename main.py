import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 1. Definir zona horaria de Argentina (UTC-3)
tz_ar = timezone(timedelta(hours=-3))
ahora = datetime.now(tz_ar)

# 2. Formatear el nombre: ej. "2026-11-19_2026-11-19_21-35-00.json"
fecha_actual = ahora.strftime("%Y-%m-%d")
fecha_y_hora = ahora.strftime("%Y-%m-%d_%H-%M-%S")
nombre_archivo = f"{fecha_actual}_{fecha_y_hora}.json"

# 3. Crear la carpeta "Actividades" en la raíz si no existe
carpeta = Path("Actividades")
carpeta.mkdir(parents=True, exist_ok=True)
ruta_archivo = carpeta / nombre_archivo

# 4. Datos a guardar en el JSON (reemplaza esto con la lógica de tu app)
datos = {
    "fecha_ejecucion": ahora.isoformat(),
    "estado": "completado",
    "actividades": []
}

# 5. Guardar el archivo JSON
with open(ruta_archivo, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, indent=4)

print(f"Archivo generado correctamente en: {ruta_archivo}")
