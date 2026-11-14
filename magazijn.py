import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.subheader("🏭 Magazijn Stapeling — Volle rijen op 4H + rest apart tegen de muur")

    mc1, mc2 = st.columns(2)
    with mc1:
        aantal_stuks = st.number_input("Aantal pallets van dit artikel:", min_value=1, value=35, step=1)
    with mc2:
        max_stapel = st.number_input("Max. stapelhoogte (lagen):", min_value=1, max_value=8, value=4, step=1)

    totaal_vloerplaatsen = math.ceil(aantal_stuks / max_stapel)

    # Berekening Kant A (3 diep)
    rijen_a = math.ceil(totaal_vloerplaatsen / 3)
    benutting_a = round((totaal_vloerplaatsen / (rijen_a * 3)) * 100)

    # Berekening Kant B (4 diep)
    rijen_b = math.ceil(totaal_vloerplaatsen / 4)
    benutting_b = round((totaal_vloerplaatsen / (rijen_b * 4)) * 100)

    if benutting_a > benutting_b:
        st.success(f"💡 **Beste benutting: Kant A (3 diep)** — Je gebruikt **{rijen_a} rijen naast elkaar** ({benutting_a}% vloerbenutting, tegenover {benutting_b}% aan Kant B).")
    elif benutting_b > benutting_a:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Je gebruikt **{rijen_b} rijen naast elkaar** ({benutting_b}% vloerbenutting, tegenover {benutting_a}% aan Kant A).")
    else:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Beide kanten hebben **{benutting_b}%** vloerbenutting, maar aan Kant B heb je maar **{rijen_b} rijen** naast elkaar nodig.")

    col_a, col_b = st.columns(2)

    def maak_volle_rijen_plus_rest(stuks, aantal_rijen, diepte, max_h):
        grid = [[0 for _ in range(diepte)] for _ in range(aantal_rijen)]
        cap_per_rij = diepte * max_h
        volle_rijen = stuks // cap_per_rij
        rest_stuks = stuks % cap_per_rij

        # 1. Vul eerst alle volledige rijen 100% op maximale hoogte (bijv. 4H van muur tot gangpad)
        for r in range(min(volle_rijen, aantal_rijen)):
            for d in range(diepte):
                grid[r][d] = max_h

        # 2. Zet het restant apart in de laatste rij tegen de muur (zoveel mogelijk max_h, rest op het laatst)
        if rest_stuks > 0 and volle_rijen < aantal_rijen:
            r_laatst = volle_rijen
            volle_stapels_rest = rest_stuks // max_h
            laatste_stapel = rest_stuks % max_h

            d_idx = 0
            for _ in range(volle_stapels_rest):
                if d_idx < diepte:
                    grid[r_laatst][d_idx] = max_h
                    d_idx += 1
            if laatste_stapel > 0 and d_idx < diepte:
                grid[r_laatst][d_idx] = laatste_stapel

        return grid

    def teken_kant(kolom, titel, diepte, aantal_rijen, benutting):
        grid = maak_volle_rijen_plus_rest(aantal_stuks, aantal_rijen, diepte, max_stapel)

        alle_hoogtes = [grid[r][d] for r in range(aantal_rijen) for d in range(diepte) if grid[r][d] > 0]
        tellingen = []
        for h in range(max_stapel, 0, -1):
            aantal_h = alle_hoogtes.count(h)
            if aantal_h > 0:
                tellingen.append(f"{aantal_h}x {h}H")
        uitleg_tekst = " + ".join(tellingen)

        with kolom:
            st.markdown(f"#### {titel}")
            k1, k2 = st.columns(2)
            k1.metric("Rijen naast elkaar", f"{aantal_rijen} rijen", uitleg_tekst)
            k2.metric("Vloerbenutting", f"{benutting}%", f"{len(alle_hoogtes)} van {aantal_rijen * diepte} plekken")

            breedte_fig = max(5.0, aantal_rijen * 1.15)
            hoogte_fig = diepte * 1.05 + 1.3
            fig, ax = plt.subplots(figsize=(breedte_fig, hoogte_fig))
            ax.set_xlim(0, aantal_rijen * 1.15 + 0.2)
            ax.set_ylim(-0.6, diepte * 1.05 + 0.9)
            ax.axis('off')

            # Muur bovenaan
            ax.plot([0.1, aantal_rijen * 1.15], [diepte * 1.05 + 0.5, diepte * 1.05 + 0.5], color="#334155", linewidth=4)
            ax.text((aantal_rijen * 1.15) / 2, diepte * 1.05 + 0.65, "🧱 MUUR (Achterkant)", ha="center", va="bottom", fontweight="bold", fontsize=10, color="#334155")

            # Gangpad onderaan
            ax.text((aantal_rijen * 1.15) / 2, -0.45, "⬇️ GANGPAD (Voorkant) ⬇️", ha="center", va="top", fontweight="bold", fontsize=10, color="#64748b")

            for r in range(aantal_rijen):
                x = 0.15 + r * 1.15
                ax.text(x + 0.45, diepte * 1.05 + 0.15, f"Rij {r + 1}", ha="center", va="bottom", fontweight="bold", fontsize=10)

                for d in range(diepte):
                    y = (diepte - 1 - d) * 1.05 + 0.05
                    h_nu = grid[r][d]

                    if h_nu == max_stapel:
                        kleur = "#1b5e20"
                        tekst_kleur = "white"
                        label = f"{h_nu}H"
                    elif h_nu > 0:
                        kleur = "#2ecc71"
                        tekst_kleur = "black"
                        label = f"{h_nu}H"
                    else:
                        kleur = "#e2e8f0"
                        tekst_kleur = "#64748b"
                        label = "Vrij"

                    ax.add_patch(patches.Rectangle((x, y), 0.9, 0.9, linewidth=1.5, edgecolor="black", facecolor=kleur))
                    ax.text(x + 0.45, y + 0.45, label, ha="center", va="center", fontweight="bold", fontsize=10, color=tekst_kleur)
            st.pyplot(fig)

    teken_kant(col_a, "◀️ Kant A (3 diep)", 3, rijen_a, benutting_a)
    teken_kant(col_b, "▶️ Kant B (4 diep)", 4, rijen_b, benutting_b)
