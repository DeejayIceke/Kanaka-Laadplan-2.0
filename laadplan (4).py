import streamlit as st
import math
import io
import re
import importlib
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

st.markdown("""
    <style>
        .block-container { padding-top: 3.5rem !important; }
        div[data-testid="stColumn"] { display: flex; flex-direction: column; }
        .custom-box {
            padding: 0.45rem; border-radius: 0.5rem; color: white; font-weight: bold; 
            font-size: 13px; text-align: center; margin-bottom: 0.25rem;
            min-height: 43px; display: flex; align-items: center; justify-content: center;
        }
        .modern-header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-left: 6px solid #38bdf8;
            padding: 1.2rem 1.5rem;
            border-radius: 0.75rem;
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
        }
        .modern-title {
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #ffffff 0%, #38bdf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            line-height: 1.2;
        }
        .modern-subtitle {
            color: #94a3b8;
            font-size: 0.9rem;
            margin: 0.25rem 0 0 0;
            font-weight: 500;
            letter-spacing: 0.3px;
        }
        @media (orientation: landscape) and (max-width: 950px) {
            .block-container {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                padding-top: 1rem !important;
                max-width: 100% !important;
            }
            header, [data-testid="stToolbar"] {
                display: none !important;
            }
        }
    </style>
    <div class="modern-header">
        <div class="modern-title">FONS LAADPLAN <span style="font-weight:400; font-size:1.3rem;">| 2.0</span></div>
        <div class="modern-subtitle">Slimme containerindeling, Laadbon import (PDF &amp; Foto) &amp; live aslast-berekening</div>
    </div>
""", unsafe_allow_html=True)
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
        elif any(c in r for c in ["CP-7", "CP7", "-NB", "-N8", "PA210", "1,4X1,2"]):
            laatste_type = "CP7"
        elif any(c in r for c in ["-SB1", "-S81"]):
            laatste_type = "CP3_1000"
        elif any(c in r for c in ["CP-3", "CP3", "-SB5", "-S85", "B580", "B382", "1,2X1,2"]):
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
            is_sb5 = any(c in context for c in ["-SB5", "-S85", "-SBS"])
            is_sb1 = any(c in context for c in ["-SB1", "-S81"])
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
            kandidaten = [
                pytesseract.image_to_string(afbeelding, config="--psm 6"),
                pytesseract.image_to_string(grijs, config="--psm 6"),
                pytesseract.image_to_string(afbeelding.rotate(180, expand=True), config="--psm 6"),
            ]
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
        type=["pdf", "jpg", "jpeg", "png", "heic", "heif"],
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
    ["45ft Container / Bache (13550 x 2426 mm)", "40ft Container (12030 x 2350 mm)", "20ft Container (5898 x 2350 mm)"],
    label_visibility="collapsed"
)

max_lengte = 13550 if "45ft" in container_type else 12030 if "40ft" in container_type else 5898
max_breedte = 2426 if "45ft" in container_type else 2350
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
    if st.button("🗑️ Wis alles", type="primary", use_container_width=True):
        st.session_state.klik_volgorde = []
        st.session_state.pdf_data = None
        st.session_state.laatste_pdf_naam = ""
        st.session_state.reset_id += 1
        st.rerun()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown('<div class="custom-box" style="background-color:#3498db;">CP3 (1150x1150)</div>', unsafe_allow_html=True)
    pallets_cp3 = st.number_input("Aantal CP3", min_value=0, value=init_cp3, step=1, key=f"cp3_{st.session_state.reset_id}", label_visibility="collapsed")
    if pallets_cp3 > 0:
        if "CP3" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("CP3")
        default_cp3_kg = 1000 if (pdf_d and pdf_d["cp3_1000"] > pdf_d["cp3_500"]) else 500
        cp3_kg_stuk = st.selectbox("Gewicht CP3:", [500, 1000], index=0 if default_cp3_kg == 500 else 1, format_func=lambda x: f"{x} kg/pal", key=f"cp3_kg_{st.session_state.reset_id}", label_visibility="collapsed")
        product_info["CP3"]["gewicht"] = cp3_kg_stuk

