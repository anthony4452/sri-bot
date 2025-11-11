import re
import time
import os
import sys
from datetime import datetime
from playwright.sync_api import Playwright, sync_playwright

os.environ["DISPLAY"] = ":99"

def run(playwright: Playwright) -> None:
    if len(sys.argv) < 6:
        print("❌ Faltan argumentos. Uso:")
        print("python3 download_recibidas.py <ruc> <ci> <clave> <ano> <mes>")
        sys.exit(1)

    ruc = sys.argv[1].strip()
    ci = sys.argv[2].strip()
    clave = sys.argv[3].strip()
    ano = sys.argv[4].strip()
    mes = sys.argv[5].strip()
    dia = "0"

    print(f"✅ Parámetros recibidos: RUC={ruc}, CI={ci}, Año={ano}, Mes={mes}")

    # Crear carpeta única de proceso
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_folder = f"/usr/src/descargas/recibidas/recibidas_{ruc}_{timestamp}"
    os.makedirs(download_folder, exist_ok=True)
    print(f"📂 Carpeta de descarga: {download_folder}")

    comprobante_num = 1

    print("\n🚀 Iniciando navegador...")

    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--disable-features=VizDisplayCompositor",
            "--window-size=1920,1080"
        ]
    )

    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    # === Paso 1: Login ===
    print("➡️ Accediendo a SRI...")
    page.goto("https://srienlinea.sri.gob.ec/sri-en-linea/inicio/NAT")
    page.get_by_role("link", name="Ir a iniciar sesión").click()
    page.get_by_role("textbox", name="*RUC / C.I. / Pasaporte").fill(ruc)
    page.get_by_role("textbox", name="C.I. adicional").fill(ci)
    page.get_by_role("textbox", name="*Clave").fill(clave)
    page.get_by_role("button", name="Ingresar").click()

    page.get_by_role("textbox", name="*RUC / C.I. / Pasaporte").fill(ruc)
    page.get_by_role("textbox", name="*Clave").fill(clave)
    page.get_by_role("button", name="Ingresar").click()

    # === Paso 2: Navegar al módulo de facturación ===
    print("➡️ Accediendo al módulo de facturación...")
    page.locator("sri-titulo-modal-mat div").nth(2).click()
    page.get_by_role("button", name="Abrir o cerrar menu desplegado").click()
    page.get_by_role("link", name="  FACTURACIÓN ELECTRÓNICA").click()
    page.get_by_role("link", name=" Producción").click()
    page.get_by_role("listitem").filter(has_text=re.compile(r"^Consultas$")).get_by_role("link").click()
    page.get_by_role("link", name="Comprobantes electrónicos recibidos").click()

    # === Paso 3: Selección de fecha ===
    print(f"📅 Consultando {ano}-{mes.zfill(2)}...")
    page.locator("#frmPrincipal\\:ano").select_option(ano)
    page.locator("#frmPrincipal\\:mes").select_option(mes)
    page.locator("#frmPrincipal\\:dia").select_option(dia)
    page.get_by_role("button", name="Consultar").click()

    # === Paso 4: Espera CAPTCHA y tabla ===
    print("🧩 Esperando a que la tabla de comprobantes esté lista (resuelve CAPTCHA manualmente)...")
    page.wait_for_selector("#frmPrincipal\\:tablaCompRecibidos_data tr", timeout=180000)  # 3 min max

    # === Paso 5: Descargar todos los comprobantes ===
    print("📥 Descargando comprobantes...")

    while True:
        filas = page.locator("#frmPrincipal\\:tablaCompRecibidos_data tr")
        total = filas.count()
        print(f"✅ {total} comprobantes en esta página")

        for i in range(total):
            try:
                link_xml = filas.nth(i).locator("td:nth-child(10) a")
                archivo_destino = os.path.join(download_folder, f"comprobante_{comprobante_num}.xml")

                if os.path.exists(archivo_destino):
                    print(f"⚠️ El comprobante {comprobante_num} ya existe, se omite")
                    comprobante_num += 1
                    continue

                with page.expect_download() as download_info:
                    link_xml.click()
                download = download_info.value
                download.save_as(archivo_destino)
                print(f"📄 Descargado comprobante {comprobante_num}")
                comprobante_num += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Error al descargar comprobante {comprobante_num}: {e}")
                comprobante_num += 1

        siguiente = page.locator("#frmPrincipal\\:tablaCompRecibidos_paginator_bottom .ui-paginator-next")
        if "ui-state-disabled" in siguiente.get_attribute("class"):
            break
        else:
            siguiente.click()
            time.sleep(1)

    print(f"🎉 Descargados {comprobante_num-1} comprobantes en total")

    # === Paso 6: Cerrar sesión ===
    print("🚪 Cerrando sesión...")
    try:
        page.get_by_role("link", name=" Cerrar sesión").click()
        page.get_by_role("button", name="Continuar").click()
    except:
        print("⚠️ No se pudo cerrar sesión (posiblemente ya desconectado).")

    print("🎉 Proceso finalizado correctamente.")
    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
