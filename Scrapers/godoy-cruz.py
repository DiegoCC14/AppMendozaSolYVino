
import json
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# CONFIGURACIÓN
# ============================================================

URL_ARCHIVO = "https://www.godoycruz.gob.ar/noticias/"
DOMINIO = "www.godoycruz.gob.ar"

LIMITE = 10  # Cantidad máxima de noticias. None para recorrer todas.
ARCHIVO_SALIDA = BASE_DIR/"Actividades/godoy-cruz.json"
PAUSA = 0.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# DESCARGA Y PARSEO DEL HTML
# ============================================================

def obtener_soup(url):
    """Descarga una página y devuelve su HTML parseado."""
    response = session.get(url, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


# ============================================================
# EXTRACCIÓN DE IMÁGENES
# ============================================================

def obtener_imagen(tarjeta):
    """Obtiene la imagen de mayor resolución disponible en la tarjeta."""

    imagen = tarjeta.select_one("img")

    if not imagen:
        return None

    srcset = imagen.get("srcset", "")

    if srcset:
        opciones = []

        for elemento in srcset.split(","):
            partes = elemento.strip().split()

            if not partes:
                continue

            url_imagen = partes[0]
            ancho = 0

            if len(partes) > 1:
                coincidencia = re.search(r"(\d+)w", partes[1])

                if coincidencia:
                    ancho = int(coincidencia.group(1))

            opciones.append((ancho, url_imagen))

        if opciones:
            opciones.sort(key=lambda x: x[0], reverse=True)
            return urljoin(URL_ARCHIVO, opciones[0][1])

    # Alternativas para imágenes con carga diferida
    src = (
        imagen.get("data-src")
        or imagen.get("data-lazy-src")
        or imagen.get("src")
    )

    if src:
        return urljoin(URL_ARCHIVO, src)

    return None


def obtener_imagen_principal(soup):
    """Busca la imagen principal en los metadatos del artículo."""

    etiqueta = soup.select_one('meta[property="og:image"]')

    if etiqueta and etiqueta.get("content"):
        return urljoin(URL_ARCHIVO, etiqueta["content"])

    imagen = soup.select_one(
        "#wpb-content-root .wpb_single_image img"
    )

    if imagen:
        return (
            imagen.get("src")
            or imagen.get("data-src")
            or imagen.get("data-lazy-src")
        )

    return None


# ============================================================
# EXTRACCIÓN DEL LISTADO DE NOTICIAS
# ============================================================

def extraer_tarjetas(soup):
    """Extrae título, enlace e imagen de las tarjetas del archivo."""

    noticias = []
    vistos = set()

    tarjetas = soup.select("#listadoNoticias .noticiaIndividual")

    for tarjeta in tarjetas:
        enlace = tarjeta.find_parent("a", href=True)

        if not enlace:
            continue

        link = urljoin(URL_ARCHIVO, enlace["href"]).split("#")[0]
        parsed = urlparse(link)

        if parsed.netloc not in (DOMINIO, "godoycruz.gob.ar"):
            continue

        titulo_elemento = tarjeta.select_one("h5")

        if not titulo_elemento:
            continue

        titulo = titulo_elemento.get_text(" ", strip=True)

        if not titulo or link in vistos:
            continue

        vistos.add(link)

        noticias.append({
            "titulo": titulo,
            "link": link,
            "imagen": obtener_imagen(tarjeta),
            "contenido": None,
        })

    return noticias


def obtener_noticias():
    """Recorre la paginación y recopila las noticias."""

    noticias = []
    vistos = set()
    pagina = 1

    while LIMITE is None or len(noticias) < LIMITE:

        if pagina == 1:
            url = URL_ARCHIVO
        else:
            url = urljoin(URL_ARCHIVO, f"page/{pagina}/")

        print(f"Consultando página {pagina}: {url}")

        try:
            soup = obtener_soup(url)
        except requests.RequestException as error:
            print(f"Error al descargar la página: {error}")
            break

        tarjetas = extraer_tarjetas(soup)

        if not tarjetas:
            print("No se encontraron más noticias.")
            break

        cantidad_anterior = len(noticias)

        for noticia in tarjetas:
            if noticia["link"] in vistos:
                continue

            vistos.add(noticia["link"])
            noticias.append(noticia)

            if LIMITE is not None and len(noticias) >= LIMITE:
                break

        print(f"Noticias recopiladas: {len(noticias)}")

        if len(noticias) == cantidad_anterior:
            print("No se encontraron noticias nuevas.")
            break

        pagina += 1
        time.sleep(PAUSA)

    return noticias


# ============================================================
# EXTRACCIÓN DEL CONTENIDO COMPLETO DE CADA NOTICIA
# ============================================================

def extraer_contenido(url):
    """Extrae el texto del contenedor principal de la noticia."""

    try:
        soup = obtener_soup(url)

        # Selector confirmado en el HTML proporcionado
        contenedor = soup.select_one("#wpb-content-root")

        if not contenedor:
            print("  No se encontró #wpb-content-root.")
            return None, None

        # Eliminar elementos que no aportan contenido textual
        for elemento in contenedor.select(
            "script, style, noscript, iframe, "
            "form, button, nav"
        ):
            elemento.decompose()

        bloques = []

        for elemento in contenedor.select(
            "h1, h2, h3, h4, h5, p, li, blockquote"
        ):
            texto = elemento.get_text(" ", strip=True)
            texto = re.sub(r"\s+", " ", texto).strip()

            if texto and (not bloques or bloques[-1] != texto):
                bloques.append(texto)

        contenido = "\n\n".join(bloques).strip()

        if not contenido:
            print("  No se encontró texto en el artículo.")
            return None, obtener_imagen_principal(soup)

        imagen_principal = obtener_imagen_principal(soup)

        return contenido, imagen_principal

    except requests.RequestException as error:
        print(f"  Error al descargar el artículo: {error}")
        return None, None


# ============================================================
# GUARDADO DEL JSON
# ============================================================

def guardar_json(noticias):
    """Guarda el progreso en JSON para evitar perder lo recopilado."""

    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as archivo:
        json.dump(
            noticias,
            archivo,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("SCRAPER DE NOTICIAS - GODOY CRUZ")
    print("=" * 60)

    noticias = obtener_noticias()

    if not noticias:
        print("No se encontraron noticias.")
        return

    print(f"\nSe procesarán {len(noticias)} noticias.\n")

    # Guardar primero el listado por si falla alguna descarga
    guardar_json(noticias)

    for numero, noticia in enumerate(noticias, start=1):
        print(f"[{numero}/{len(noticias)}] {noticia['titulo']}")
        
        noticia["fecha_creacion"] = datetime.now().strftime("%Y-%m-%d")

        contenido, imagen_articulo = extraer_contenido(
            noticia["link"]
        )

        noticia["contenido"] = contenido

        # Si no se obtuvo imagen de la tarjeta, usar la del artículo
        if not noticia["imagen"]:
            noticia["imagen"] = imagen_articulo

        if contenido:
            print(
                f"  Contenido extraído: "
                f"{len(contenido)} caracteres."
            )
        else:
            print("  No se pudo extraer el contenido.")

        # Guardar después de procesar cada artículo
        guardar_json(noticias)

        time.sleep(PAUSA)

    con_contenido = sum(
        bool(noticia["contenido"])
        for noticia in noticias
    )

    print("\n" + "=" * 60)
    print("PROCESO FINALIZADO")
    print("=" * 60)
    print(f"Archivo: {ARCHIVO_SALIDA}")
    print(f"Noticias recopiladas: {len(noticias)}")
    print(f"Noticias con contenido: {con_contenido}")
    print(f"Noticias sin contenido: {len(noticias) - con_contenido}")


if __name__ == "__main__":
    main()
