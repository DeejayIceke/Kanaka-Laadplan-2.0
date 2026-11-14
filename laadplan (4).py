import math
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Fons Laadplan", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; }
        div[data-testid="stColumn"] { display: flex; flex-direction: column; }
        .custom-box {
            padding: 0.45rem; border-radius: 0.5rem; color: white; font-weight: bold; 
            font-size: 13px; text-align: center; margin-bottom: 0.25rem;
            min-height: 43px; display: flex; align-items: center; justify-content: center;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Fons Laadplan 2.0 🚛")

container_type = st.selectbox(
    "1. Kies container:", 
    ["45ft Container (13550 x 2426 mm)", "40ft Container (12030 x 2350 mm)", "20ft Container (5898 x 2350 mm)"]
)

max_lengte = 13550 if "45ft" in container_type else 12030 if "40ft" in container_type else 5898
max_breedte = 2426 if "45ft" in container_type else 2350

if "klik_volgorde" not in st.session_state: st.session_state.klik_volgorde = []
if "reset_id" not in st.session_state: st.session_state.reset_id = 0

product_info = {
    "CP3": {"lengte": 1150, "breedte": 1150, "kleur": "#3498db", "stapelbaar": False, "label": "CP3"},
    "CP7_600": {"lengte": 1400, "breedte": 1100, "kleur": "#2ecc71", "stapelbaar": True, "label": "CP7 600"},
    "CP7_750": {"lengte": 1400, "breedte": 1200, "kleur": "#e74c3c", "stapelbaar": True, "label": "CP7 750"},
    "IBC": {"lengte": 1000, "breedte": 1200, "kleur": "#f1c40f", "stapelbaar": False, "label": "IBC"},
    "Maatwerk": {"lengte": 1000, "breedte": 1000, "kleur": "#7f8c8d", "stapelbaar": False, "label": "Maatwerk"}
}
def haal_pallet_kleur(art_naam, overgebleven, standaard_kleur):
    if art_naam == "CP7_600":
        return "#1b5e20" if overgebleven >= 2 else "#2ecc71"
    elif art_naam == "CP7_750":
        return "#b71c1c" if overgebleven >= 2 else "#ff7675"
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

def voeg_partij_toe(art_naam, aantal):
    if aantal > 0:
        info = product_info[art_naam]
        vloer = int(math.ceil(aantal / 2)) if info["stapelbaar"] else int(aantal)
        overgebleven = aantal
        for _ in range(vloer):
            h_label = " (2H)" if info["stapelbaar"] and overgebleven >= 2 else (" (1H)" if info["stapelbaar"] else "")
            gekozen_kleur = haal_pallet_kleur(art_naam, overgebleven, info["kleur"])
            overgebleven -= 2
            laad_lijst.append({"naam": f"{info['label']}{h_label}", "naam_puur": art_naam, "L": info["lengte"], "B": info["breedte"], "kleur": gekozen_kleur, "force_midden": False})
x_onder, x_boven, ibc_paar_teller, idx = 0, 0, 0, 0
while idx < len(laad_lijst):
    item = laad_lijst[idx]
    tekst_grootte = 7 if item["L"] <= 1200 and "CP7" in item["naam"] else 10

    if item["force_midden"]:
        start_x = max(x_onder, x_boven)
        vulling_kleur = "#ff0000" if (start_x + item["L"] > max_lengte) else item["kleur"]
        y_pos = (max_breedte - item["B"]) / 2
        rect = patches.Rectangle((start_x, y_pos), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85)
        ax.add_patch(rect)
        ax.text(start_x + (item["L"]/2), y_pos + (item["B"]/2), item["naam"], color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
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
        ax.text(x_onder + (item["L"]/2), 20 + (item["B"]/2), item["naam"], color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        x_onder += item["L"]
    else:
        vulling_kleur = "#ff0000" if (x_boven + item["L"] > max_lengte) else item["kleur"]
        rect = patches.Rectangle((x_boven, max_breedte - item["B"] - 20), item["L"], item["B"], linewidth=1, edgecolor='white', facecolor=vulling_kleur, alpha=0.85)
        ax.add_patch(rect)
        ax.text(x_boven + (item["L"]/2), max_breedte - item["B"] - 20 + (item["B"]/2), item["naam"], color="white" if "750" in item["naam"] else "black", weight="bold", ha="center", va="center", fontsize=tekst_grootte)
        x_boven += item["L"]
    idx += 1
