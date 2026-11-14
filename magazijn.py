import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.subheader("🏭 Magazijn Stapeling — Visueel op Pallets")

    mc1, mc2 = st.columns(2)
    with mc1:
        aantal_stuks = st.number_input("Aantal pallets van dit artikel:", min_value=1, value=48, step=1)
    with mc2:
        max_stapel = st.number_input("Max. stapelhoogte (lagen):", min_value=1, max_value=8, value=3, step=1)

    volle = aantal_stuks // max_stapel
    rest = aantal_stuks % max_stapel
    basis_hoogtes = [max_stapel] * volle

    if rest > 0:
        if rest == 1 and max_stapel >= 3 and len(basis_hoogtes) > 0:
            basis_hoogtes[-1] = max_stapel - 1
            basis_hoogtes.append(2)
        else:
            basis_hoogtes.append(rest)

    totaal_vloerplaatsen = len(basis_hoogtes)

    rijen_a = math.ceil(totaal_vloerplaatsen / 3)
    benutting_a = round((totaal_vloerplaatsen / (rijen_a * 3)) * 100)

    rijen_b = math.ceil(totaal_vloerplaatsen / 4)
    benutting_b = round((totaal_vloerplaatsen / (rijen_b * 4)) * 100)

    if rijen_b < rijen_a:
        st.success(f"💡 **Beste keuze (minste breedte): Kant B (4 diep)** — Je gebruikt maar **{rijen_b} rijen naast elkaar** (tegenover {rijen_a} rijen aan Kant A).")
    elif rijen_a < rijen_b:
        st.success(f"💡 **Beste keuze (minste breedte): Kant A (3 diep)** — Je gebruikt maar **{rijen_a} rijen naast elkaar** (tegenover {rijen_b} rijen aan Kant B).")
    else:
        if benutting_a >= benutting_b:
            st.success(f"💡 **Beste keuze: Kant A (3 diep)** — Beide kanten gebruiken **{rijen_a} rijen breed**, maar Kant A benut de rijen strakker ({benutting_a}% tegenover {benutting_b}%).")
        else:
            st.success(f"💡 **Beste keuze: Kant B (4 diep)** — Beide kanten gebruiken **{rijen_b} rijen breed**, maar Kant B benut de rijen strakker ({benutting_b}% tegenover {benutting_a}%).")

    col_a, col_b = st.columns(2)

    def teken_pallet_stapel(ax, x, y, breedte, hoogte, h_nu, max_h):
        if h_nu == 0:
            ax.add_patch(patches.Rectangle((x, y), breedte, hoogte, linewidth=1.2, linestyle="--", edgecolor="#94a3b8", facecolor="#f8fafc"))
            ax.text(x + breedte / 2, y + hoogte / 2, "Vrij", ha="center", va="center", fontweight="bold", fontsize=9, color="#94a3b8")
            return

        # 1. Houten pallet onderaan tekenen (strak zonder tussenruimte)
        p_hoogte = hoogte * 0.20
        bovenplank_h = p_hoogte * 0.36
        klos_h = p_hoogte * 0.64

        ax.add_patch(patches.Rectangle((x + 0.02, y + klos_h), breedte - 0.04, bovenplank_h, linewidth=1, edgecolor="#5c3a21", facecolor="#c89d7c"))

        klos_b = (breedte - 0.04) * 0.18
        for klos_x in [x + 0.02, x + breedte / 2 - klos_b / 2, x + breedte - 0.02 - klos_b]:
            ax.add_patch(patches.Rectangle((klos_x, y), klos_b, klos_h, linewidth=1, edgecolor="#5c3a21", facecolor="#8d5b3c"))

        # 2. Volledig blok lading direct bovenop de pallet (zonder witte lijnen ertussen)
        lading_y_start = y + p_hoogte
        beschikbare_hoogte = hoogte - p_hoogte
        totale_lading_h = beschikbare_hoogte * (h_nu / max_h)

        kleur_lading = "#1b5e20" if h_nu == max_h else "#2ecc71"
        tekst_kleur = "white" if h_nu == max_h else "black"

        ax.add_patch(patches.Rectangle((x + 0.03, lading_y_start), breedte - 0.06, totale_lading_h, linewidth=1, edgecolor="#144517", facecolor=kleur_lading))

        # 3. Label in het midden van het blok
        ax.text(x + breedte / 2, lading_y_start + totale_lading_h / 2, f"{h_nu}H", ha="center", va="center", fontweight="bold", fontsize=10, color=tekst_kleur)

    def teken_kant(kolom, titel, diepte, aantal_rijen, benutting):
        totaal_plekken = aantal_rijen * diepte
        lege_plekken = [0] * (totaal_plekken - len(basis_hoogtes))
        hoogtes = basis_hoogtes + lege_plekken

        grid = [[0 for _ in range(diepte)] for _ in range(aantal_rijen)]
        idx = 0
        for d in range(diepte):
            for r in range(aantal_rijen):
                grid[r][d] = hoogtes[idx]
                idx += 1

        tellingen = []
        for h in range(max_stapel, 0, -1):
            aantal_h = basis_hoogtes.count(h)
            if aantal_h > 0:
                tellingen.append(f"{aantal_h}x {h}H")
        uitleg_tekst = " + ".join(tellingen)

        with kolom:
            st.markdown(f"#### {titel}")
            k1, k2 = st.columns(2)
            k1.metric("Breedte (rijen naast elkaar)", f"{aantal_rijen} rijen", uitleg_tekst)
            k2.metric("Vloerbenutting", f"{benutting}%", f"{totaal_vloerplaatsen} van {totaal_plekken} plekken")

            stap_x = 1.12
            stap_y = 1.04
            breedte_fig = max(5.2, aantal_rijen * stap_x + 0.2)
            hoogte_fig = diepte * stap_y + 0.95
            fig, ax = plt.subplots(figsize=(breedte_fig, hoogte_fig))
            ax.set_xlim(0, aantal_rijen * stap_x + 0.15)
            ax.set_ylim(-0.35, diepte * stap_y + 0.65)
            ax.axis('off')

            # Muur bovenaan (compacter)
            ax.plot([0.1, aantal_rijen * stap_x], [diepte * stap_y + 0.35, diepte * stap_y + 0.35], color="#334155", linewidth=4)
            ax.text((aantal_rijen * stap_x) / 2, diepte * stap_y + 0.45, "🧱 MUUR (Achterkant)", ha="center", va="bottom", fontweight="bold", fontsize=10, color="#334155")

            # Gangpad onderaan (compacter)
            ax.text((aantal_rijen * stap_x) / 2, -0.25, "⬇️ GANGPAD (Voorkant) ⬇️", ha="center", va="top", fontweight="bold", fontsize=10, color="#64748b")

            for r in range(aantal_rijen):
                x = 0.12 + r * stap_x
                ax.text(x + 0.46, diepte * stap_y + 0.08, f"Rij {r + 1}", ha="center", va="bottom", fontweight="bold", fontsize=10)

                for d in range(diepte):
                    y = (diepte - 1 - d) * stap_y + 0.02
                    teken_pallet_stapel(ax, x, y, 0.92, 0.94, grid[r][d], max_stapel)

            st.pyplot(fig)

    teken_kant(col_a, "◀️ Kant A (3 diep)", 3, rijen_a, benutting_a)
    teken_kant(col_b, "▶️ Kant B (4 diep)", 4, rijen_b, benutting_b)
