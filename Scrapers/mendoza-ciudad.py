
import json
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

URL_ARCHIVO = "https://prensa.ciudaddemendoza.gob.ar/archivo/"
DOMINIO = "prensa.ciudaddemendoza.gob.ar"
LIMITE = 10
ARCHIVO_SALIDA = BASE_DIR/"Actividades/mendoza-ciudad.json"
PAUSA = 0.4

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


def obtener_soup(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def es_url_noticia(url):
    parsed = urlparse(url)

    return (
        parsed.scheme in ("http", "https")
        and parsed.netloc == DOMINIO
        and parsed.path.strip("/") not in ("", "archivo")
        and not parsed.path.startswith("/wp-")
    )


def extraer_tarjetas(soup):
    """
    Extrae título, enlace e imagen de las tarjetas.
    """
    noticias = []
    vistos = set()

    tarjetas = soup.select(".jet-listing-grid__item")

    # Alternativa por si la estructura cambia.
    if not tarjetas:
        tarjetas = soup.select("article.elementor-post")

    for tarjeta in tarjetas:
        enlace = tarjeta.select_one(
            "h2.elementor-heading-title a, "
            ".elementor-post__title a, "
            "a[href]"
        )

        if not enlace:
            continue

        titulo = enlace.get_text(" ", strip=True)
        href = enlace.get("href")

        if not titulo or not href:
            continue

        link = urljoin(URL_ARCHIVO, href).split("#")[0]

        if not es_url_noticia(link) or link in vistos:
            continue

        vistos.add(link)

        noticias.append({
            "titulo": titulo,
            "link": link,
            "imagen": extraer_imagen(tarjeta),
            "contenido": None,
            "fecha_creacion": datetime.now().strftime("%Y-%m-%d")
        })

    return noticias


def extraer_imagen(tarjeta):
    """
    Busca imágenes en etiquetas img y en fondos CSS.
    """
    for img in tarjeta.select("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
        )

        if not src:
            srcset = img.get("data-srcset") or img.get("srcset")
            if srcset:
                src = srcset.split(",")[0].strip().split()[0]

        if src:
            return urljoin(URL_ARCHIVO, src)

    for elemento in [tarjeta, *tarjeta.select("[style]")]:
        estilo = elemento.get("style", "")

        coincidencia = re.search(
            r"""background-image\s*:\s*url\(['"]?(.*?)['"]?\)""",
            estilo,
            re.IGNORECASE,
        )

        if coincidencia:
            return urljoin(URL_ARCHIVO, coincidencia.group(1))

    for style in tarjeta.find_all("style"):
        coincidencia = re.search(
            r"""background-image\s*:\s*url\(['"]?(.*?)['"]?\)""",
            style.get_text(),
            re.IGNORECASE,
        )

        if coincidencia:
            return urljoin(URL_ARCHIVO, coincidencia.group(1))

    return None


def obtener_noticias_recientes():
    """
    Recorre las rutas habituales de paginación de WordPress.
    Si la paginación AJAX es obligatoria, será necesario adaptar
    esta función a los parámetros concretos que exige el sitio.
    """
    noticias = []
    vistos = set()

    pagina = 1
    paginas_maximas = 5

    while len(noticias) < LIMITE and pagina <= paginas_maximas:
        if pagina == 1:
            urls = [URL_ARCHIVO]
        else:
            urls = [
                urljoin(URL_ARCHIVO, f"page/{pagina}/"),
                f"{URL_ARCHIVO}?paged={pagina}",
            ]

        encontradas = []
        pagina_valida = False

        for url in urls:
            try:
                soup = obtener_soup(url)
                encontradas = extraer_tarjetas(soup)

                if encontradas:
                    pagina_valida = True
                    break

            except requests.RequestException as error:
                print(f"Error consultando {url}: {error}")

        if not pagina_valida:
            print(
                f"No se pudieron encontrar tarjetas en la página {pagina}. "
                "Se detiene la búsqueda."
            )
            break

        cantidad_anterior = len(noticias)

        for noticia in encontradas:
            if noticia["link"] in vistos:
                continue

            vistos.add(noticia["link"])
            noticias.append(noticia)

            if len(noticias) >= LIMITE:
                break

        print(
            f"Página {pagina}: {len(encontradas)} tarjetas; "
            f"{len(noticias)} noticias acumuladas."
        )

        if len(noticias) == cantidad_anterior:
            print("No se encontraron noticias nuevas.")
            break

        pagina += 1
        time.sleep(PAUSA)

    return noticias[:LIMITE]


def extraer_contenido(link):
    """
    Extrae el cuerpo de una noticia sin incluir la fecha,
    los botones para compartir ni la navegación.
    """
    try:
        soup = obtener_soup(link)

        selectores = [
            ".elementor-widget-theme-post-content "
            ".elementor-widget-container "
            'div[data-elementor-type="wp-post"]',
            ".elementor-widget-theme-post-content "
            ".elementor-widget-container",
            ".entry-content",
            "article .elementor-post__text",
        ]

        contenedor = None

        for selector in selectores:
            contenedor = soup.select_one(selector)
            if contenedor:
                break

        if not contenedor:
            print("  No se encontró el cuerpo de la noticia.")
            return None

        # Eliminar elementos que no forman parte del contenido.
        for elemento in contenedor.select(
            "script, style, noscript, iframe, "
            ".elementor-widget-share-buttons, "
            ".elementor-widget-author-box, "
            ".elementor-widget-post-navigation, "
            ".elementor-post-navigation, "
            ".elementor-widget-post-info"
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

        if bloques:
            return "\n\n".join(bloques)

        texto = contenedor.get_text("\n", strip=True)
        return texto or None

    except requests.RequestException as error:
        print(f"  Error al descargar la noticia: {error}")
        return None


def guardar_json(noticias):
    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as archivo:
        json.dump(
            noticias,
            archivo,
            ensure_ascii=False,
            indent=2,
        )


def main():
    print("Buscando noticias recientes...\n")

    noticias = obtener_noticias_recientes()

    if not noticias:
        print("No se encontraron noticias.")
        return

    print(f"\nSe procesarán {len(noticias)} noticias.\n")

    for i, noticia in enumerate(noticias, start=1):
        print(f"[{i}/{len(noticias)}] {noticia['titulo']}")

        noticia["contenido"] = extraer_contenido(noticia["link"])

        if noticia["contenido"]:
            print(
                f"  Contenido extraído: "
                f"{len(noticia['contenido'])} caracteres."
            )
        else:
            print("  No se pudo extraer el contenido.")

        # Guardar después de cada noticia para conservar el progreso.
        guardar_json(noticias)
        time.sleep(PAUSA)

    print(f"\nProceso finalizado. Archivo: {ARCHIVO_SALIDA}")
    print(f"Noticias recopiladas: {len(noticias)}")
    print(
        "Noticias con contenido: "
        f"{sum(bool(n['contenido']) for n in noticias)}"
    )

    if len(noticias) < LIMITE:
        print(
            "\nATENCIÓN: no se alcanzaron las 10 noticias. "
            "El sitio puede requerir paginación AJAX."
        )


if __name__ == "__main__":
    main()
