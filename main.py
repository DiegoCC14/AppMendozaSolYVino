
import json
import subprocess
import sys
from pathlib import Path


# Carpeta donde se encuentra main.py
BASE_DIR = Path(__file__).resolve().parent

# Archivos .py y sus respectivos archivos .json.
# Se ejecutan y procesan en este orden.
FUENTES = [
    ("Scrapers/mendoza-ciudad.py", "Actividades/mendoza-ciudad.json"),
    ("Scrapers/guaymallen.py", "Actividades/guaymallen.json"),
    ("Scrapers/godoy-cruz.py", "Actividades/godoy-cruz.json"),
]

DATA_FILE = BASE_DIR / "data.json"


def ejecutar_scripts():
    """Ejecuta los scripts secuencialmente."""
    for script, _ in FUENTES:
        ruta_script = BASE_DIR / script

        if not ruta_script.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo: {ruta_script}"
            )

        print(f"\nEjecutando {script}...")

        # Espera a que termine antes de continuar.
        subprocess.run(
            [sys.executable, str(ruta_script)],
            cwd=BASE_DIR,
            check=True
        )

        print(f"{script} finalizado correctamente.")


def cargar_json(ruta):
    """Carga un JSON que contiene una lista o un objeto."""
    with ruta.open("r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if isinstance(contenido, list):
        return contenido

    if isinstance(contenido, dict):
        # También admite estructuras como {"noticias": [...]}
        for clave in ("noticias", "data", "items", "results"):
            if isinstance(contenido.get(clave), list):
                return contenido[clave]

        # Si el JSON contiene una única noticia.
        return [contenido]

    raise ValueError(f"Formato JSON no válido en {ruta.name}")


def obtener_titulo(noticia):
    """Obtiene el título, admitiendo distintos nombres de campo."""
    if not isinstance(noticia, dict):
        return ""

    for clave in ("titulo", "Título", "Titulo", "title"):
        valor = noticia.get(clave)

        if isinstance(valor, str) and valor.strip():
            return valor.strip()

    return ""


def normalizar_titulo(titulo):
    """Evita duplicados por diferencias de mayúsculas o espacios."""
    return " ".join(titulo.split()).casefold()


def unir_noticias():
    """Agrega a data.json solamente las noticias nuevas."""
    if DATA_FILE.exists():
        noticias_existentes = cargar_json(DATA_FILE)
    else:
        noticias_existentes = []

    # Títulos que ya existen en data.json.
    titulos_existentes = {
        normalizar_titulo(titulo)
        for noticia in noticias_existentes
        if (titulo := obtener_titulo(noticia))
    }

    agregadas = 0

    for _, nombre_json in FUENTES:
        ruta_json = BASE_DIR / nombre_json

        if not ruta_json.exists():
            print(f"Advertencia: no existe {nombre_json}; se omite.")
            continue

        print(f"Leyendo {nombre_json}...")
        noticias_nuevas = cargar_json(ruta_json)

        for noticia in noticias_nuevas:
            titulo = obtener_titulo(noticia)

            if not titulo:
                print(
                    f"Advertencia: noticia sin título en {nombre_json}; "
                    "se omite."
                )
                continue

            titulo_normalizado = normalizar_titulo(titulo)

            if titulo_normalizado not in titulos_existentes:
                noticias_existentes.append(noticia)
                titulos_existentes.add(titulo_normalizado)
                agregadas += 1

    # Guarda el resultado actualizado.
    # Se conservan todas las noticias anteriores y las nuevas.
    with DATA_FILE.open("w", encoding="utf-8") as archivo:
        json.dump(
            noticias_existentes,
            archivo,
            ensure_ascii=False,
            indent=2
        )

    print(f"\nProceso finalizado.")
    print(f"Noticias nuevas agregadas: {agregadas}")
    print(f"Total de noticias en data.json: {len(noticias_existentes)}")
    print(f"Archivo actualizado: {DATA_FILE}")


def main():
    # Primero ejecuta todas las fuentes en orden.
    ejecutar_scripts()

    # Después une los JSON y elimina duplicados por título.
    unir_noticias()


if __name__ == "__main__":
    main()
