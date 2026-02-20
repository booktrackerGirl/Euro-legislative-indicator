import requests
import fitz
import pytesseract
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
import time


# ============================================================
# Timeout Wrapper (Safe on Windows)
# ============================================================

def run_with_timeout(func, args=(), timeout=90):
    result = [None]

    def target():
        try:
            result[0] = func(*args)
        except Exception:
            result[0] = None

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return None

    return result[0]


# ============================================================
# Advanced Safe Request (Anti-bot aware)
# ============================================================

def smart_get(url, timeout=30):

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/html,application/pdf,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

    try:
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=timeout)

        if r.status_code == 200:
            return r

        # Retry once with referer (anti-bot bypass trick)
        headers["Referer"] = url
        r = session.get(url, headers=headers, timeout=timeout)

        if r.status_code == 200:
            return r

        return None

    except:
        return None


# ============================================================
#                     ADVANCED PDF EXTRACTOR
# ============================================================

class PDFExtractor:

    def __init__(self):

        self.methods = [
            ("Climate Laws Optimized", self._climate_laws_handler),
            ("Direct PDF", self._handle_pdf),
            ("HTML Page", self._handle_html),
            ("Hostile Portal Fallback", self._hostile_portal_handler),
            ("JS Render Fallback", self._js_render_handler),
        ]


    # ============================================================
    # PUBLIC ENTRY
    # ============================================================

    def extract(self, url):

        for name, method in self.methods:
            print(f"→ Trying {name}")

            result = run_with_timeout(method, args=(url,), timeout=120)

            if result and isinstance(result, dict):
                text = result.get("text", "")
                if text and len(text.strip()) > 500:
                    print(f"✔ Success via {name}")
                    return result

        print("❌ Processing failed")
        return None


    # ============================================================
    # 1️⃣ CLIMATE-LAWS OPTIMIZED
    # ============================================================

    def _climate_laws_handler(self, url):

        if "climate-laws.org" not in url:
            return None

        r = smart_get(url)
        if not r:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        # Climate-laws always stores PDF in S3
        for link in soup.find_all("a", href=True):
            if "amazonaws.com" in link["href"] and ".pdf" in link["href"].lower():
                pdf_url = link["href"]
                return self._handle_pdf(pdf_url)

        return None


    # ============================================================
    # 2️⃣ PDF HANDLER (Embedded + Controlled OCR)
    # ============================================================

    def _handle_pdf(self, url):

        r = smart_get(url)
        if not r:
            return None

        if not r.content.startswith(b"%PDF"):
            return None

        pdf_bytes = r.content

        # Embedded text first
        embedded = self._extract_embedded(pdf_bytes)

        if embedded and len(embedded.strip()) > 1500:
            return {
                "text": embedded.strip(),
                "metadata": {"source": "embedded_pdf"}
            }

        # Controlled OCR fallback
        ocr = self._controlled_ocr(pdf_bytes)

        if ocr and len(ocr.strip()) > 800:
            return {
                "text": ocr.strip(),
                "metadata": {"source": "ocr_pdf"}
            }

        return None


    # ============================================================
    # 3️⃣ EMBEDDED TEXT
    # ============================================================

    def _extract_embedded(self, pdf_bytes):

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            text = []
            for page in doc:
                text.append(page.get_text())

            doc.close()
            return "\n".join(text)

        except:
            return ""


    # ============================================================
    # 4️⃣ CONTROLLED OCR (NO MEMORY SPIKE)
    # ============================================================

    def _controlled_ocr(self, pdf_bytes):

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            page_count = len(doc)

            MAX_PAGES = 15
            DPI = 150

            pages_to_ocr = min(page_count, MAX_PAGES)

            ocr_parts = []

            for i in range(pages_to_ocr):

                page = doc[i]
                pix = page.get_pixmap(dpi=DPI)

                img = Image.open(BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img)

                ocr_parts.append(text)

                img.close()
                del img
                del pix

            doc.close()

            return "\n".join(ocr_parts)

        except:
            return ""


    # ============================================================
    # 5️⃣ HTML HANDLER
    # ============================================================

    def _handle_html(self, url):

        r = smart_get(url)
        if not r:
            return None

        if r.content.startswith(b"%PDF"):
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        # Look for embedded PDF
        for link in soup.find_all("a", href=True):
            if ".pdf" in link["href"].lower():
                pdf_url = urljoin(url, link["href"])
                return self._handle_pdf(pdf_url)

        text = soup.get_text(separator="\n")

        if text and len(text.strip()) > 1000:
            return {
                "text": text.strip(),
                "metadata": {"source": "html_page"}
            }

        return None


    # ============================================================
    # 6️⃣ HOSTILE PORTAL FALLBACK
    # ============================================================

    def _hostile_portal_handler(self, url):

        # Last resort attempt
        time.sleep(2)  # mimic human delay

        r = smart_get(url)
        if not r:
            return None

        # Some portals hide PDF in scripts
        if "pdf" in r.text.lower():

            soup = BeautifulSoup(r.text, "html.parser")

            for link in soup.find_all("a", href=True):
                if ".pdf" in link["href"].lower():
                    pdf_url = urljoin(url, link["href"])
                    return self._handle_pdf(pdf_url)

        return None
    
    # ============================================================
    # 7️⃣ GENERIC JS RENDER FALLBACK (SAFE + LIGHTWEIGHT)
    # ============================================================

    def _js_render_handler(self, url):

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)  # allow JS to render

                content = page.content()
                browser.close()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")

            text = soup.get_text(separator="\n")

            if text and len(text.strip()) > 1000:
                return {
                    "text": text.strip(),
                    "metadata": {"source": "js_rendered"}
                }

            return None

        except Exception as e:
            print(f"JS render failed: {e}")
            return None

