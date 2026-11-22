import streamlit as st
import streamlit.components.v1 as components
import math
import io
import re
import base64
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

try:
    from pypdf import PdfReader
    PDF_BESCHIKBAAR = True
except ImportError:
    PDF_BESCHIKBAAR = False

try:
    import pytesseract
    OCR_BESCHIKBAAR = True
except ImportError:
    OCR_BESCHIKBAAR = False

st.set_page_config(page_title="Fons Laadplan", layout="wide")
css_en_header = (
    "<st" + "yle>"
    ".block-container { padding-top: 1.5rem !important; }"
    "div[data-testid='stColumn'] { display: flex; flex-direction: column; }"
    ".custom-box { padding: 0.45rem; border-radius: 0.5rem; color: white; font-weight: bold; font-size: 13px; text-align: center; margin-bottom: 0.25rem; min-height: 43px; display: flex; align-items: center; justify-content: center; }"
    ".modern-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left: 6px solid #38bdf8; padding: 1.2rem 1.5rem; border-radius: 0.75rem; margin-top: 0.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25); }"
    ".modern-title { font-size: 2.1rem; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(90deg, #ffffff 0%, #38bdf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; line-height: 1.2; }"
    ".modern-subtitle { color: #94a3b8; font-size: 0.9rem; margin: 0.25rem 0 0 0; font-weight: 500; letter-spacing: 0.3px; }"
    "@media (min-width: 951px) { .alleen-mobiel { display: none !important; } }"
    "@media (max-width: 950px) { div[data-testid='stExpander']:has(div[data-testid='stFileUploader']), div[data-testid='stDownloadButton'] { display: none !important; } }"
    "@media (orientation: landscape) and (max-width: 950px) { .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; padding-top: 1rem !important; max-width: 100% !important; } header, [data-testid='stToolbar'] { display: none !important; } }"
    "#MainMenu, footer, header, [data-testid='stToolbar'], [data-testid='stHeader'], [data-testid='stDecoration'], [data-testid='stStatusWidget'], .stAppDeployButton, .stDeployButton { display: none !important; visibility: hidden !important; }"
    "</st" + "yle>"
    "<div class='modern-header'>"
    "<div class='modern-title'>FONS LAADPLAN <span style='font-weight:400; font-size:1.3rem;'>| 2.0</span></div>"
    "<div class='modern-subtitle'>Containerindeling &amp; live aslast-berekening</div>"
    "</div>"
)
st.markdown(css_en_header, unsafe_allow_html=True)
def verwerk_laadbon_tekst(volledige_tekst, is_foto=False):
    res = {
        "cp3_500": 0, "cp3_1000": 0, "cp7_600": 0, "cp7_750": 0, "ibc": 0,
        "totaal_gewicht": 0, "bon_totaal_pal": 0, "regels": [], "ruwe_tekst": volledige_tekst
    }
    regels = [r.upper().strip() for r in volledige_tekst.splitlines() if r.strip()]

    for r in regels:
        if "ITEMS TOTAL" in r or "ITEM TOTAL" in r or "TOTAAL" in r:
            tot_m = re.search(r'(\d+)\s*(?:PAL|PA[L1I])\b', r)
            if tot_m:
                res["bon_totaal_pal"] = int(tot_m.group(1))

    witte_res = {"cp3_500": 0, "cp3_1000": 0, "cp7_600": 0, "cp7_750": 0, "ibc": 0, "totaal_gewicht": 0, "regels": []}
    laatste_type = None

    for r in regels:
        if "ITEMS TOTAL" in r or "ITEM TOTAL" in r or "TOTAAL" in r:
            continue
        if "CNPE" in r or "IBC" in r:
            laatste_type = "IBC"
        elif any(c in r for c in ("CP-7", "CP7", "-NB", "-N8", "PA210", "1,4X1,2")):
            laatste_type = "CP7"
        elif any(c in r for c in ("-SB1", "-S81")):
            laatste_type = "CP3_1000"
        elif any(c in r for c in ("CP-3", "CP3", "-SB5", "-S85", "B580", "B382", "1,2X1,2")):
            laatste_type = "CP3_500"

        if re.search(r'PAL\s*/', r):
            continue

        pal_m = re.search(r'(?:^|[^\d])(\d{1,2})\s*(?:PAL|PA[L1I])\b', r)
        kg_m = re.search(r'([\d\.,]+)\s*KG\b', r)

        if pal_m and laatste_type:
            aantal_pal = int(pal_m.group(1))
            if aantal_pal <= 0 or aantal_pal > 60:
                continue
            gewicht_kg = 0
            if kg_m:
                try:
                    gewicht_kg = int(float(kg_m.group(1).replace(".", "").replace(",", ".")))
                except ValueError:
                    gewicht_kg = 0

            if laatste_type == "IBC":
                witte_res["ibc"] += aantal_pal
                witte_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 1000
                witte_res["regels"].append(f"{aantal_pal}x IBC")
            elif laatste_type == "CP7":
                kg_p = (gewicht_kg / aantal_pal) if gewicht_kg > 0 else 600
                if kg_p > 650:
                    witte_res["cp7_750"] += aantal_pal
                    witte_res["regels"].append(f"{aantal_pal}x CP7 750kg")
                else:
                    witte_res["cp7_600"] += aantal_pal
                    witte_res["regels"].append(f"{aantal_pal}x CP7 600kg")
                witte_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 600
            elif laatste_type == "CP3_1000":
                witte_res["cp3_1000"] += aantal_pal
                witte_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 1000
                witte_res["regels"].append(f"{aantal_pal}x CP3 1000kg")
            elif laatste_type == "CP3_500":
                kg_p = (gewicht_kg / aantal_pal) if gewicht_kg > 0 else 500
                if kg_p > 750 and "-SB5" not in r:
                    witte_res["cp3_1000"] += aantal_pal
                    witte_res["regels"].append(f"{aantal_pal}x CP3 1000kg")
                else:
                    witte_res["cp3_500"] += aantal_pal
                    witte_res["regels"].append(f"{aantal_pal}x CP3 500kg")
                witte_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 500

    witte_totaal = witte_res["cp3_500"] + witte_res["cp3_1000"] + witte_res["cp7_600"] + witte_res["cp7_750"] + witte_res["ibc"]
    if not is_foto or (witte_totaal > 0 and (res["bon_totaal_pal"] == 0 or witte_totaal == res["bon_totaal_pal"])):
        res.update(witte_res)
        return res
    kop_res = {"cp3_500": 0, "cp3_1000": 0, "cp7_600": 0, "cp7_750": 0, "ibc": 0, "totaal_gewicht": 0, "regels": []}
    for idx, r in enumerate(regels):
        if "ITEMS TOTAL" in r or "ITEM TOTAL" in r:
            continue
        kop_match = re.search(r'(\d+)\s*(?:PAL|PA[L1I])\s*/\s*([\d\.,]+)\s*KG', r)
        if not kop_match:
            continue
        aantal_pal = int(kop_match.group(1))
        try:
            gewicht_kg = int(float(kop_match.group(2).replace(".", "").replace(",", ".")))
        except ValueError:
            gewicht_kg = 0

        context = " ".join(regels[max(0, idx - 1):min(len(regels), idx + 3)])
        if "CNPE" in context or "IBC" in context:
            if gewicht_kg > 0 and gewicht_kg % 1000 == 0 and (gewicht_kg // 1000) > aantal_pal:
                aantal_pal = gewicht_kg // 1000
            kop_res["ibc"] += aantal_pal
            kop_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 1000
            kop_res["regels"].append(f"{aantal_pal}x IBC")
        elif "CP-7" in context or "CP7" in context or "-NB" in context or "-N8" in context or "1,4X1,2" in context:
            if gewicht_kg > 0:
                if gewicht_kg % 600 == 0 and abs(gewicht_kg / max(1, aantal_pal) - 600) > 100:
                    aantal_pal = gewicht_kg // 600
                elif gewicht_kg % 750 == 0 and abs(gewicht_kg / max(1, aantal_pal) - 750) > 100:
                    aantal_pal = gewicht_kg // 750
            kg_p = (gewicht_kg / aantal_pal) if gewicht_kg > 0 else 600
            if kg_p > 650:
                kop_res["cp7_750"] += aantal_pal
                kop_res["regels"].append(f"{aantal_pal}x CP7 750kg")
            else:
                kop_res["cp7_600"] += aantal_pal
                kop_res["regels"].append(f"{aantal_pal}x CP7 600kg")
            kop_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 600
        else:
            is_sb5 = any(c in context for c in ("-SB5", "-S85", "-SBS"))
            is_sb1 = any(c in context for c in ("-SB1", "-S81"))
            if gewicht_kg > 0:
                verwacht = 500 if is_sb5 else 1000
                if abs((gewicht_kg / max(1, aantal_pal)) - verwacht) > 150:
                    if is_sb5 and gewicht_kg % 500 == 0:
                        aantal_pal = gewicht_kg // 500
                    elif gewicht_kg % 1000 == 0:
                        aantal_pal = gewicht_kg // 1000
                    elif gewicht_kg % 500 == 0:
                        aantal_pal = gewicht_kg // 500
            if is_sb1 or (not is_sb5 and gewicht_kg > 0 and (gewicht_kg / max(1, aantal_pal)) > 750):
                kop_res["cp3_1000"] += aantal_pal
                kop_res["regels"].append(f"{aantal_pal}x CP3 1000kg")
                kop_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 1000
            else:
                kop_res["cp3_500"] += aantal_pal
                kop_res["regels"].append(f"{aantal_pal}x CP3 500kg")
                kop_res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 500

    kop_totaal = kop_res["cp3_500"] + kop_res["cp3_1000"] + kop_res["cp7_600"] + kop_res["cp7_750"] + kop_res["ibc"]
    res.update(kop_res if kop_totaal > witte_totaal else witte_res)
    return res
def lees_kaneka_bestand(bestand):
    naam = bestand.name.lower()
    ruwe_bytes = bestand.getvalue()
    volledige_tekst = ""

    if naam.endswith((".jpg", ".jpeg", ".png", ".heic", ".heif")):
        if not OCR_BESCHIKBAAR:
            return "GEEN_OCR"
        try:
            afbeelding = Image.open(io.BytesIO(ruwe_bytes))
            afbeelding = ImageOps.exif_transpose(afbeelding).convert("RGB")
            w, h = afbeelding.size
            if h > w:
                afbeelding = afbeelding.rotate(-90, expand=True)

            grijs = ImageOps.autocontrast(afbeelding.convert("L"))
            kandidaten = (
                pytesseract.image_to_string(afbeelding, config="--psm 6"),
                pytesseract.image_to_string(grijs, config="--psm 6"),
                pytesseract.image_to_string(afbeelding.rotate(180, expand=True), config="--psm 6"),
            )
            beste_res, beste_pal = None, -1
            for t in kandidaten:
                r = verwerk_laadbon_tekst(t, is_foto=True)
                tot = r["cp3_500"] + r["cp3_1000"] + r["cp7_600"] + r["cp7_750"] + r["ibc"]
                if tot > beste_pal:
                    beste_pal, beste_res = tot, r
            return beste_res
        except Exception:
            return "ONLEESBARE_FOTO"

    if PDF_BESCHIKBAAR:
        try:
            reader = PdfReader(io.BytesIO(ruwe_bytes))
            for pagina in reader.pages:
                volledige_tekst += "\n" + (pagina.extract_text() or "")
        except Exception:
            return "CORRUPT_PDF"

    if volledige_tekst.strip():
        return verwerk_laadbon_tekst(volledige_tekst, is_foto=False)
    return "GEEN_TEKST"

if "klik_volgorde" not in st.session_state: st.session_state.klik_volgorde = []
if "reset_id" not in st.session_state: st.session_state.reset_id = 0
if "pdf_data" not in st.session_state: st.session_state.pdf_data = None
if "laatste_pdf_naam" not in st.session_state: st.session_state.laatste_pdf_naam = ""

with st.expander("📄 Laadbon importeren (PDF of Foto) — Automatisch invullen & aslast optimaliseren", expanded=True):
    geupload_bestand = st.file_uploader(
        "Upload hier de Kaneka Loading List (digitale PDF of foto JPG/PNG/HEIC):",
        type=("pdf", "jpg", "jpeg", "png", "heic", "heif"),
        key=f"pdf_up_{st.session_state.reset_id}"
    )
    if geupload_bestand is not None and geupload_bestand.name != st.session_state.laatste_pdf_naam:
        data = lees_kaneka_bestand(geupload_bestand)
        if data == "CORRUPT_PDF":
            st.error("❌ Dit PDF-bestand is onvolledig opgeslagen. Kies een foto uit je fotorol of gebruik de originele PDF uit SAP.")
        elif data == "ONLEESBARE_FOTO":
            st.error("❌ Dit afbeeldingsformaat kon niet worden geopend. Zorg dat `pillow-heif` in `requirements.txt` staat of maak een screenshot van de foto en upload die.")
        elif data == "GEEN_TEKST":
            st.warning("⚠️ Deze PDF bevat alleen een afbeelding zonder tekstlaag. Upload de foto direct uit je fotorol.")
        elif data == "GEEN_OCR":
            st.warning("⚠️ Voeg `pytesseract` en `packages.txt` (`tesseract-ocr`) toe op GitHub om foto's te kunnen uitlezen.")
        else:
            st.session_state.pdf_data = data
            st.session_state.laatste_pdf_naam = geupload_bestand.name
            st.session_state.reset_id += 1
            st.rerun()

    if st.session_state.pdf_data:
        d = st.session_state.pdf_data
        gelezen_pal = d["cp3_500"] + d["cp3_1000"] + d["cp7_600"] + d["cp7_750"] + d["ibc"]
        if d["regels"]:
            st.success(f"✅ **Bon ingelezen ({gelezen_pal} PAL):** {' | '.join(d['regels'])} — **Totaal gewicht:** {d['totaal_gewicht']} kg")
            if d.get("bon_totaal_pal", 0) > 0 and gelezen_pal != d["bon_totaal_pal"]:
                st.warning(f"⚠️ Let op: op de bon staat onderaan **{d['bon_totaal_pal']} PAL**, maar er zijn **{gelezen_pal} PAL** herkend. Controleer even de ontbrekende regel.")
        else:
            st.warning("⚠️ Bestand gelezen, maar geen regels herkend. Maak een rechtere/scherpere foto of gebruik de SAP-PDF.")
        with st.expander("🔍 Bekijk uitgelezen tekst van de bon"):
            st.text(d.get("ruwe_tekst", ""))

st.write("### 1. Kies container / oplegger:")
container_type = st.selectbox(
    "1. Kies container:", 
    ("45ft Container / Bache (13550 x 2426 mm)", "40ft Container (12030 x 2350 mm)", "20ft Container (5898 x 2350 mm)"),
    label_visibility="collapsed"
)

max_lengte = 13550 if "45ft" in container_type else 12030 if "40ft" in container_type else 5898
max_breedte = 2426 if "45ft" in container_type else 2350
marge_achter = 100
effectieve_lengte = max_lengte - marge_achter

product_info = {
    "CP3": {"lengte": 1150, "breedte": 1150, "kleur": "#3498db", "stapelbaar": False, "label": "CP3", "gewicht": 500},
    "CP7_600": {"lengte": 1400, "breedte": 1100, "kleur": "#2ecc71", "stapelbaar": True, "label": "CP7 600", "gewicht": 600},
    "CP7_750": {"lengte": 1400, "breedte": 1150, "kleur": "#e74c3c", "stapelbaar": True, "label": "CP7 750", "gewicht": 750},
    "IBC": {"lengte": 1000, "breedte": 1200, "kleur": "#f1c40f", "stapelbaar": False, "label": "IBC", "gewicht": 1000},
    "Maatwerk": {"lengte": 1000, "breedte": 1000, "kleur": "#7f8c8d", "stapelbaar": False, "label": "Maatwerk", "gewicht": 500}
}

pdf_d = st.session_state.pdf_data
init_cp3 = (pdf_d["cp3_500"] + pdf_d["cp3_1000"]) if pdf_d else 0
init_cp7_600 = pdf_d["cp7_600"] if pdf_d else 0
init_cp7_750 = pdf_d["cp7_750"] if pdf_d else 0
init_ibc = pdf_d["ibc"] if pdf_d else 0

col_titel, col_wis = st.columns(2)
with col_titel: st.write("### 2. Vul aantal pallets in:")
with col_wis:
    if st.button("🗑️ Wis alles", type="primary", use_container_width=True, key="wis_alles_hoofd"):
        st.session_state.klik_volgorde = []
        st.session_state.pdf_data = None
        st.session_state.laatste_pdf_naam = ""
        st.session_state.reset_id += 1
        st.rerun()
    uitvloeren = st.radio(
        "Uitvloeren? (gehele lengte benutten):",
        ("Ja", "Nee"),
        horizontal=True,
        key=f"uitvloeren_{st.session_state.reset_id}"
    ) == "Ja"
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown('<div class="custom-box" style="background-color:#3498db;">CP3 (1150x1150)</div>', unsafe_allow_html=True)
    in_cp3 = st.number_input("Aantal CP3", min_value=0, value=init_cp3, step=1, key=f"cp3_{st.session_state.reset_id}", label_visibility="collapsed")
    pallets_cp3 = int(in_cp3) if in_cp3 is not None else 0
    if pallets_cp3 > 0:
        if "CP3" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("CP3")
        default_cp3_kg = 1000 if (pdf_d and pdf_d["cp3_1000"] > pdf_d["cp3_500"]) else 500
        cp3_kg_stuk = st.selectbox("Gewicht CP3:", (500, 1000), index=0 if default_cp3_kg == 500 else 1, format_func=lambda x: f"{x} kg/pal", key=f"cp3_kg_{st.session_state.reset_id}", label_visibility="collapsed")
        product_info["CP3"]["gewicht"] = cp3_kg_stuk

with col2:
    st.markdown('<div class="custom-box" style="background-color:#2ecc71;">CP7 600kg (1400x1100)</div>', unsafe_allow_html=True)
    in_cp7_600 = st.number_input("Aantal CP7 600", min_value=0, value=init_cp7_600, step=1, key=f"cp7_600_{st.session_state.reset_id}", label_visibility="collapsed")
    pallets_cp7_600_totaal = int(in_cp7_600) if in_cp7_600 is not None else 0

with col3:
    st.markdown('<div class="custom-box" style="background-color:#e74c3c;">CP7 750kg (1400x1150)</div>', unsafe_allow_html=True)
    in_cp7_750 = st.number_input("Aantal CP7 750", min_value=0, value=init_cp7_750, step=1, key=f"cp7_750_{st.session_state.reset_id}", label_visibility="collapsed")
    pallets_cp7_750_totaal = int(in_cp7_750) if in_cp7_750 is not None else 0

with col4:
    st.markdown('<div class="custom-box" style="background-color:#f1c40f; color:black;">IBC (1000x1200)</div>', unsafe_allow_html=True)
    in_ibc = st.number_input("Aantal IBC", min_value=0, value=init_ibc, step=1, key=f"ibc_{st.session_state.reset_id}", label_visibility="collapsed")
    pallets_ibc = int(in_ibc) if in_ibc is not None else 0
    if pallets_ibc > 0 and "IBC" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("IBC")

with col5:
    st.markdown('<div class="custom-box" style="background-color:#7f8c8d;">Maatwerk 📐</div>', unsafe_allow_html=True)
    in_mw = st.number_input("Aantal Maatwerk", min_value=0, value=0, step=1, key=f"mw_{st.session_state.reset_id}", label_visibility="collapsed")
    pallets_mw = int(in_mw) if in_mw is not None else 0
    if pallets_mw > 0:
        if "Maatwerk" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("Maatwerk")
        mw_L = st.number_input("L (mm):", min_value=1, value=1000, step=10, key=f"mw_l_{st.session_state.reset_id}") or 1000
        mw_B = st.number_input("B (mm):", min_value=1, value=1000, step=10, key=f"mw_b_{st.session_state.reset_id}") or 1000
        mw_kg = st.number_input("Gewicht (kg):", min_value=1, value=500, step=50, key=f"mw_kg_{st.session_state.reset_id}") or 500
        product_info["Maatwerk"]["lengte"] = mw_L
        product_info["Maatwerk"]["breedte"] = mw_B
        product_info["Maatwerk"]["gewicht"] = mw_kg

js_select = (
    "<sc" + "ript>"
    "const doc = window.parent.document;"
    "function selecteerBijKlik(e) {"
    "  if (e.target && e.target.tagName === 'INPUT' && (e.target.type === 'number' || e.target.inputMode === 'numeric')) {"
    "    setTimeout(() => { e.target.select(); }, 20);"
    "  }"
    "}"
    "doc.removeEventListener('focusin', selecteerBijKlik);"
    "doc.addEventListener('focusin', selecteerBijKlik);"
    "doc.removeEventListener('click', selecteerBijKlik);"
    "doc.addEventListener('click', selecteerBijKlik);"
    "</sc" + "ript>"
)
components.html(js_select, height=0, width=0)

handmatig_modus = False
if pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0:
    handmatig_modus = st.checkbox("🛠️ Handmatig aanpassen (zelf volgorde & voor/achter bepalen)", value=False)
auto_aslast = not handmatig_modus

as_v_cp3, as_a_cp3 = 0, 0
as_v_cp7_600, as_a_cp7_600 = 0, 0
as_v_cp7_750, as_a_cp7_750 = 0, 0
as_v_ibc, as_a_ibc = 0, 0
as_v_mw, as_a_mw = 0, 0

c_v_cp3, c_a_cp3 = False, False
c_v_cp7_600, c_a_cp7_600 = True, True
c_v_cp7_750, c_a_cp7_750 = True, True
c_v_ibc, c_a_ibc = False, False
c_v_mw, c_a_mw = False, False

richting_v_cp7_600 = "Lang (1400x1100)"
richting_a_cp7_600 = "Lang (1400x1100)"
richting_v_cp7_750 = "Lang (1400x1150)"
richting_a_cp7_750 = "Lang (1400x1150)"

if handmatig_modus and (pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0):
    with st.expander("⚖️ Handmatige plaatsing vooraan (VOR) / achteraan (ACH) per artikel", expanded=True):
        v_col1, v_col2, v_col3, v_col4, v_col5 = st.columns(5)
        with v_col1:
            if pallets_cp3 > 0:
                as_v_cp3 = st.number_input("CP3 VOR", min_value=0, max_value=pallets_cp3, value=0, step=1, key=f"v_cp3_{st.session_state.reset_id}") or 0
                if as_v_cp3 > 0:
                    c_v_cp3 = (st.radio("CP3 VOR plaatsing:", ("Naast elkaar", "Centraal"), key=f"cv_cp3_{st.session_state.reset_id}") == "Centraal")
                as_a_cp3 = st.number_input("CP3 ACH", min_value=0, max_value=pallets_cp3 - as_v_cp3, value=0, step=1, key=f"a_cp3_{st.session_state.reset_id}") or 0
                if as_a_cp3 > 0:
                    c_a_cp3 = (st.radio("CP3 ACH plaatsing:", ("Naast elkaar", "Centraal"), key=f"ca_cp3_{st.session_state.reset_id}") == "Centraal")
        with v_col2:
            if pallets_cp7_600_totaal > 0:
                as_v_cp7_600 = st.number_input("CP7 600 VOR", min_value=0, max_value=pallets_cp7_600_totaal, value=0, step=1, key=f"v_cp7_600_{st.session_state.reset_id}") or 0
                if as_v_cp7_600 > 0:
                    richting_v_cp7_600 = st.radio("Richting VOR (600):", ("Lang (1400x1100)", "Smal (1100x1400)"), key=f"r_v_cp7_600_{st.session_state.reset_id}")
                    c_v_cp7_600 = (st.radio("CP7 600 VOR plaatsing:", ("Centraal", "Naast elkaar"), key=f"cv_600_{st.session_state.reset_id}") == "Centraal")
                as_a_cp7_600 = st.number_input("CP7 600 ACH", min_value=0, max_value=pallets_cp7_600_totaal - as_v_cp7_600, value=0, step=1, key=f"a_cp7_600_{st.session_state.reset_id}") or 0
                if as_a_cp7_600 > 0:
                    richting_a_cp7_600 = st.radio("Richting ACH (600):", ("Lang (1400x1100)", "Smal (1100x1400)"), key=f"r_a_cp7_600_{st.session_state.reset_id}")
                    c_a_cp7_600 = (st.radio("CP7 600 ACH plaatsing:", ("Centraal", "Naast elkaar"), key=f"ca_600_{st.session_state.reset_id}") == "Centraal")
        with v_col3:
            if pallets_cp7_750_totaal > 0:
                as_v_cp7_750 = st.number_input("CP7 750 VOR", min_value=0, max_value=pallets_cp7_750_totaal, value=0, step=1, key=f"v_cp7_750_{st.session_state.reset_id}") or 0
                if as_v_cp7_750 > 0:
                    richting_v_cp7_750 = st.radio("Richting VOR (750):", ("Lang (1400x1150)", "Smal (1150x1400)"), key=f"r_v_cp7_750_{st.session_state.reset_id}")
                    c_v_cp7_750 = (st.radio("CP7 750 VOR plaatsing:", ("Centraal", "Naast elkaar"), key=f"cv_750_{st.session_state.reset_id}") == "Centraal")
                as_a_cp7_750 = st.number_input("CP7 750 ACH", min_value=0, max_value=pallets_cp7_750_totaal - as_v_cp7_750, value=0, step=1, key=f"a_cp7_750_{st.session_state.reset_id}") or 0
                if as_a_cp7_750 > 0:
                    richting_a_cp7_750 = st.radio("Richting ACH (750):", ("Lang (1400x1150)", "Smal (1150x1400)"), key=f"r_a_cp7_750_{st.session_state.reset_id}")
                    c_a_cp7_750 = (st.radio("CP7 750 ACH plaatsing:", ("Centraal", "Naast elkaar"), key=f"ca_750_{st.session_state.reset_id}") == "Centraal")
        with v_col4:
            if pallets_ibc > 0:
                as_v_ibc = st.number_input("IBC VOR", min_value=0, max_value=pallets_ibc, value=0, step=1, key=f"v_ibc_{st.session_state.reset_id}") or 0
                if as_v_ibc > 0:
                    c_v_ibc = (st.radio("IBC VOR plaatsing:", ("Naast elkaar", "Centraal"), key=f"cv_ibc_{st.session_state.reset_id}") == "Centraal")
                as_a_ibc = st.number_input("IBC ACH", min_value=0, max_value=pallets_ibc - as_v_ibc, value=0, step=1, key=f"a_ibc_{st.session_state.reset_id}") or 0
                if as_a_ibc > 0:
                    c_a_ibc = (st.radio("IBC ACH plaatsing:", ("Naast elkaar", "Centraal"), key=f"ca_ibc_{st.session_state.reset_id}") == "Centraal")
        with v_col5:
            if pallets_mw > 0:
                as_v_mw = st.number_input("MW VOR", min_value=0, max_value=pallets_mw, value=0, step=1, key=f"v_mw_{st.session_state.reset_id}") or 0
                if as_v_mw > 0:
                    c_v_mw = (st.radio("MW VOR plaatsing:", ("Naast elkaar", "Centraal"), key=f"cv_mw_{st.session_state.reset_id}") == "Centraal")
                as_a_mw = st.number_input("MW ACH", min_value=0, max_value=pallets_mw - as_v_mw, value=0, step=1, key=f"a_mw_{st.session_state.reset_id}") or 0
                if as_a_mw > 0:
                    c_a_mw = (st.radio("MW ACH plaatsing:", ("Naast elkaar", "Centraal"), key=f"ca_mw_{st.session_state.reset_id}") == "Centraal")
hoofd_cp7_600 = max(0, pallets_cp7_600_totaal - as_v_cp7_600 - as_a_cp7_600)
if pallets_cp7_600_totaal > 0 and "CP7_600" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("CP7_600")

hoofd_cp7_750 = max(0, pallets_cp7_750_totaal - as_v_cp7_750 - as_a_cp7_750)
if pallets_cp7_750_totaal > 0 and "CP7_750" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("CP7_750")

with col2:
    if pallets_cp7_600_totaal > 0 and not auto_aslast: st.write(f"➡️ **Gewone CP7 600 over:** {hoofd_cp7_600}")
with col3:
    if pallets_cp7_750_totaal > 0 and not auto_aslast: st.write(f"➡️ **Gewone CP7 750 over:** {hoofd_cp7_750}")

hoofd_cp3 = max(0, pallets_cp3 - as_v_cp3 - as_a_cp3)
hoofd_ibc = max(0, pallets_ibc - as_v_ibc - as_a_ibc)
hoofd_mw = max(0, pallets_mw - as_v_mw - as_a_mw)

laad_lijst = []

def haal_pallet_kleur(art_naam, overgebleven, standaard_kleur):
    if art_naam == "CP7_600":
        return "#1b5e20" if overgebleven >= 2 else "#2ecc71"
    elif art_naam == "CP7_750":
        return "#c0392b" if overgebleven >= 2 else "#ff7675"
    return standaard_kleur

def voeg_partij_toe_aslast(art_naam, aantal, richting, override_kg=None, centraal=True):
    if aantal > 0:
        info = product_info[art_naam].copy()
        stuk_kg = override_kg if override_kg is not None else info["gewicht"]
        if "Smal" in richting:
            info["lengte"], info["breedte"] = info["breedte"], info["lengte"]

        vloer = int(math.ceil(aantal / 2)) if info["stapelbaar"] else int(aantal)
        overgebleven = aantal
        for _ in range(vloer):
            aantal_op_vloer = 2 if (info["stapelbaar"] and overgebleven >= 2) else 1
            stapel_kg = aantal_op_vloer * stuk_kg
            h_label = " (2H)" if info["stapelbaar"] and overgebleven >= 2 else (" (1H)" if info["stapelbaar"] else "")
            gekozen_kleur = haal_pallet_kleur(art_naam, overgebleven, info["kleur"])
            overgebleven -= 2
            laad_lijst.append({
                "naam": f"{info['label']}{h_label}", "naam_puur": art_naam,
                "L": info["lengte"], "B": info["breedte"], "kleur": gekozen_kleur,
                "force_midden": centraal, "kg": stapel_kg
            })

def voeg_partij_toe(art_naam, aantal, dwars=False, override_kg=None):
    if aantal > 0:
        info = product_info[art_naam].copy()
        stuk_kg = override_kg if override_kg is not None else info["gewicht"]
        if dwars:
            info["lengte"], info["breedte"] = info["breedte"], info["lengte"]
        vloer = int(math.ceil(aantal / 2)) if info["stapelbaar"] else int(aantal)
        overgebleven = aantal
        for _ in range(vloer):
            aantal_op_vloer = 2 if (info["stapelbaar"] and overgebleven >= 2) else 1
            stapel_kg = aantal_op_vloer * stuk_kg
            h_label = " (2H)" if info["stapelbaar"] and overgebleven >= 2 else (" (1H)" if info["stapelbaar"] else "")
            gekozen_kleur = haal_pallet_kleur(art_naam, overgebleven, info["kleur"])
            overgebleven -= 2
            laad_lijst.append({
                "naam": f"{info['label']}{h_label}", "naam_puur": art_naam,
                "L": info["lengte"], "B": info["breedte"], "kleur": gekozen_kleur,
                "force_midden": False, "kg": stapel_kg
            })

if handmatig_modus:
    voor_items = (
        ("CP7_600", as_v_cp7_600, richting_v_cp7_600, c_v_cp7_600),
        ("CP7_750", as_v_cp7_750, richting_v_cp7_750, c_v_cp7_750),
        ("CP3", as_v_cp3, "Lang", c_v_cp3),
        ("IBC", as_v_ibc, "Lang", c_v_ibc),
        ("Maatwerk", as_v_mw, "Lang", c_v_mw),
    )
    for art, aantal, richt, is_centr in voor_items:
        if aantal > 0 and is_centr:
            voeg_partij_toe_aslast(art, aantal, richt, centraal=True)
    for art, aantal, richt, is_centr in voor_items:
        if aantal > 0 and not is_centr:
            voeg_partij_toe_aslast(art, aantal, richt, centraal=False)
rest_600 = hoofd_cp7_600
rest_750 = hoofd_cp7_750

if not handmatig_modus and rest_750 >= 36 and rest_600 == 0 and hoofd_cp3 == 0 and hoofd_ibc == 0 and max_lengte == 13550:
    voeg_partij_toe_aslast("CP7_750", 4, "Smal (1150x1400)", centraal=True)
    rest_750 -= 4
    voeg_partij_toe("CP7_750", rest_750)
elif not handmatig_modus and rest_600 >= 36 and rest_750 == 0 and hoofd_cp3 == 0 and hoofd_ibc == 0 and max_lengte == 13550:
    voeg_partij_toe_aslast("CP7_600", 4, "Smal (1100x1400)", centraal=True)
    rest_600 -= 4
    voeg_partij_toe("CP7_600", rest_600)
else:
    def bouw_auto_lijst(d_750, e_750, d_600, e_600, mix_600_op_750=0, dwars_600=0, dwars_750=0, dwars_1h_600=0):
        lijst = []
        # Nooit 2H en 1H tegelijk dwars mixen
        if dwars_600 > 0 or dwars_750 > 0:
            dwars_1h_600 = 0

        for _ in range(dwars_600):
            lijst.append({"naam": "CP7 600 (2H)", "naam_puur": "CP7_600", "L": 1100, "B": 1400, "kleur": "#1b5e20", "force_midden": True, "kg": 1200})
        for _ in range(dwars_750):
            lijst.append({"naam": "CP7 750 (2H)", "naam_puur": "CP7_750", "L": 1150, "B": 1400, "kleur": "#c0392b", "force_midden": True, "kg": 1500})
        for _ in range(dwars_1h_600):
            lijst.append({"naam": "CP7 600 (1H)", "naam_puur": "CP7_600", "L": 1100, "B": 1400, "kleur": "#2ecc71", "force_midden": True, "kg": 600})

        heeft_pdf_cp3 = pdf_d and (pdf_d["cp3_500"] + pdf_d["cp3_1000"] == pallets_cp3) and (hoofd_cp3 == pallets_cp3)
        cp3_licht = pdf_d["cp3_500"] if heeft_pdf_cp3 else (hoofd_cp3 if product_info["CP3"]["gewicht"] == 500 else 0)
        cp3_zwaar = pdf_d["cp3_1000"] if heeft_pdf_cp3 else (hoofd_cp3 if product_info["CP3"]["gewicht"] == 1000 else 0)

        # 1. Hoogste eerst: CP7 (2H) & mix
        for _ in range(d_600):
            lijst.append({"naam": "CP7 600 (2H)", "naam_puur": "CP7_600", "L": 1400, "B": 1100, "kleur": "#1b5e20", "force_midden": False, "kg": 1200})
        for _ in range(mix_600_op_750):
            lijst.append({"naam": "CP7 600 op 750", "naam_puur": "CP7_MIX", "L": 1400, "B": 1150, "kleur": "#c0392b", "force_midden": False, "kg": 1350})
        for _ in range(d_750):
            lijst.append({"naam": "CP7 750 (2H)", "naam_puur": "CP7_750", "L": 1400, "B": 1150, "kleur": "#c0392b", "force_midden": False, "kg": 1500})

        # 2. CP3 1000kg (mag zowel naast oneven CP7 2H als naast IBC aansluiten, maar nooit door elkaar met CP7 1H)
        dubbel_rij = d_600 + mix_600_op_750 + d_750
        for i_z in range(cp3_zwaar):
            is_laatste_oneven = (i_z == cp3_zwaar - 1) and ((dubbel_rij + cp3_zwaar) % 2 == 1) and (e_600 + e_750 > 0) and (hoofd_ibc == 0)
            lijst.append({"naam": "CP3", "naam_puur": "CP3", "L": 1150, "B": 1150, "kleur": "#3498db", "force_midden": is_laatste_oneven, "kg": 1000})

        # 3. CP7 (1H) — altijd strak bij elkaar, nooit door elkaar met CP3
        for _ in range(e_600):
            lijst.append({"naam": "CP7 600 (1H)", "naam_puur": "CP7_600", "L": 1400, "B": 1100, "kleur": "#2ecc71", "force_midden": False, "kg": 600})
        for _ in range(e_750):
            lijst.append({"naam": "CP7 750 (1H)", "naam_puur": "CP7_750", "L": 1400, "B": 1150, "kleur": "#ff7675", "force_midden": False, "kg": 750})

        # 4. Laagste pallets vóór IBC: CP3 500kg & Maatwerk
        for _ in range(cp3_licht):
            lijst.append({"naam": "CP3", "naam_puur": "CP3", "L": 1150, "B": 1150, "kleur": "#3498db", "force_midden": False, "kg": 500})
        for _ in range(hoofd_mw):
            mw_i = product_info["Maatwerk"]
            lijst.append({"naam": "Maatwerk", "naam_puur": "Maatwerk", "L": mw_i["lengte"], "B": mw_i["breedte"], "kleur": "#7f8c8d", "force_midden": False, "kg": mw_i["gewicht"]})

        # 5. IBC's altijd helemaal achteraan (tweede laadkaai)
        for _ in range(hoofd_ibc):
            lijst.append({"naam": "IBC", "naam_puur": "IBC", "L": 1000, "B": 1200, "kleur": "#f1c40f", "force_midden": False, "kg": 1000})

        return lijst




    def simuleer_lengte_trekas_zw(lijst):
        xo, xb, bo, bb, ibc_t, i = 0, 0, 0, 0, 0, 0
        hoogte_o, hoogte_b, hoogte_fouten = 0, 0, 0
        blokken = []
        while i < len(lijst):
            it = lijst[i]
            h_type = 2 if ("(2H)" in it["naam"] or "op 750" in it["naam"]) else (1 if "(1H)" in it["naam"] else 0)
            if it.get("force_midden"):
                start_x = max(xo, xb)
                blokken.append({"x_mid": start_x + (it["L"] / 2), "kg": it["kg"]})
                xo, xb = start_x + it["L"], start_x + it["L"]
                bo, bb, hoogte_o, hoogte_b = 0, 0, 0, 0
                i += 1
                continue
            if max_breedte == 2350 and it["naam_puur"] == "IBC" and (i + 1 < len(lijst) and lijst[i + 1]["naam_puur"] == "IBC"):
                if ibc_t % 2 == 0:
                    x1 = max(xo, xb) if ibc_t == 0 else xo
                    x2 = max(xo, xb) if ibc_t == 0 else xb
                    blokken.append({"x_mid": x1 + 500, "kg": it["kg"]})
                    blokken.append({"x_mid": x2 + 600, "kg": lijst[i + 1]["kg"]})
                    xo, xb = x1 + 1000, x2 + 1200
                    bo, bb = 1200, 1000
                else:
                    blokken.append({"x_mid": xo + 600, "kg": it["kg"]})
                    blokken.append({"x_mid": xb + 500, "kg": lijst[i + 1]["kg"]})
                    xo, xb = xo + 1200, xb + 1000
                    bo, bb = 1000, 1200
                hoogte_o, hoogte_b = 0, 0
                ibc_t += 1
                i += 2
                continue
            if xo <= xb:
                if xo < xb and (it["B"] + bb > max_breedte):
                    xo, bo, hoogte_o = xb, 0, 0
                if xo < xb and h_type > 0 and hoogte_b > 0 and h_type != hoogte_b:
                    hoogte_fouten += 1
                blokken.append({"x_mid": xo + (it["L"] / 2), "kg": it["kg"]})
                xo += it["L"]
                bo, hoogte_o = it["B"], h_type
            else:
                if xb < xo and (it["B"] + bo > max_breedte):
                    xb, bb, hoogte_b = xo, 0, 0
                if xb < xo and h_type > 0 and hoogte_o > 0 and h_type != hoogte_o:
                    hoogte_fouten += 1
                blokken.append({"x_mid": xb + (it["L"] / 2), "kg": it["kg"]})
                xb += it["L"]
                bb, hoogte_b = it["B"], h_type
            i += 1

        tot_len = max(xo, xb)
        tot_kg = sum(b["kg"] for b in blokken)
        if tot_kg == 0 or max_lengte != 13550:
            return tot_len, 0, 0, hoogte_fouten
        zw_mm = sum(b["x_mid"] * b["kg"] for b in blokken) / tot_kg
        aandeel_tr = max(0.0, min(1.25, (zw_mm - 1600) / (10200 - 1600)))
        schotel = 2000 + (tot_kg * (1.0 - aandeel_tr))
        trekas = round(2800 + (schotel * 0.72))
        return tot_len, trekas, zw_mm, hoogte_fouten
    achter_lijst = []
    if handmatig_modus:
        tijdelijk_laad = laad_lijst.copy()
        laad_lijst = []
        achter_items = (
            ("CP3", as_a_cp3, "Lang", c_a_cp3),
            ("CP7_600", as_a_cp7_600, richting_a_cp7_600, c_a_cp7_600),
            ("CP7_750", as_a_cp7_750, richting_a_cp7_750, c_a_cp7_750),
            ("IBC", as_a_ibc, "Lang", c_a_ibc),
            ("Maatwerk", as_a_mw, "Lang", c_a_mw),
        )
        for art, aantal, richt, is_centr in achter_items:
            if aantal > 0 and not is_centr:
                voeg_partij_toe_aslast(art, aantal, richt, centraal=False)
        for art, aantal, richt, is_centr in achter_items:
            if aantal > 0 and is_centr:
                voeg_partij_toe_aslast(art, aantal, richt, centraal=True)
        achter_lijst = laad_lijst
        laad_lijst = tijdelijk_laad

    def bereken_variant(dwars_600=0, dwars_750=0, mag_halveren=True):
        d6 = max(0, (rest_600 // 2) - dwars_600)
        e6 = rest_600 % 2
        d7 = max(0, (rest_750 // 2) - dwars_750)
        e7 = rest_750 % 2
        mix = 0

        if e6 == 1 and e7 == 1:
            zonder_mix = laad_lijst + bouw_auto_lijst(d7, e7, d6, e6, 0, dwars_600, dwars_750) + achter_lijst
            len_zonder, _, _, _ = simuleer_lengte_trekas_zw(zonder_mix)
            if len_zonder > effectieve_lengte:
                e6, e7, mix = 0, 0, 1

        if mag_halveren:
            while (d6 + d7) > 0:
                if d7 > 0:
                    kand = laad_lijst + bouw_auto_lijst(d7 - 1, e7 + 2, d6, e6, mix, dwars_600, dwars_750) + achter_lijst
                    k_len, _, _, _ = simuleer_lengte_trekas_zw(kand)
                    if k_len <= effectieve_lengte:
                        d7 -= 1
                        e7 += 2
                        continue
                if d6 > 0:
                    kand = laad_lijst + bouw_auto_lijst(d7, e7, d6 - 1, e6 + 2, mix, dwars_600, dwars_750) + achter_lijst
                    k_len, _, _, _ = simuleer_lengte_trekas_zw(kand)
                    if k_len <= effectieve_lengte:
                        d6 -= 1
                        e6 += 2
                        continue
                break

            heeft_voor = (as_v_cp7_600 + as_v_cp7_750 + as_v_cp3 + as_v_ibc + as_v_mw + dwars_600 + dwars_750) > 0
            if heeft_voor and (d7 + d6 + mix) % 2 == 1 and (e7 + e6) > 0:
                if e7 >= 2:
                    e7 -= 2
                    d7 += 1
                elif e6 >= 2:
                    e6 -= 2
                    d6 += 1

        return laad_lijst + bouw_auto_lijst(d7, e7, d6, e6, mix, dwars_600, dwars_750) + achter_lijst

    def bereken_variant(dwars_600=0, dwars_750=0, mag_halveren=True, dwars_1h_600=0):
        d6 = max(0, (rest_600 // 2) - dwars_600)
        e6 = rest_600 % 2
        d7 = max(0, (rest_750 // 2) - dwars_750)
        e7 = rest_750 % 2
        mix = 0

        if e6 == 1 and e7 == 1:
            zonder_mix = laad_lijst + bouw_auto_lijst(d7, e7, d6, e6, 0, dwars_600, dwars_750, 0) + achter_lijst
            len_zonder, _, _, _ = simuleer_lengte_trekas_zw(zonder_mix)
            if len_zonder > effectieve_lengte:
                e6, e7, mix = 0, 0, 1

        if mag_halveren:
            while (d6 + d7) > 0:
                if d7 > 0:
                    kand = laad_lijst + bouw_auto_lijst(d7 - 1, e7 + 2, d6, e6, mix, dwars_600, dwars_750, 0) + achter_lijst
                    k_len, _, _, _ = simuleer_lengte_trekas_zw(kand)
                    if k_len <= effectieve_lengte:
                        d7 -= 1
                        e7 += 2
                        continue
                if d6 > 0:
                    kand = laad_lijst + bouw_auto_lijst(d7, e7, d6 - 1, e6 + 2, mix, dwars_600, dwars_750, 0) + achter_lijst
                    k_len, _, _, _ = simuleer_lengte_trekas_zw(kand)
                    if k_len <= effectieve_lengte:
                        d6 -= 1
                        e6 += 2
                        continue
                break

            heeft_voor = (as_v_cp7_600 + as_v_cp7_750 + as_v_cp3 + as_v_ibc + as_v_mw + dwars_600 + dwars_750) > 0
            if heeft_voor and (d7 + d6 + mix) % 2 == 1 and (e7 + e6) > 0:
                if e7 >= 2:
                    e7 -= 2
                    d7 += 1
                elif e6 >= 2:
                    e6 -= 2
                    d6 += 1

        dw1 = min(e6, dwars_1h_600)
        e6 -= dw1
        return laad_lijst + bouw_auto_lijst(d7, e7, d6, e6, mix, dwars_600, dwars_750, dw1) + achter_lijst

    def score_kandidaat(lijst):
        k_len, k_trekas, k_zw, h_fouten = simuleer_lengte_trekas_zw(lijst)
        past = 1 if k_len <= effectieve_lengte else 0
        trekas_ok = 1 if k_trekas <= 11500 else 0
        tot_kg = sum(it["kg"] for it in lijst)
        aandeel_tr = max(0.0, min(1.25, (k_zw - 1600) / (10200 - 1600))) if k_zw > 0 else 0
        k_tridem = round(5200 + (tot_kg * aandeel_tr)) if max_lengte == 13550 else 0
        tridem_ok = 1 if k_tridem <= 24000 else 0
        lengte_score = (k_len // 300) if (uitvloeren and past == 1) else -k_len
        enkele_stuks = sum(1 for it in lijst if "(1H)" in it["naam"])
        zw_afwijking = abs(k_zw - 6900) if k_zw > 0 else 0
        return (past, -h_fouten, trekas_ok, tridem_ok, -enkele_stuks, lengte_score, -zw_afwijking)

    beste_lijst = bereken_variant(0, 0, mag_halveren=False)
    if uitvloeren:
        beste_score = score_kandidaat(beste_lijst)
        k_len_basis, _, _, _ = simuleer_lengte_trekas_zw(beste_lijst)
        if k_len_basis <= effectieve_lengte:
            heeft_handmatig_voor = (as_v_cp7_600 + as_v_cp7_750 + as_v_cp3 + as_v_ibc + as_v_mw) > 0
            if not heeft_handmatig_voor and max_lengte == 13550:
                max_dw6 = min(4, rest_600 // 2)
                max_dw7 = min(4, rest_750 // 2) if rest_600 == 0 else 0
                for dw6 in range(0, max_dw6 + 1):
                    for dw7 in range(0, max_dw7 + 1):
                        for halv in (False, True):
                            max_dw1 = 4 if (halv and rest_600 > 0) else 0
                            for dw1 in range(0, max_dw1 + 1):
                                if dw6 == 0 and dw7 == 0 and not halv and dw1 == 0:
                                    continue
                                kand = bereken_variant(dw6, dw7, mag_halveren=halv, dwars_1h_600=dw1)
                                sc = score_kandidaat(kand)
                                if sc > beste_score:
                                    beste_lijst = kand
                                    beste_score = sc

    laad_lijst = beste_lijst


fig, ax = plt.subplots(figsize=(15, 4.1))
ax.set_xlim(0, max_lengte)
ax.set_ylim(-650 if max_lengte == 13550 else -200, max_breedte + 180)
ax.set_aspect('equal', adjustable='box')
ax.axis('off')

container_border = patches.Rectangle((0, 0), max_lengte, max_breedte, linewidth=2, edgecolor='black', facecolor='none')
ax.add_patch(container_border)

ax.text(80, max_breedte + 45, "⬅️ KOPSCHOT (0 m)", ha="left", va="bottom", fontweight="bold", fontsize=9, color="#334155")
ax.text(max_lengte - 80, max_breedte + 45, f"DEUREN ({max_lengte / 1000:.2f} m) ➡️", ha="right", va="bottom", fontweight="bold", fontsize=9, color="#334155")
ax.plot((effectieve_lengte, effectieve_lengte), (0, max_breedte), color="#f59e0b", linestyle=":", linewidth=2)
ax.text(effectieve_lengte - 40, 40, "Min. 10 cm vrij", ha="right", va="bottom", fontsize=7.5, fontweight="bold", color="#d97706")

def teken_blok(x, y, lengte, breedte, item, kleur_override=None):
    if item.get("naam_puur") == "CP7_MIX" and kleur_override is None:
        driehoek_rood = patches.Polygon(
            [(x, y), (x + lengte, y), (x, y + breedte)],
            closed=True, linewidth=0, facecolor="#c0392b", alpha=0.9
        )
        driehoek_groen = patches.Polygon(
            [(x + lengte, y), (x + lengte, y + breedte), (x, y + breedte)],
            closed=True, linewidth=0, facecolor="#1b5e20", alpha=0.9
        )
        ax.add_patch(driehoek_rood)
        ax.add_patch(driehoek_groen)
        ax.plot((x, x + lengte), (y + breedte, y), color="white", linewidth=0.8, alpha=0.7)
        ax.add_patch(patches.Rectangle((x, y), lengte, breedte, linewidth=1.2, edgecolor='white', facecolor='none'))
    else:
        kleur = kleur_override if kleur_override else item["kleur"]
        ax.add_patch(patches.Rectangle((x, y), lengte, breedte, linewidth=1, edgecolor='white', facecolor=kleur, alpha=0.85))

geplaatste_blokken = []
x_onder, x_boven, ibc_paar_teller, idx = 0, 0, 0, 0
breedte_op_onder = 0
breedte_op_boven = 0
while idx < len(laad_lijst):
    item = laad_lijst[idx]
    tekst_grootte = 9

    if item["L"] <= 1200 and "CP7" in item["naam"]:
        basis_naam = item["naam"].replace(" 600", "").replace(" 750", "")
    else:
        basis_naam = item["naam"]
    tekst_weergave = f"{basis_naam}\n{item['kg']} kg"

    if item["force_midden"]:
        start_x = max(x_onder, x_boven)
        fout_kleur = "#ff0000" if (start_x + item["L"] > max_lengte or item["B"] > max_breedte) else None
        y_pos = (max_breedte - item["B"]) / 2
        teken_blok(start_x, y_pos, item["L"], item["B"], item, fout_kleur)
        ax.text(start_x + (item["L"]/2), y_pos + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        geplaatste_blokken.append({"x_mid": start_x + (item["L"] / 2), "kg": item["kg"]})
        x_onder, x_boven = start_x + item["L"], start_x + item["L"]
        breedte_op_onder, breedte_op_boven = 0, 0
        idx += 1
        continue

    if max_breedte == 2350 and item["naam_puur"] == "IBC":
        heeft_partner = (idx + 1 < len(laad_lijst) and laad_lijst[idx+1]["naam_puur"] == "IBC" and not laad_lijst[idx+1]["force_midden"])
        if heeft_partner:
            kg_1, kg_2 = item["kg"], laad_lijst[idx+1]["kg"]
            if ibc_paar_teller % 2 == 0:
                x_pos_onder = max(x_onder, x_boven) if ibc_paar_teller == 0 else x_onder
                vulling_kleur1 = "#ff0000" if (x_pos_onder + 1000 > max_lengte) else item["kleur"]
                ax.add_patch(patches.Rectangle((x_pos_onder, 20), 1000, 1200, linewidth=1, edgecolor='white', facecolor=vulling_kleur1, alpha=0.85))
                ax.text(x_pos_onder + 500, 20 + 600, f"IBC (Breed)\n{kg_1} kg", color="black", weight="bold", ha="center", va="center", fontsize=9.5)
                geplaatste_blokken.append({"x_mid": x_pos_onder + 500, "kg": kg_1})

                x_pos_boven = max(x_onder, x_boven) if ibc_paar_teller == 0 else x_boven
                vulling_kleur2 = "#ff0000" if (x_pos_boven + 1200 > max_lengte) else item["kleur"]
                ax.add_patch(patches.Rectangle((x_pos_boven, max_breedte - 1000 - 20), 1200, 1000, linewidth=1, edgecolor='white', facecolor=vulling_kleur2, alpha=0.85))
                ax.text(x_pos_boven + 600, max_breedte - 1000 - 20 + 500, f"IBC (Lang)\n{kg_2} kg", color="black", weight="bold", ha="center", va="center", fontsize=9.5)
                geplaatste_blokken.append({"x_mid": x_pos_boven + 600, "kg": kg_2})

                x_onder, x_boven = x_pos_onder + 1000, x_pos_boven + 1200
                breedte_op_onder, breedte_op_boven = 1200, 1000
            else:
                vulling_kleur1 = "#ff0000" if (x_onder + 1200 > max_lengte) else item["kleur"]
                ax.add_patch(patches.Rectangle((x_onder, 20), 1200, 1000, linewidth=1, edgecolor='white', facecolor=vulling_kleur1, alpha=0.85))
                ax.text(x_onder + 600, 20 + 500, f"IBC (Lang)\n{kg_1} kg", color="black", weight="bold", ha="center", va="center", fontsize=9.5)
                geplaatste_blokken.append({"x_mid": x_onder + 600, "kg": kg_1})

                vulling_kleur2 = "#ff0000" if (x_boven + 1000 > max_lengte) else item["kleur"]
                ax.add_patch(patches.Rectangle((x_boven, max_breedte - 1200 - 20), 1000, 1200, linewidth=1, edgecolor='white', facecolor=vulling_kleur2, alpha=0.85))
                ax.text(x_boven + 500, max_breedte - 1200 - 20 + 600, f"IBC (Breed)\n{kg_2} kg", color="black", weight="bold", ha="center", va="center", fontsize=9.5)
                geplaatste_blokken.append({"x_mid": x_boven + 500, "kg": kg_2})

                x_onder, x_boven = x_onder + 1200, x_boven + 1000
                breedte_op_onder, breedte_op_boven = 1000, 1200
            ibc_paar_teller += 1; idx += 2; continue

    if x_onder <= x_boven:
        if x_onder < x_boven and (item["B"] + breedte_op_boven > max_breedte):
            x_onder = x_boven
            breedte_op_onder = 0

        fout_kleur = "#ff0000" if (x_onder + item["L"] > max_lengte or item["B"] > max_breedte) else None
        teken_blok(x_onder, 20, item["L"], item["B"], item, fout_kleur)
        ax.text(x_onder + (item["L"]/2), 20 + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        geplaatste_blokken.append({"x_mid": x_onder + (item["L"] / 2), "kg": item["kg"]})
        x_onder += item["L"]
        breedte_op_onder = item["B"]
    else:
        if x_boven < x_onder and (item["B"] + breedte_op_onder > max_breedte):
            x_boven = x_onder
            breedte_op_boven = 0

        fout_kleur = "#ff0000" if (x_boven + item["L"] > max_lengte or item["B"] > max_breedte) else None
        teken_blok(x_boven, max_breedte - item["B"] - 20, item["L"], item["B"], item, fout_kleur)
        ax.text(x_boven + (item["L"]/2), max_breedte - item["B"] - 20 + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        geplaatste_blokken.append({"x_mid": x_boven + (item["L"] / 2), "kg": item["kg"]})
        x_boven += item["L"]
        breedte_op_boven = item["B"]
    idx += 1
totaal_lading_kg = sum(b["kg"] for b in geplaatste_blokken)
zwaartepunt_mm = (sum(b["x_mid"] * b["kg"] for b in geplaatste_blokken) / totaal_lading_kg) if totaal_lading_kg > 0 else 0

if max_lengte == 13550:
    kingpin_x = 1600
    tridem_x = 10200
    ax.plot((kingpin_x, kingpin_x), (-320, 0), color="#0284c7", linewidth=3)
    ax.add_patch(patches.Circle((kingpin_x, -380), 140, facecolor="#0284c7", edgecolor="white"))
    ax.text(kingpin_x, -560, "TREKAS / SCHOTEL\n(1,60 m)", ha="center", va="top", fontsize=8.5, fontweight="bold", color="#0284c7")

    for as_offset in (-1310, 0, 1310):
        ax.plot((tridem_x + as_offset, tridem_x + as_offset), (-320, 0), color="#475569", linewidth=2.5)
        ax.add_patch(patches.Circle((tridem_x + as_offset, -380), 130, facecolor="#475569", edgecolor="white"))
    ax.text(tridem_x, -560, "TRIDEMSTEL (3 ASSEN)\n(10,20 m)", ha="center", va="top", fontsize=8.5, fontweight="bold", color="#475569")

    if totaal_lading_kg > 0:
        ax.plot((zwaartepunt_mm, zwaartepunt_mm), (0, max_breedte), color="#dc2626", linestyle="--", linewidth=2.2)
        ax.text(zwaartepunt_mm, max_breedte + 35, f"⚖️ Zwaartepunt: {zwaartepunt_mm / 1000:.2f} m", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#dc2626", bbox=dict(boxstyle="round,pad=0.2", facecolor="#fef2f2", edgecolor="#dc2626"))

totale_meters = max(x_onder, x_boven)
restruimte = max_lengte - totale_meters
st.write("### 3. Plan & Aslast-controle:")
if pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0 or as_v_cp3 + as_v_cp7_600 + as_v_cp7_750 + as_v_ibc + as_v_mw + as_a_cp3 + as_a_cp7_600 + as_a_cp7_750 + as_a_ibc + as_a_mw > 0:
    if restruimte >= marge_achter:
        st.success(f"✅ Past! Nog {restruimte} mm over (incl. {marge_achter} mm marge) — **Totaal gewicht lading:** {totaal_lading_kg} kg")
    elif restruimte >= 0:
        st.warning(f"⚠️ Te krap! Nog maar {restruimte} mm over (minder dan de vereiste {marge_achter} mm marge) — **Totaal gewicht lading:** {totaal_lading_kg} kg")
    else:
        st.error(f"❌ Past NIET! {abs(restruimte)} mm tekort — **Totaal gewicht lading:** {totaal_lading_kg} kg")
    st.pyplot(fig, use_container_width=True)
    if max_lengte == 13550 and totaal_lading_kg > 0:
        trekas_leeg, schotel_leeg, tridem_leeg = 2800, 2000, 5200
        afstand_assen = 10200 - 1600
        aandeel_tridem = max(0.0, min(1.25, (zwaartepunt_mm - 1600) / afstand_assen))
        schotel_druk = schotel_leeg + (totaal_lading_kg * (1.0 - aandeel_tridem))
        belasting_trekas = round(trekas_leeg + (schotel_druk * 0.72))
        belasting_tridem = round(tridem_leeg + (totaal_lading_kg * aandeel_tridem))

        ac1, ac2, ac3 = st.columns(3)
        ac1.metric("⚖️ Zwaartepunt lading", f"{zwaartepunt_mm / 1000:.2f} m", "Ideaal: 6,20 m – 7,60 m vanaf kopschot")
        ac2.metric(
            "🚛 Trekas trekker (max 11.500 kg)",
            f"{belasting_trekas} kg",
            "✅ Binnen limiet" if belasting_trekas <= 11500 else f"⚠️ +{belasting_trekas - 11500} kg te zwaar!",
            delta_color="normal" if belasting_trekas <= 11500 else "inverse"
        )
        ac3.metric(
            "🛞 Tridemstel trailer (max 24.000 kg)",
            f"{belasting_tridem} kg",
            "✅ Binnen limiet" if belasting_tridem <= 24000 else f"⚠️ +{belasting_tridem - 24000} kg te zwaar!",
            delta_color="normal" if belasting_tridem <= 24000 else "inverse"
        )

    st.write(f"**Geladen:** {totale_meters} mm van {max_lengte} mm.")
    st.write("💡 **Legenda:** Blauw=CP3 | Groen=CP7 600kg | Rood=CP7 750kg | Geel=IBC | Grijs=Maatwerk | FELROOD=Past Niet")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    png_bytes = buf.getvalue()
    b64_img = base64.b64encode(png_bytes).decode()

    st.download_button(label="📸 Download Laadplan (Afbeelding)", data=png_bytes, file_name="fons_laadplan.png", mime="image/png")

    fs_html = (
        "<st" + "yle>body { margin: 0; padding: 0; background: transparent; font-family: sans-serif; } @media (min-width: 951px) { #fs-btn { display: none; } }</st" + "yle>"
        "<button id='fs-btn' style='width: 100%; padding: 14px 16px; border-radius: 10px; border: none; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; font-weight: 700; font-size: 16px; cursor: pointer; box-shadow: 0 3px 10px rgba(0,0,0,0.25);'>🔍 Groot scherm</button>"
        "<sc" + "ript>"
        f"const b64 = '{b64_img}';"
        "document.getElementById('fs-btn').addEventListener('click', function() {"
        "  const pDoc = window.parent.document;"
        "  let oud = pDoc.getElementById('fons-fs-overlay');"
        "  if (oud) oud.remove();"
        "  let overlay = pDoc.createElement('div');"
        "  overlay.id = 'fons-fs-overlay';"
        "  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:#0f172a;z-index:2147483647;display:flex;align-items:center;justify-content:center;padding:10px;box-sizing:border-box;';"
        "  overlay.addEventListener('click', function() { overlay.remove(); });"
        "  let hint = pDoc.createElement('div');"
        "  hint.innerText = '👆 Tik op het scherm om terug te keren';"
        "  hint.style.cssText = 'position:fixed;bottom:14px;left:50%;transform:translateX(-50%);background:rgba(15,23,42,0.9);color:#f8fafc;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:600;border:1px solid #38bdf8;z-index:2147483647;pointer-events:none;white-space:nowrap;';"
        "  let img = pDoc.createElement('img');"
        "  img.src = 'data:image/png;base64,' + b64;"
        "  img.style.cssText = 'max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;background:white;border-radius:8px;padding:6px;box-shadow:0 8px 30px rgba(0,0,0,0.6);';"
        "  overlay.appendChild(img);"
        "  overlay.appendChild(hint);"
        "  pDoc.body.appendChild(overlay);"
        "});"
        "</sc" + "ript>"
    )
    components.html(fs_html, height=56)
else:
    st.info("Container is leeg. Upload een PDF/foto-laadbon of gebruik de + en - knoppen om te beginnen.")

st.divider()
with st.expander("📋 Laatste updates & verbeteringen", expanded=False):
    st.markdown("""
    * **22-11-2026:**
        * **Keuze 'Uitvloeren' (Ja/Nee):** Kies voor *Ja* om de volledige vloerlengte te benutten, of *Nee* om alles compact 2-hoog te stapelen zodat er ruimte overblijft om later bij te laden.
        * **Minimaal 10 cm marge achteraan:** Het laadplan houdt nu standaard 10 cm (100 mm) vrij bij de deuren zodat alles zeker past.
    * **Versie 2.0 (Eerdere verbeteringen):**
        * **Laadbon scannen (PDF & foto):** Upload een Kaneka Loading List (ook iPhone-foto's) om aantallen en gewichten automatisch in te vullen.
        * **Live aslast- & zwaartepuntcontrole (45ft):** Directe controle of de belasting op de trekas (max. 11.500 kg) en het tridemstel (max. 24.000 kg) binnen de limiet blijft.
        * **Slim combineren & plaatsen:** Automatisch combineren van CP7 600 op CP7 750 en slim draaien van pallets voor een optimale verdeling.
        * **Handmatig aanpassen (VOR/ACH):** Zelf bepalen welke pallets vooraan of achteraan komen te staan.
        * **Groot scherm op mobiel:** Tik op *🔍 Groot scherm* om het laadplan schermvullend op je telefoon te bekijken.
    """)
