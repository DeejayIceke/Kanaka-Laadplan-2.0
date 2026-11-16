import streamlit as st
import math
import io
import re
import importlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

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
        <div class="modern-subtitle">Slimme containerindeling, Laadbon import (PDF &amp; Foto) &amp; aslast-optimalisatie</div>
    </div>
""", unsafe_allow_html=True)

def verwerk_laadbon_tekst(volledige_tekst):
    res = {
        "cp3_500": 0,
        "cp3_1000": 0,
        "cp7_600": 0,
        "cp7_750": 0,
        "ibc": 0,
        "totaal_gewicht": 0,
        "regels": []
    }

    huidige_groep = None

    for regel in volledige_tekst.splitlines():
        r_upper = regel.upper().strip()
        if not r_upper:
            continue

        # Stop of sla totaalregels over
        if "ITEMS TOTAL" in r_upper or "ITEM TOTAL" in r_upper:
            continue

        # Herken groepskoppen op de bon ("Stack. CP-7" of "Non-Stack. CP-3")
        if "CP-7" in r_upper or "CP7" in r_upper or "STACK." in r_upper:
            if "NON-STACK" not in r_upper and "NON STACK" not in r_upper:
                huidige_groep = "CP7"
        if "CP-3" in r_upper or "CP3" in r_upper or "NON-STACK" in r_upper or "NON STACK" in r_upper:
            huidige_groep = "CP3"

        # Sla de blauwe subtotaal-kopregels met een schuine streep over (bijv. "6 PAL / 3.600 KG" of "16 PAL / 16.000 KG")
        if re.search(r'PAL\s*/', r_upper):
            continue

        pal_match = re.search(r'(\d+)\s*PAL\b', r_upper)
        kg_match = re.search(r'([\d\.,]+)\s*KG\b', r_upper)

        if pal_match:
            aantal_pal = int(pal_match.group(1))
            gewicht_kg = 0
            if kg_match:
                kg_str = kg_match.group(1).replace(".", "").replace(",", ".")
                try:
                    gewicht_kg = int(float(kg_str))
                except ValueError:
                    gewicht_kg = 0

            # Bepaal het pallettype op basis van artikelcode op de regel, of anders op basis van de groepskop erboven
            is_ibc = "CNPE" in r_upper
            is_cp7 = any(code in r_upper for code in ["-NB", "-N8", "B-NB", "B-N8"]) or (not is_ibc and huidige_groep == "CP7")
            is_sb1 = any(code in r_upper for code in ["-SB1", "-S81", "B-SB1", "K6-SB1"])
            is_sb5 = any(code in r_upper for code in ["-SB5", "-S85", "-SBS", "B-SB5", "K6-SB5"])

            if is_ibc:
                res["ibc"] += aantal_pal
                res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 1000
                res["regels"].append(f"{aantal_pal}x IBC (CNPE)")

            elif is_cp7:
                kg_per_pal = (gewicht_kg / aantal_pal) if aantal_pal > 0 and gewicht_kg > 0 else 600
                if kg_per_pal > 650:
                    res["cp7_750"] += aantal_pal
                    res["regels"].append(f"{aantal_pal}x CP7 750kg")
                else:
                    res["cp7_600"] += aantal_pal
                    res["regels"].append(f"{aantal_pal}x CP7 600kg")
                res["totaal_gewicht"] += gewicht_kg

            elif is_sb1:
                res["cp3_1000"] += aantal_pal
                res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 1000
                res["regels"].append(f"{aantal_pal}x CP3 1000kg (-SB1)")

            elif is_sb5 or huidige_groep == "CP3":
                kg_per_pal = (gewicht_kg / aantal_pal) if aantal_pal > 0 and gewicht_kg > 0 else 500
                if kg_per_pal > 750 and not is_sb5:
                    res["cp3_1000"] += aantal_pal
                    res["regels"].append(f"{aantal_pal}x CP3 1000kg")
                else:
                    res["cp3_500"] += aantal_pal
                    res["regels"].append(f"{aantal_pal}x CP3 500kg")
                res["totaal_gewicht"] += gewicht_kg if gewicht_kg > 0 else aantal_pal * 500

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
            afbeelding = afbeelding.convert("RGB")
            volledige_tekst = pytesseract.image_to_string(afbeelding, config="--psm 6")
            return verwerk_laadbon_tekst(volledige_tekst)
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
        return verwerk_laadbon_tekst(volledige_tekst)

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
        if d["regels"]:
            st.success(f"✅ **Bon ingelezen:** {' | '.join(d['regels'])} — **Totaal gewicht:** {d['totaal_gewicht']} kg")
        else:
            st.warning("⚠️ Bestand gelezen, maar geen regels met `PAL` en `-NB / -SB5 / -SB1 / CNPE` herkend. Maak een rechtere/scherpere foto of gebruik de SAP-PDF.")
st.write("### 1. Kies container:")
container_type = st.selectbox(
    "1. Kies container:", 
    ["45ft Container (13550 x 2426 mm)", "40ft Container (12030 x 2350 mm)", "20ft Container (5898 x 2350 mm)"],
    label_visibility="collapsed"
)

max_lengte = 13550 if "45ft" in container_type else 12030 if "40ft" in container_type else 5898
max_breedte = 2426 if "45ft" in container_type else 2350

product_info = {
    "CP3": {"lengte": 1150, "breedte": 1150, "kleur": "#3498db", "stapelbaar": False, "label": "CP3"},
    "CP7_600": {"lengte": 1400, "breedte": 1100, "kleur": "#2ecc71", "stapelbaar": True, "label": "CP7 600"},
    "CP7_750": {"lengte": 1400, "breedte": 1200, "kleur": "#e74c3c", "stapelbaar": True, "label": "CP7 750"},
    "IBC": {"lengte": 1000, "breedte": 1200, "kleur": "#f1c40f", "stapelbaar": False, "label": "IBC"},
    "Maatwerk": {"lengte": 1000, "breedte": 1000, "kleur": "#7f8c8d", "stapelbaar": False, "label": "Maatwerk"}
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
    if pallets_cp3 > 0 and "CP3" not in st.session_state.klik_volgorde: st.session_state.klik_volgorde.append("CP3")

with col2:
    st.markdown('<div class="custom-box" style="background-color:#2ecc71;">CP7 600kg (1400x1100)</div>', unsafe_allow_html=True)
    pallets_cp7_600_totaal = st.number_input("Aantal CP7 600", min_value=0, value=init_cp7_600, step=1, key=f"cp7_600_{st.session_state.reset_id}", label_visibility="collapsed")

with col3:
    st.markdown('<div class="custom-box" style="background-color:#e74c3c;">CP7 750kg (1400x1200)</div>', unsafe_allow_html=True)
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
        product_info["Maatwerk"]["lengte"] = mw_L
        product_info["Maatwerk"]["breedte"] = mw_B

auto_aslast = False
if pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0:
    auto_aslast = st.checkbox("⚖️ Automatisch optimaliseren op aslast & oppervlakte (even CP7 altijd naast elkaar, enkele vooraan dwars)", value=(pdf_d is not None))

as_v_cp3, as_a_cp3 = 0, 0
as_v_cp7_600, as_a_cp7_600 = 0, 0
as_v_cp7_750, as_a_cp7_750 = 0, 0
as_v_ibc, as_a_ibc = 0, 0
as_v_mw, as_a_mw = 0, 0

richting_v_cp7_600 = "Lang (1400x1100)"
richting_a_cp7_600 = "Lang (1400x1100)"
richting_v_cp7_750 = "Lang (1400x1200)"
richting_a_cp7_750 = "Lang (1400x1200)"

if not auto_aslast and (pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0):
    with st.expander("⚖️ Klik hier voor handmatige aslast-regelingen (Midden vooraan/achteraan)"):
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
                    richting_v_cp7_750 = st.radio("Richting VOR (750):", ["Lang (1400x1200)", "Smal (1200x1400)"], key=f"r_v_cp7_750_{st.session_state.reset_id}")
                as_a_cp7_750 = st.number_input("CP7 750 ACH", min_value=0, max_value=pallets_cp7_750_totaal - as_v_cp7_750, value=0, step=1, key=f"a_cp7_750_{st.session_state.reset_id}")
                if as_a_cp7_750 > 0:
                    richting_a_cp7_750 = st.radio("Richting ACH (750):", ["Lang (1400x1200)", "Smal (1200x1400)"], key=f"r_a_cp7_750_{st.session_state.reset_id}")
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

def voeg_partij_toe_aslast(art_naam, aantal, richting):
    if aantal > 0:
        info = product_info[art_naam].copy()
        if "Smal" in richting:
            info["lengte"], info["breedte"] = info["breedte"], info["lengte"]

        vloer = int(math.ceil(aantal / 2)) if info["stapelbaar"] else int(aantal)
        overgebleven = aantal
        for _ in range(vloer):
            h_label = " (2H)" if info["stapelbaar"] and overgebleven >= 2 else (" (1H)" if info["stapelbaar"] else "")
            gekozen_kleur = haal_pallet_kleur(art_naam, overgebleven, info["kleur"])
            overgebleven -= 2
            laad_lijst.append({"naam": f"{info['label']}{h_label}", "naam_puur": art_naam, "L": info["lengte"], "B": info["breedte"], "kleur": gekozen_kleur, "force_midden": True})

def voeg_partij_toe(art_naam, aantal, dwars=False):
    if aantal > 0:
        info = product_info[art_naam].copy()
        if dwars:
            info["lengte"], info["breedte"] = info["breedte"], info["lengte"]
        vloer = int(math.ceil(aantal / 2)) if info["stapelbaar"] else int(aantal)
        overgebleven = aantal
        for _ in range(vloer):
            h_label = " (2H)" if info["stapelbaar"] and overgebleven >= 2 else (" (1H)" if info["stapelbaar"] else "")
            gekozen_kleur = haal_pallet_kleur(art_naam, overgebleven, info["kleur"])
            overgebleven -= 2
            laad_lijst.append({"naam": f"{info['label']}{h_label}", "naam_puur": art_naam, "L": info["lengte"], "B": info["breedte"], "kleur": gekozen_kleur, "force_midden": False})

if auto_aslast:
    rest_600 = pallets_cp7_600_totaal
    rest_750 = pallets_cp7_750_totaal

    vloer_600 = math.ceil(rest_600 / 2)
    if vloer_600 % 2 == 1 and rest_600 > 0:
        enkele_600 = 1 if rest_600 % 2 == 1 else 2
        voeg_partij_toe_aslast("CP7_600", enkele_600, "Smal (1100x1400)")
        rest_600 -= enkele_600

    vloer_750 = math.ceil(rest_750 / 2)
    if vloer_750 % 2 == 1 and rest_750 > 0:
        enkele_750 = 1 if rest_750 % 2 == 1 else 2
        voeg_partij_toe_aslast("CP7_750", enkele_750, "Smal (1200x1400)")
        rest_750 -= enkele_750

    cp3_licht = pdf_d["cp3_500"] if pdf_d and (pdf_d["cp3_500"] + pdf_d["cp3_1000"] == pallets_cp3) else pallets_cp3
    cp3_zwaar = pdf_d["cp3_1000"] if pdf_d and (pdf_d["cp3_500"] + pdf_d["cp3_1000"] == pallets_cp3) else 0

    cp3_licht_voor = (cp3_licht // 4) * 2
    if cp3_licht_voor == 0 and cp3_licht >= 2:
        cp3_licht_voor = 2
    cp3_licht_achter = max(0, cp3_licht - cp3_licht_voor)

    voeg_partij_toe("CP3", cp3_licht_voor)
    voeg_partij_toe("CP7_600", rest_600)
    voeg_partij_toe("CP7_750", rest_750)
    voeg_partij_toe("CP3", cp3_zwaar)
    voeg_partij_toe("IBC", pallets_ibc)
    voeg_partij_toe("Maatwerk", pallets_mw)
    voeg_partij_toe("CP3", cp3_licht_achter)
else:
    voeg_partij_toe_aslast("CP3", as_v_cp3, "Lang")
    voeg_partij_toe_aslast("CP7_600", as_v_cp7_600, richting_v_cp7_600)
    voeg_partij_toe_aslast("CP7_750", as_v_cp7_750, richting_v_cp7_750)
    voeg_partij_toe_aslast("IBC", as_v_ibc, "Lang")
    voeg_partij_toe_aslast("Maatwerk", as_v_mw, "Lang")

    for art_naam in st.session_state.klik_volgorde:
        if art_naam in actuele_aantallen: voeg_partij_toe(art_naam, actuele_aantallen[art_naam])

    voeg_partij_toe_aslast("CP3", as_a_cp3, "Lang")
    voeg_partij_toe_aslast("CP7_600", as_a_cp7_600, richting_a_cp7_600)
    voeg_partij_toe_aslast("CP7_750", as_a_cp7_750, richting_a_cp7_750)
    voeg_partij_toe_aslast("IBC", as_a_ibc, "Lang")
    voeg_partij_toe_aslast("Maatwerk", as_a_mw, "Lang")
fig, ax = plt.subplots(figsize=(15, 3.5))
ax.set_xlim(0, max_lengte); ax.set_ylim(0, max_breedte); ax.set_aspect('equal', adjustable='box')
container_border = patches.Rectangle((0, 0), max_lengte, max_breedte, linewidth=2, edgecolor='black', facecolor='none')
ax.add_patch(container_border)

x_onder, x_boven, ibc_paar_teller, idx = 0, 0, 0, 0
while idx < len(laad_lijst):
    item = laad_lijst[idx]
    tekst_grootte = 10

    if item["L"] <= 1200 and "CP7" in item["naam"]:
        if "600" in item["naam"]:
            tekst_weergave = item["naam"].replace(" 600", "") + "\n600"
        else:
            tekst_weergave = item["naam"].replace(" 750", "") + "\n750"
    else:
        tekst_weergave = item["naam"]

    if item["force_midden"]:
        start_x = max(x_onder, x_boven)
        vulling_kleur = "#ff0000" if (start_x + item["L"] > max_lengte) else item["kleur"]
        y_pos = (max_breedte - item["B"]) / 2
        rect = patches.Rectangle((start_x, y_pos), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85)
        ax.add_patch(rect)
        ax.text(start_x + (item["L"]/2), y_pos + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        x_onder, x_boven = start_x + item["L"], start_x + item["L"]
        idx += 1
        continue
    if max_breedte == 2350 and item["naam_puur"] == "IBC":
        heeft_partner = (idx + 1 < len(laad_lijst) and laad_lijst[idx+1]["naam_puur"] == "IBC" and not laad_lijst[idx+1]["force_midden"])
        if heeft_partner:
            if ibc_paar_teller % 2 == 0:
                x_pos_onder = max(x_onder, x_boven) if ibc_paar_teller == 0 else x_onder
                vulling_kleur1 = "#ff0000" if (x_pos_onder + 1000 > max_lengte) else item["kleur"]
                rect1 = patches.Rectangle((x_pos_onder, 20), 1000, 1200, linewidth=1, edgecolor='white', facecolor=vulling_kleur1, alpha=0.85)
                ax.add_patch(rect1)
                ax.text(x_pos_onder + 500, 20 + 600, "IBC (Breed)", color="black", weight="bold", ha="center", va="center", fontsize=11)
                x_pos_boven = max(x_onder, x_boven) if ibc_paar_teller == 0 else x_boven
                vulling_kleur2 = "#ff0000" if (x_pos_boven + 1200 > max_lengte) else item["kleur"]
                rect2 = patches.Rectangle((x_pos_boven, max_breedte - 1000 - 20), 1200, 1000, linewidth=1, edgecolor='white', facecolor=vulling_kleur2, alpha=0.85)
                ax.add_patch(rect2)
                ax.text(x_pos_boven + 600, max_breedte - 1000 - 20 + 500, "IBC (Lang)", color="black", weight="bold", ha="center", va="center", fontsize=11)
                x_onder, x_boven = x_pos_onder + 1000, x_pos_boven + 1200
            else:
                vulling_kleur1 = "#ff0000" if (x_onder + 1200 > max_lengte) else item["kleur"]
                rect1 = patches.Rectangle((x_onder, 20), 1200, 1000, linewidth=1, edgecolor='white', facecolor=vulling_kleur1, alpha=0.85)
                ax.add_patch(rect1)
                ax.text(x_onder + 600, 20 + 500, "IBC (Lang)", color="black", weight="bold", ha="center", va="center", fontsize=11)
                vulling_kleur2 = "#ff0000" if (x_boven + 1000 > max_lengte) else item["kleur"]
                rect2 = patches.Rectangle((x_boven, max_breedte - 1200 - 20), 1000, 1200, linewidth=1, edgecolor='white', facecolor=vulling_kleur2, alpha=0.85)
                ax.add_patch(rect2)
                ax.text(x_boven + 500, max_breedte - 1200 - 20 + 600, "IBC (Breed)", color="black", weight="bold", ha="center", va="center", fontsize=11)
                x_onder, x_boven = x_onder + 1200, x_boven + 1000
            ibc_paar_teller += 1; idx += 2; continue
    if x_onder <= x_boven:
        vulling_kleur = "#ff0000" if (x_onder + item["L"] > max_lengte) else item["kleur"]
        rect = patches.Rectangle((x_onder, 20), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85)
        ax.add_patch(rect)
        ax.text(x_onder + (item["L"]/2), 20 + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        x_onder += item["L"]
    else:
        vulling_kleur = "#ff0000" if (x_boven + item["L"] > max_lengte) else item["kleur"]
        rect = patches.Rectangle((x_boven, max_breedte - item["B"] - 20), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85)
        ax.add_patch(rect)
        ax.text(x_boven + (item["L"]/2), max_breedte - item["B"] - 20 + (item["B"]/2), tekst_weergave, color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        x_boven += item["L"]
    idx += 1

totale_meters = max(x_onder, x_boven); restruimte = max_lengte - totale_meters
st.write("### 3. Plan:")
if pallets_cp3 + pallets_cp7_600_totaal + pallets_cp7_750_totaal + pallets_ibc + pallets_mw > 0 or as_v_cp3 + as_v_cp7_600 + as_v_cp7_750 + as_v_ibc + as_v_mw + as_a_cp3 + as_a_cp7_600 + as_a_cp7_750 + as_a_ibc + as_a_mw > 0:
    if restruimte >= 0: st.success(f"✅ Past! Nog {restruimte} mm over.")
    else: st.error(f"❌ Past NIET! {abs(restruimte)} mm tekort.")
    st.pyplot(fig, use_container_width=True)
    st.write(f"**Geladen:** {totale_meters} mm van {max_lengte} mm.")
    st.write("💡 **Legenda:** Blauw=CP3 | Groen=CP7 600kg | Rood=CP7 750kg | Geel=IBC | Grijs=Maatwerk | FELROOD=Past Niet")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    st.download_button(
        label="📸 Download Laadplan (Afbeelding)",
        data=buf.getvalue(),
        file_name="fons_laadplan.png",
        mime="image/png"
    )
else:
    st.info("Container is leeg. Upload een PDF/foto-laadbon of gebruik de + en - knoppen om te beginnen.")

st.divider()
import magazijn
importlib.reload(magazijn)
magazijn.toon_magazijn_tab()
