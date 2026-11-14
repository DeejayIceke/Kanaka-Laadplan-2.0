import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.subheader("🏭 Magazijn Stapeling — Maximaal hoog van achter tegen de muur")

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

            breedte_fig = max(5.0, aantal_rijen * 1.15)
            hoogte_fig = diepte * 1.05 + 1.3
            fig, ax = plt.subplots(figsize=(breedte_fig, hoogte_fig))
            ax.set_xlim(0, aantal_rijen * 1.15 + 0.2)
            ax.set_ylim(-0.6, diepte * 1.05 + 0.9)
            ax.axis('off')

            ax.plot([0.1, aantal_rijen * 1.15], [diepte * 1.05 + 0.5, diepte * 1.05 + 0.5], color="#334155", linewidth=4)
            ax.text((aantal_rijen * 1.15) / 2, diepte * 1.05 + 0.65, "🧱 MUUR (Achterkant)", ha="center", va="bottom", fontweight="bold", fontsize=10, color="#334155")
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