with col2:
    st.markdown('<div class="custom-box" style="background-color:#2ecc71;">CP7 600kg (1400x1100)</div>', unsafe_allow_html=True)
    pallets_cp7_600_totaal = st.number_input("Aantal CP7 600", min_value=0, value=init_cp7_600, step=1, key=f"cp7_600_{st.session_state.reset_id}", label_visibility="collapsed")

with col3:
    st.markdown('<div class="custom-box" style="background-color:#e74c3c;">CP7 750kg (1400x1150)</div>', unsafe_allow_html=True)
    pallets_cp7_750_totaal = st.number_input("Aantal CP7 750", min_value=0, value=init_cp7_750, step=1, key=f"cp7_750_{st.session_state.reset_id}", label_visibility="collapsed")

with col4:
    st.markdown('<div class="custom-box" style="background-color:#f1c40f; color:black;">IBC (1000x1200)</div>', unsafe_allow_html=True)
    pallets_ibc = st.number_input("Aantal IBC", min_value=0, value=init_ibc, step=1, key=f"ibc_{st.session_state.reset_id}", label_visibility="collapsed")
    if pallets_ibc > 0 and "IBC" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("IBC")

with col5:
    st.markdown('<div class="custom-box" style="background-color:#7f8c8d;">Maatwerk 📐</div>', unsafe_allow_html=True)
    pallets_mw = st.number_input("Aantal Maatwerk", min_value=0, value=0, step=1, key=f"mw_{st.session_state.reset_id}", label_visibility="collapsed")
    if pallets_mw > 0:
        if "Maatwerk" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("Maatwerk")
        mw_L = st.number_input("L (mm):", min_value=1, value=1000, step=10, key=f"mw_l_{st.session_state.reset_id}")
        mw_B = st.number_input("B (mm):", min_value=1, value=1000, step=10, key=f"mw_b_{st.session_state.reset_id}")
        mw_kg = st.number_input("Gewicht (kg):", min_value=1, value=500, step=50, key=f"mw_kg_{st.session_state.reset_id}")
        product_info["Maatwerk"]["lengte"] = mw_L
        product_info["Maatwerk"]["breedte"] = mw_B
        product_info["Maatwerk"]["gewicht"] = mw_kg

auto_aslast = False
if pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0:
    auto_aslast = st.checkbox("⚖️ Automatisch optimaliseren op aslast & oppervlakte (alleen vooraan dwars als dit past in de lengte)", value=(pdf_d is not None))

as_v_cp3, as_a_cp3 = 0, 0
as_v_cp7_600, as_a_cp7_600 = 0, 0
as_v_cp7_750, as_a_cp7_750 = 0, 0
as_v_ibc, as_a_ibc = 0, 0
as_v_mw, as_a_mw = 0, 0
handmatig_centraal = False

richting_v_cp7_600 = "Lang (1400x1100)"
richting_a_cp7_600 = "Lang (1400x1100)"
richting_v_cp7_750 = "Lang (1400x1150)"
richting_a_cp7_750 = "Lang (1400x1150)"

