from playwright.sync_api import sync_playwright

try:
    from utils.config import URL_FISCALIA, HEADLESS, TIMEOUT, ESPERA_BUSQUEDA
except ImportError:
    try:
        from src.utils.config import URL_FISCALIA, HEADLESS, TIMEOUT, ESPERA_BUSQUEDA
    except ImportError:
        URL_FISCALIA = "https://www.fiscalia.gob.ec/accesibilidad/consulta-de-noticias-del-delito/"
        HEADLESS = True
        TIMEOUT = 5000
        ESPERA_BUSQUEDA = 3000


class BuscadorFiscalia:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    def iniciar(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        self.page = self.browser.new_page()
        self.page.goto(URL_FISCALIA)

        # Esperar a que el iframe se cargue o usar fallback corto
        try:
            self.obtener_iframe()
        except Exception:
            self.page.wait_for_timeout(2000)

        print("✅ Fiscalía abierta correctamente")

    def obtener_iframe(self):
        # Polling corto para esperar el iframe (hasta 10 segundos)
        for _ in range(20):
            for frame in self.page.frames:
                if "gestiondefiscalias" in frame.url:
                    return frame
            self.page.wait_for_timeout(500)

        raise Exception("No se encontró iframe Fiscalía")

    def limpiar_busqueda(self, frame):
        try:
            frame.click("#btn_limpiar_campo")
            # Esperar a que el campo de texto se limpie realmente
            frame.wait_for_function(
                "document.querySelector('#pwd').value === ''",
                timeout=2000,
            )
        except Exception:
            frame.wait_for_timeout(500)

    def _buscar(self, valor):
        """Escribe el valor en el buscador, presiona Buscar y devuelve el texto del iframe."""
        frame = self.obtener_iframe()
        self.limpiar_busqueda(frame)
        frame.locator("#pwd").fill(valor)

        try:
            # Esperar dinámicamente la respuesta HTTP que consulta la denuncia
            with self.page.expect_response(
                lambda r: "gestiondefiscalias" in r.url,
                timeout=3500,
            ):
                frame.click("#btn_buscar_denuncia")
            # Margen de renderizado del DOM en el iframe
            self.page.wait_for_timeout(500)
        except Exception:
            self.page.wait_for_timeout(ESPERA_BUSQUEDA)

        return frame.inner_text("body")

    def buscar_por_cedula(self, cedula):
        print("🔎 Buscando cédula:", cedula)
        return self._buscar(cedula)

    def buscar_por_nombre(self, nombre):
        print("🔎 Buscando nombre:", nombre)
        return self._buscar(nombre)

    def cerrar(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
