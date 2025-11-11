import os
import sys
import time
import re
from datetime import datetime
from playwright.sync_api import Playwright, sync_playwright

def run(playwright: Playwright) -> None:
    if len(sys.argv) < 8:
        print("❌ Faltan argumentos. Uso:")
        print("python3 download_emitidas.py <ruc> <ci> <clave> <fecha_dd/mm/yyyy> <estado> <tipo> <establecimiento>")
        sys.exit(1)

    ruc = sys.argv[1].strip()
    ci = sys.argv[2].strip()
    clave = sys.argv[3].strip()
    fecha = sys.argv[4].strip()
    estado = sys.argv[5].strip()        # AUT, NAT, PPR
    tipo = sys.argv[6].strip()          # 1 a 6
    establecimiento = sys.argv[7].strip()  # Normalmente ""

    print(f"✅ Parámetros recibidos: RUC={ruc}, Fecha={fecha}, Estado={estado}, Tipo={tipo}")

    # Carpeta de descargas
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_folder = f"/usr/src/descargas/emitidas/emitidas_{ruc}_{timestamp}"
    os.makedirs(download_folder, exist_ok=True)
    print(f"📂 Carpeta de descarga: {download_folder}")

    comprobante_num = 1

    print("\n🚀 Iniciando navegador...")
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    # === Login ===
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
    print("✅ Login exitoso")

    # === Cerrar modal interno y navegar a emitidas ===
    print("➡️ Accediendo al módulo de facturación...")
    try:
        page.locator("sri-titulo-modal-mat div").nth(2).click()
        print("✅ Modal interno cerrado")
    except:
        print("ℹ️ No apareció el modal interno, continuando...")

    page.get_by_role("button", name="Abrir o cerrar menu desplegado").click()
    page.get_by_role("link", name="  FACTURACIÓN ELECTRÓNICA").click()
    page.get_by_role("link", name=" Producción").click()
    page.get_by_role("listitem").filter(has_text=re.compile(r"^Consultas$")).get_by_role("link").click()
    page.get_by_role("link", name="Comprobantes electrónicos emitidos").click()
    print("✅ Accedido a Comprobantes electrónicos emitidos")

    # === Selección de filtros ===
    print(f"📅 Consultando fecha {fecha}, Estado={estado}, Tipo={tipo}")
    page.locator("#frmPrincipal\\:calendarFechaDesde_input").fill(fecha)
    page.locator("#frmPrincipal\\:cmbEstadoAutorizacion").select_option(estado)
    page.locator("#frmPrincipal\\:cmbTipoComprobante").select_option(tipo)
    page.locator("#frmPrincipal\\:cmbEstablecimiento").select_option(establecimiento)
    page.get_by_role("button", name="Consultar").click()

    # === Verificar mensajes del sistema ===
    time.sleep(3)  # espera a que cargue mensajes o tabla

    mensaje = ""
    try:
        mensaje = page.locator("[id='formMessages:messages'] div").text_content(timeout=3000)
    except:
        pass

    filas = page.locator("#frmPrincipal\\:tablaCompEmitidos_data tr")
    if mensaje:
        mensaje = mensaje.strip()
        print(f"⚠️ Mensaje del sistema: {mensaje}")
        print("🚪 Cerrando sesión y finalizando proceso...")
        try:
            page.get_by_role("link", name=" Cerrar sesión").click()
            page.get_by_role("button", name="Continuar").click()
        except:
            pass
        context.close()
        browser.close()
        print("🎉 Proceso finalizado sin descargas debido al mensaje.")
        return
    elif filas.count() == 0:
        print("⚠️ No hay comprobantes para los parámetros ingresados")
        try:
            page.get_by_role("link", name=" Cerrar sesión").click()
            page.get_by_role("button", name="Continuar").click()
        except:
            pass
        context.close()
        browser.close()
        print("🎉 Proceso finalizado sin descargas.")
        return

    # === Descarga de comprobantes ===
    print("📥 Descargando comprobantes...")
    while True:
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

        # Paginación
        siguiente = page.locator("#frmPrincipal\\:tablaCompEmitidos_paginator_bottom .ui-paginator-next")
        if "ui-state-disabled" in siguiente.get_attribute("class"):
            break
        else:
            siguiente.click()
            time.sleep(1)

    # === Cerrar sesión ===
    print("🚪 Cerrando sesión...")
    try:
        page.get_by_role("link", name=" Cerrar sesión").click()
        page.get_by_role("button", name="Continuar").click()
    except:
        print("⚠️ No se pudo cerrar sesión.")

    context.close()
    browser.close()
    print("🎉 Proceso finalizado correctamente.")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