if not auto_aslast and (pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0):
    with st.expander("⚖️ Klik hier voor handmatige plaatsing vooraan (VOR) / achteraan (ACH)"):
        plaatsing_keuze = st.radio(
            "Hoe wil je de pallets onder VOR / ACH plaatsen?",
            ["Naast elkaar (2 rijen)", "Centraal in het midden"],
            horizontal=True,
            key=f"pl_keuze_{st.session_state.reset_id}"
        )
        handmatig_centraal = (plaatsing_keuze == "Centraal in het midden")

        v_col1, v_col2, v_col3, v_col4, v_col5 = st.columns(5)
        with v_col1:
            if pallets_cp3 > 0:
                as_v_cp3 = st.number_input("CP3 VOR", min_value=0, max_value=pallets_cp3, value=0, step=1, key=f"v_cp3_{st.session_state.reset_id}")
                as_a_cp3 = st.number_input("CP3 ACH", min_value=0, max_value=pallets_cp3 - as_v_cp3, value=0, step=1, key=f"a_cp3_{st.session_state.reset_id}")
        with v_col2:
            if pallets_cp7_600_totaal > 0:
                as_v_cp7_600 = st.number_input("CP7 600 VOR", min_value=0, max_value=pallets_cp7_600_totaal, value=0, step=1, key=f"v_cp7_600_{st.session_state.reset_id}")
                if as_v_cp7_600 > 0:
                    richting_v_cp7_600 = st.radio("Richting VOR (600):", ["Lang (1400x1100)", "Smal (1100x1400)"], key=f"r_v_cp7_600_{st.session_state.reset_id}")
                as_a_cp7_600 = st.number_input("CP7 600 ACH", min_value=0, max_value=pallets_cp7_600_totaal - as_v_cp7_600, value=0, step=1, key=f"a_cp7_600_{st.session_state.reset_id}")
                if as_a_cp7_600 > 0:
                    richting_a_cp7_600 = st.radio("Richting ACH (600):", ["Lang (1400x1100)", "Smal (1100x1400)"], key=f"r_a_cp7_600_{st.session_state.reset_id}")
        with v_col3:
            if pallets_cp7_750_totaal > 0:
                as_v_cp7_750 = st.number_input("CP7 750 VOR", min_value=0, max_value=pallets_cp7_750_totaal, value=0, step=1, key=f"v_cp7_750_{st.session_state.reset_id}")
                if as_v_cp7_750 > 0:
                    richting_v_cp7_750 = st.radio("Richting VOR (750):", ["Lang (1400x1150)", "Smal (1150x1400)"], key=f"r_v_cp7_750_{st.session_state.reset_id}")
                as_a_cp7_750 = st.number_input("CP7 750 ACH", min_value=0, max_value=pallets_cp7_750_totaal - as_v_cp7_750, value=0, step=1, key=f"a_cp7_750_{st.session_state.reset_id}")
                if as_a_cp7_750 > 0:
                    richting_a_cp7_750 = st.radio("Richting ACH (750):", ["Lang (1400x1150)", "Smal (1150x1400)"], key=f"r_a_cp7_750_{st.session_state.reset_id}")
        with v_col4:
            if pallets_ibc > 0:
                as_v_ibc = st.number_input("IBC VOR", min_value=0, max_value=pallets_ibc, value=0, step=1, key=f"v_ibc_{st.session_state.reset_id}")
                as_a_ibc = st.number_input("IBC ACH", min_value=0, max_value=pallets_ibc - as_v_ibc, value=0, step=1, key=f"a_ibc_{st.session_state.reset_id}")
        with v_col5:
            if pallets_mw > 0:
                as_v_mw = st.number_input("MW VOR", min_value=0, max_value=pallets_mw, value=0, step=1, key=f"v_mw_{st.session_state.reset_id}")
                as_a_mw = st.number_input("MW ACH", min_value=0, max_value=pallets_mw - as_v_mw, value=0, step=1, key=f"a_mw_{st.session_state.reset_id}")
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
actuele_aantallen = {"CP3": hoofd_cp3, "CP7_600": hoofd_cp7_600, "CP7_750": hoofd_cp7_750, "IBC": hoofd_ibc, "Maatwerk": hoofd_mw}

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

