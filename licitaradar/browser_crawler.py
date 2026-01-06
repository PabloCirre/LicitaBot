"""
Extractor de datos de licitaciones usando Playwright.
Versión 2.1: Soporte para descarga y organización física de pliegos (PDFs).
"""

import os
import re
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def normalize_filename(name: str) -> str:
    """Limpia el nombre para ser usado como archivo."""
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = name.replace('\n', ' ').strip()
    return name[:150]

def esperar_carga_contenido(page: Page, timeout: int = 15000) -> bool:
    """Espera a que los elementos clave de la licitación estén visibles."""
    try:
        logging.info("Esperando indicio de carga (CSS)...")
        page.wait_for_selector("span[id*='text_Expediente']", timeout=timeout, state="visible")
        return True
    except Exception:
        try:
            logging.info("Esperando indicio de carga (Texto)...")
            page.wait_for_selector("text=Expediente", timeout=5000, state="visible")
            return True
        except Exception:
            logging.warning("No se encontró indicio claro de carga, procediendo con precaución.")
            return False

def extraer_datos_licitacion(url: str, save_dir: str, headless: bool = True) -> Dict:
    """Extrae datos y DESCARGA documentos físicos de la licitación."""
    if not PLAYWRIGHT_AVAILABLE:
        logging.error("Playwright no instalado")
        return {'campos': {}, 'documentos': [], 'enlaces': []}
    
    result = {
        'campos': {},
        'documentos': [],
        'url': url
    }
    
    os.makedirs(save_dir, exist_ok=True)
    docs_dir = os.path.join(save_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="LicitaRadar/2.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1600, "height": 1200}
        )
        page = context.new_page()
        page.set_default_timeout(45000)
        
        try:
            logging.info("Inicializando sesión...")
            page.goto("https://contrataciondelestado.es/wps/portal/plataforma", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            logging.info(f"Navegando a: {url}")
            page.goto(url, wait_until="domcontentloaded")
            esperar_carga_contenido(page)
            
            logging.info("Scroll y espera para carga completa...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
            
            # Screenshot y HTML Detalle
            page.screenshot(path=os.path.join(save_dir, "screenshot.png"), full_page=True)
            with open(os.path.join(save_dir, "detalle.html"), 'w', encoding='utf-8') as f:
                f.write(page.content())

            # 1. Extraer Campos (Metadata)
            campos = page.evaluate("""
                () => {
                    const data = {};
                    const labelSpans = document.querySelectorAll("span[id*='label_']");
                    labelSpans.forEach(lSpan => {
                        const labelValue = lSpan.innerText.trim().replace(/:$/, '');
                        if (!labelValue) return;
                        const textId = lSpan.id.replace('label_', 'text_');
                        const tSpan = document.getElementById(textId);
                        if (tSpan) {
                            data[labelValue] = tSpan.innerText.trim();
                        }
                    });
                    if (Object.keys(data).length < 3) {
                        document.querySelectorAll('td, th').forEach((cell, i) => {
                            const text = cell.innerText.trim();
                            if (text.endsWith(':') && text.length < 50) {
                                const key = text.replace(':', '');
                                const next = cell.nextElementSibling || (cell.parentElement ? cell.parentElement.cells[i+1] : null);
                                if (next) data[key] = next.innerText.trim();
                            }
                        });
                    }
                    return data;
                }
            """)
            result['campos'] = campos

            # 2. Extraer Enlaces de Documentos (Priorizando PDFs)
            enlaces_docs = page.evaluate("""
                () => {
                    const found = [];
                    const seen = new Set();
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (!href.includes('GetDocumentByIdServlet') && !href.toLowerCase().endsWith('.pdf')) return;
                        if (seen.has(href)) return;
                        
                        let name = a.innerText.trim();
                        if (!name || name.includes('abrirá en una nueva ventana')) {
                             name = a.title.trim() || "";
                             const row = a.closest('tr');
                             if ((!name || name.includes('abrirá')) && row) {
                                 const labelCol = row.querySelector('.tipoDocumento');
                                 if (labelCol) name = labelCol.innerText.trim();
                             }
                        }
                        name = name.replace(/abrirá en una nueva ventana/g, '').replace(/\\s+/g, ' ').trim();
                        
                        seen.add(href);
                        found.push({ url: href, nombre: name || "Documento", isPdf: href.toLowerCase().endsWith('.pdf') || true });
                    });
                    return found;
                }
            """)

            # 3. Descarga Física Selectiva
            logging.info(f"Iniciando descargas para {len(enlaces_docs)} documentos...")
            documentos_finales = []
            
            # Limitar a los primeros 8 para no eternizar
            for edoc in enlaces_docs[:8]:
                nombre_limpio = normalize_filename(edoc['nombre'])
                try:
                    # Estrategia robusta para encontrar el link: buscar por href contenido
                    # Escapamos comillas simples para el selector
                    safe_href = edoc['url'].replace("'", "\\'")
                    link_element = page.query_selector(f"a[href='{safe_href}']")
                    
                    if not link_element:
                        # Fallback: buscar por el ID del servlet si está presente
                        if 'DocumentIdParam=' in edoc['url']:
                            doc_id = edoc['url'].split('DocumentIdParam=')[1].split('&')[0]
                            link_element = page.query_selector(f"a[href*='{doc_id}']")

                    if link_element:
                        logging.info(f"Intentando descargar: {edoc['nombre']}")
                        # Scroll al elemento para asegurar visibilidad
                        link_element.scroll_into_view_if_needed()
                        
                        try:
                            # Manejar descargas que abren nuevas pestañas
                            with context.expect_page() as new_page_info:
                                with page.expect_download(timeout=20000) as download_info:
                                    link_element.click(force=True)
                            
                            download = download_info.value
                            ext = os.path.splitext(download.suggested_filename)[1] or ".pdf"
                            final_path = os.path.join(docs_dir, f"{nombre_limpio}{ext}")
                            
                            # Evitar duplicados
                            counter = 1
                            while os.path.exists(final_path):
                                final_path = os.path.join(docs_dir, f"{nombre_limpio}_{counter}{ext}")
                                counter += 1
                                
                            download.save_as(final_path)
                            logging.info(f"Guardado: {os.path.basename(final_path)}")
                            
                            documentos_finales.append({
                                'nombre': edoc['nombre'],
                                'url': edoc['url'],
                                'local_path': os.path.relpath(final_path, save_dir),
                                'status': 'descargado'
                            })
                        except Exception as inner_e:
                            logging.warning(f"Error en paso intermedio de descarga: {inner_e}")
                            # Intentar descarga directa si falló el click/catch
                            documentos_finales.append({'nombre': edoc['nombre'], 'url': edoc['url'], 'status': 'solo_link'})
                    else:
                        logging.warning(f"No se encontró el elemento para: {edoc['nombre']}")
                except Exception as de:
                    logging.warning(f"Error procesando enlace {edoc['nombre']}: {de}")
                    documentos_finales.append({'nombre': edoc['nombre'], 'url': edoc['url'], 'status': 'error'})

            result['documentos'] = documentos_finales
            logging.info(f"Descargas completadas: {len(documentos_finales)} archivos procesados.")

        except Exception as e:
            logging.error(f"Error crítico en crawler: {e}")
            result['error'] = str(e)
            
        finally:
            browser.close()
            
    return result


def generar_resumen(save_dir: str, url: str, titulo: str, keyword: str, datos: Dict):
    """Genera resumen.md con enlaces locales a archivos."""
    resumen_path = os.path.join(save_dir, "resumen.md")
    
    with open(resumen_path, "w", encoding="utf-8") as f:
        f.write(f"# {titulo}\n\n")
        f.write(f"**URL Original:** [{url}]({url})\n\n")
        f.write(f"**Identidad:** `LicitaRadar 2.0` | **Filtro:** `{keyword}`\n\n")
        
        campos = datos.get('campos', {})
        if campos:
            f.write("## Datos del Expediente\n\n")
            prioritarios = ['Expediente', 'Estado', 'Órgano de contratación', 'Objeto', 'Presupuesto', 'Valor estimado', 'Fecha límite']
            mostrados = set()
            for p in prioritarios:
                for k in campos:
                    if p.lower() in k.lower() and k not in mostrados:
                        f.write(f"- **{k}:** {campos[k]}\n")
                        mostrados.add(k)
            for k, v in campos.items():
                if k not in mostrados and len(v) < 300:
                    f.write(f"- **{k}:** {v}\n")
        
        docs = datos.get('documentos', [])
        if docs:
            f.write(f"\n## Documentos Descargados ({len(docs)})\n\n")
            f.write("| Documento | Archivo Local | Enlace Original |\n")
            f.write("| :--- | :--- | :--- |\n")
            for d in docs:
                nombre = d['nombre'].replace('\n', ' ').strip()
                local = f"[📂 Abrir]({d['local_path'].replace('\\\\', '/')})" if d.get('local_path') else "N/A"
                f.write(f"| {nombre} | {local} | [Original]({d['url']}) |\n")
        else:
            f.write("\n## Documentos\n\nNo se detectaron documentos físicos.\n")
    
    logging.info(f"Resumen actualizado con archivos locales en: {resumen_path}")


def procesar_licitacion(url: str, titulo: str, keyword: str, base_dir: str = "./data/licitaciones") -> Dict:
    from .utils import get_safe_project_name
    project_name = get_safe_project_name(titulo, url, base_dir)
    save_dir = os.path.join(base_dir, project_name)
    logging.info(f"Iniciando flujo completo para: {project_name}")
    datos = extraer_datos_licitacion(url, save_dir)
    generar_resumen(save_dir, url, titulo, keyword, datos)
    return { 'project_dir': save_dir, 'project_name': project_name, **datos }

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    url = sys.argv[1] if len(sys.argv) > 1 else "https://contrataciondelestado.es/wps/poc?uri=deeplink:detalle_licitacion&idEvl=OeYkKIOTEdeAAM7L03kM8A%3D%3D"
    procesar_licitacion(url, "Licitación Demo con Descargas", "demo", "./data/licitaciones")
