
import json
import time
import requests
from datetime import datetime

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

URL_BASE = "https://www.guaymallen.gob.ar"
URL_NOTICIAS = f"{URL_BASE}/prensa/"

LIMITE = 10  # Cantidad máxima de noticias. None para todas.
ARCHIVO_SALIDA = BASE_DIR/"Actividades/guaymallen.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 30


def obtener_soup(url):
    """Descarga una página y devuelve su HTML analizado."""
    try:
        respuesta = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        respuesta.raise_for_status()

        respuesta.encoding = respuesta.apparent_encoding

        return BeautifulSoup(respuesta.text, "html.parser")

    except requests.RequestException as e:
        print(f"Error al acceder a {url}: {e}")
        return None


def obtener_imagen_url(img, pagina_url):
    """Obtiene la imagen de mayor resolución disponible."""
    if img is None:
        return None

    # Primero intenta obtener la imagen de mayor tamaño del srcset.
    srcset = img.get("srcset") or img.get("data-srcset")

    if srcset:
        candidatos = []

        for elemento in srcset.split(","):
            partes = elemento.strip().split()

            if not partes:
                continue

            url = partes[0]
            ancho = 0

            if len(partes) > 1 and partes[1].endswith("w"):
                try:
                    ancho = int(partes[1][:-1])
                except ValueError:
                    pass

            candidatos.append((ancho, url))

        if candidatos:
            return urljoin(
                pagina_url,
                max(candidatos, key=lambda x: x[0])[1]
            )

    # Fallbacks para imágenes con carga diferida.
    for atributo in (
        "data-lazy-src",
        "data-src",
        "data-original",
        "src"
    ):
        valor = img.get(atributo)

        if valor and not valor.startswith("data:image"):
            return urljoin(pagina_url, valor)

    return None


def extraer_tarjetas(soup):
    """Extrae título, enlace e imagen del listado de noticias."""
    noticias = []
    enlaces_vistos = set()

    contenedor = soup.select_one(".elementor-loop-container")

    if contenedor is None:
        print("No se encontró .elementor-loop-container.")
        return noticias

    tarjetas = contenedor.select('[data-elementor-type="loop-item"]')

    # Fallback por si Elementor cambia la estructura de las tarjetas.
    if not tarjetas:
        tarjetas = contenedor.select(".e-loop-item")

    for tarjeta in tarjetas:
        enlace = tarjeta.select_one("h1 a, h2 a, h3 a")

        if enlace is None:
            enlace = tarjeta.select_one("a[href]")

        if enlace is None:
            continue

        titulo = enlace.get_text(" ", strip=True)
        link = urljoin(URL_BASE, enlace.get("href", ""))

        if not titulo or not link:
            continue

        if link in enlaces_vistos:
            continue

        # Evita enlaces que no sean noticias del sitio.
        if not link.startswith(URL_BASE + "/"):
            continue

        enlaces_vistos.add(link)

        # Prioriza la imagen destacada de la tarjeta.
        imagen_tag = tarjeta.select_one(
            ".elementor-widget-theme-post-featured-image img"
        )

        if imagen_tag is None:
            imagen_tag = tarjeta.select_one("img")

        imagen = obtener_imagen_url(imagen_tag, URL_BASE)

        noticias.append({
            "titulo": titulo,
            "link": link,
            "imagen": imagen,
            "contenido": "",
            "fecha_creacion": datetime.now().strftime("%Y-%m-%d")
        })

    return noticias


def extraer_contenido(url):
    """Extrae el texto y la imagen principal de una noticia."""
    soup = obtener_soup(url)

    if soup is None:
        return "", None

    # La imagen principal suele estar en los metadatos Open Graph.
    imagen_principal = None

    meta_imagen = soup.select_one(
        'meta[property="og:image"]'
    )

    if meta_imagen:
        imagen_principal = meta_imagen.get("content")

    if imagen_principal:
        imagen_principal = urljoin(url, imagen_principal)

    # Fallback: imagen destacada del artículo.
    if not imagen_principal:
        img = soup.select_one(
            ".elementor-widget-theme-post-featured-image img"
        )
        imagen_principal = obtener_imagen_url(img, url)

    # Toma el contenido específico de la noticia.
    contenedor = soup.select_one(
        ".elementor-widget-theme-post-content"
    )

    if contenedor is None:
        print(f"No se encontró el contenido de: {url}")
        return "", imagen_principal

    # Elimina elementos que no forman parte del texto.
    for elemento in contenedor.select(
        "script, style, iframe, form, "
        ".elementor-button-wrapper, .elementor-share-buttons"
    ):
        elemento.decompose()

    bloques = []

    for elemento in contenedor.select(
        "h2, h3, h4, p, li, blockquote"
    ):
        texto = elemento.get_text(" ", strip=True)

        if texto and texto not in bloques:
            bloques.append(texto)

    contenido = "\n\n".join(bloques)

    # Fallback si la estructura del contenido cambia.
    if not contenido:
        contenido = contenedor.get_text("\n", strip=True)

    return contenido, imagen_principal


def guardar_json(noticias):
    """Guarda las noticias en JSON con codificación UTF-8."""
    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as archivo:
        json.dump(
            noticias,
            archivo,
            ensure_ascii=False,
            indent=4
        )


def obtener_noticias():
    noticias = []
    enlaces_procesados = set()
    pagina = 1

    while True:
        if LIMITE is not None and len(noticias) >= LIMITE:
            break

        if pagina == 1:
            url_pagina = URL_NOTICIAS
        else:
            url_pagina = f"{URL_NOTICIAS}page/{pagina}/"

        print(f"\nLeyendo listado: {url_pagina}")

        soup = obtener_soup(url_pagina)

        if soup is None:
            break

        tarjetas = extraer_tarjetas(soup)

        if not tarjetas:
            print("No se encontraron más noticias.")
            break

        nuevas = [
            noticia
            for noticia in tarjetas
            if noticia["link"] not in enlaces_procesados
        ]

        if not nuevas:
            print("No hay noticias nuevas en esta página.")
            break

        for noticia in nuevas:
            if LIMITE is not None and len(noticias) >= LIMITE:
                break

            link = noticia["link"]
            enlaces_procesados.add(link)

            print(f"\n[{len(noticias) + 1}] {noticia['titulo']}")

            contenido, imagen_principal = extraer_contenido(link)

            noticia["contenido"] = contenido

            # Prioriza la imagen principal del artículo.
            if imagen_principal:
                noticia["imagen"] = imagen_principal

            noticias.append(noticia)

            # Guarda el avance para no perder lo procesado.
            guardar_json(noticias)

            print(f"Contenido extraído: {len(contenido)} caracteres")

            time.sleep(0.5)

        pagina += 1

    guardar_json(noticias)

    return noticias


def main():
    print("Iniciando scraper de noticias de Guaymallén...")

    noticias = obtener_noticias()

    print(f"\nProceso finalizado.")
    print(f"Noticias guardadas: {len(noticias)}")
    print(f"Archivo generado: {ARCHIVO_SALIDA}")


if __name__ == "__main__":
    main()