if auto_aslast:
    rest_600 = pallets_cp7_600_totaal
    rest_750 = pallets_cp7_750_totaal

    vloer_600 = math.ceil(rest_600 / 2)
    vloer_750 = math.ceil(rest_750 / 2)
    totaal_cp7_vloer = vloer_600 + vloer_750

    lengte_cp7_normaal = math.ceil(totaal_cp7_vloer / 2) * 1400
    lengte_cp3_normaal = math.ceil(pallets_cp3 / 2) * 1150
    lengte_ibc_normaal = math.ceil(pallets_ibc / 2) * (1100 if max_breedte == 2350 else 1000)
    lengte_mw_normaal = math.ceil(pallets_mw / 2) * product_info["Maatwerk"]["lengte"]
    geschatte_lengte_normaal = lengte_cp7_normaal + lengte_cp3_normaal + lengte_ibc_normaal + lengte_mw_normaal

    mag_enkele_dwars = (totaal_cp7_vloer % 2 == 1) and (geschatte_lengte_normaal + 1150 <= max_lengte)

    if rest_750 >= 36 and rest_600 == 0 and pallets_cp3 == 0 and pallets_ibc == 0 and max_lengte == 13550:
        voeg_partij_toe_aslast("CP7_750", 4, "Smal (1150x1400)", centraal=True)
        rest_750 -= 4
        vloer_750 = math.ceil(rest_750 / 2)
    elif rest_600 >= 36 and rest_750 == 0 and pallets_cp3 == 0 and pallets_ibc == 0 and max_lengte == 13550:
        voeg_partij_toe_aslast("CP7_600", 4, "Smal (1100x1400)", centraal=True)
        rest_600 -= 4
        vloer_600 = math.ceil(rest_600 / 2)
    elif mag_enkele_dwars:
        if vloer_600 % 2 == 1 and rest_600 > 0:
            enkele_600 = 1 if rest_600 % 2 == 1 else 2
            voeg_partij_toe_aslast("CP7_600", enkele_600, "Smal (1100x1400)", centraal=True)
            rest_600 -= enkele_600
        elif vloer_750 % 2 == 1 and rest_750 > 0:
            enkele_750 = 1 if rest_750 % 2 == 1 else 2
            voeg_partij_toe_aslast("CP7_750", enkele_750, "Smal (1150x1400)", centraal=True)
            rest_750 -= enkele_750

    heeft_pdf_cp3 = pdf_d and (pdf_d["cp3_500"] + pdf_d["cp3_1000"] == pallets_cp3)
    cp3_licht = pdf_d["cp3_500"] if heeft_pdf_cp3 else (pallets_cp3 if product_info["CP3"]["gewicht"] == 500 else 0)
    cp3_zwaar = pdf_d["cp3_1000"] if heeft_pdf_cp3 else (pallets_cp3 if product_info["CP3"]["gewicht"] == 1000 else 0)

    cp3_licht_voor = (cp3_licht // 4) * 2
    if cp3_licht_voor == 0 and cp3_licht >= 2:
        cp3_licht_voor = 2
    cp3_licht_achter = max(0, cp3_licht - cp3_licht_voor)

    voeg_partij_toe("CP3", cp3_licht_voor, override_kg=500)
    voeg_partij_toe("CP7_600", rest_600)
    voeg_partij_toe("CP3", cp3_zwaar, override_kg=1000)
    voeg_partij_toe("IBC", pallets_ibc)
    voeg_partij_toe("Maatwerk", pallets_mw)
    voeg_partij_toe("CP7_750", rest_750)
    voeg_partij_toe("CP3", cp3_licht_achter, override_kg=500)
else:
    voeg_partij_toe_aslast("CP3", as_v_cp3, "Lang", centraal=handmatig_centraal)
    voeg_partij_toe_aslast("CP7_600", as_v_cp7_600, richting_v_cp7_600, centraal=handmatig_centraal)
    voeg_partij_toe_aslast("CP7_750", as_v_cp7_750, richting_v_cp7_750, centraal=handmatig_centraal)
    voeg_partij_toe_aslast("IBC", as_v_ibc, "Lang", centraal=handmatig_centraal)
    voeg_partij_toe_aslast("Maatwerk", as_v_mw, "Lang", centraal=handmatig_centraal)

    for art_naam in st.session_state.klik_volgorde:
        if art_naam in actuele_aantallen: voeg_partij_toe(art_naam, actuele_aantallen[art_naam])

    voeg_partij_toe_aslast("CP3", as_a_cp3, "Lang", centraal=handmatig_centraal)
    voeg_partij_toe_aslast("CP7_600", as_a_cp7_600, richting_a_cp7_600, centraal=handmatig_centraal)
    voeg_partij_toe_aslast("CP7_750", as_a_cp7_750, richting_a_cp7_750, centraal=handmatig_centraal)
    voeg_partij_toe_aslast("IBC", as_a_ibc, "Lang", centraal=handmatig_centraal)
    voeg_partij_toe_aslast("Maatwerk", as_a_mw, "Lang", centraal=handmatig_centraal)
fig, ax = plt.subplots(figsize=(15, 4.1))
ax.set_xlim(0, max_lengte)
ax.set_ylim(-650 if max_lengte == 13550 else -200, max_breedte + 180)
ax.set_aspect('equal', adjustable='box')
ax.axis('off')

container_border = patches.Rectangle((0, 0), max_lengte, max_breedte, linewidth=2, edgecolor='black', facecolor='none')
ax.add_patch(container_border)

ax.text(80, max_breedte + 45, "⬅️ KOPSCHOT (0 m)", ha="left", va="bottom", fontweight="bold", fontsize=9, color="#334155")
ax.text(max_lengte - 80, max_breedte + 45, f"DEUREN ({max_lengte / 1000:.2f} m) ➡️", ha="right", va="bottom", fontweight="bold", fontsize=9, color="#334155")

geplaatste_blokken = []
x_onder, x_boven, ibc_paar_teller, idx = 0, 0, 0, 0

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
        vulling_kleur = "#ff0000" if (start_x + item["L"] > max_lengte) else item["kleur"]
        y_pos = (max_breedte - item["B"]) / 2
        ax.add_patch(patches.Rectangle((start_x, y_pos), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85))
        ax.text(start_x + (item["L"]/2), y_pos + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        geplaatste_blokken.append({"x_mid": start_x + (item["L"] / 2), "kg": item["kg"]})
        x_onder, x_boven = start_x + item["L"], start_x + item["L"]
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
            ibc_paar_teller += 1; idx += 2; continue

    if x_onder <= x_boven:
        vulling_kleur = "#ff0000" if (x_onder + item["L"] > max_lengte) else item["kleur"]
        ax.add_patch(patches.Rectangle((x_onder, 20), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85))
        ax.text(x_onder + (item["L"]/2), 20 + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        geplaatste_blokken.append({"x_mid": x_onder + (item["L"] / 2), "kg": item["kg"]})
        x_onder += item["L"]
    else:
        vulling_kleur = "#ff0000" if (x_boven + item["L"] > max_lengte) else item["kleur"]
        ax.add_patch(patches.Rectangle((x_boven, max_breedte - item["B"] - 20), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85))
        ax.text(x_boven + (item["L"]/2), max_breedte - item["B"] - 20 + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        geplaatste_blokken.append({"x_mid": x_boven + (item["L"] / 2), "kg": item["kg"]})
        x_boven += item["L"]
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

totale_meters = max(x_onder, x_boven); restruimte = max_lengte - totale_meters
st.write("### 3. Plan & Aslast-controle:")
if pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0 or as_v_cp3 + as_v_cp7_600 + as_v_cp7_750 + as_v_ibc + as_v_mw + as_a_cp3 + as_a_cp7_600 + as_a_cp7_750 + as_a_ibc + as_a_mw > 0:
    if restruimte >= 0: st.success(f"✅ Past! Nog {restruimte} mm over — **Totaal gewicht lading:** {totaal_lading_kg} kg")
    else: st.error(f"❌ Past NIET! {abs(restruimte)} mm tekort — **Totaal gewicht lading:** {totaal_lading_kg} kg")

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
    st.download_button(label="📸 Download Laadplan (Afbeelding)", data=buf.getvalue(), file_name="fons_laadplan.png", mime="image/png")
else:
    st.info("Container is leeg. Upload een PDF/foto-laadbon of gebruik de + en - knoppen om te beginnen.")

st.divider()
import magazijn
importlib.reload(magazijn)
magazijn.toon_magazijn_tab()
