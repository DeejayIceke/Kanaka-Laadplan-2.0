import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.subheader("🏭 Magazijn Stapeling — Vergelijking Kant A (3 diep) vs. Kant B (4 diep)")

    mc1, mc2 = st.columns(2)
    with mc1:
        aantal_stuks = st.number_input("Aantal pallets van dit artikel:", min_value=1, value=35, step=1)
    with mc2:
        max_stapel = st.number_input("Max. stapelhoogte (lagen):", min_value=1, max_value=8, value=4, step=1)

    totaal_vloerplaatsen = math.ceil(aantal_stuks / max_stapel)

    # Berekening Kant A (3 diep)
    rijen_a = math.ceil(totaal_vloerplaatsen / 3)
    plekken_a = rijen_a * 3
    benutting_a = round((aantal_stuks / (plekken_a * max_stapel)) * 100)

    # Berekening Kant B (4 diep)
    rijen_b = math.ceil(totaal_vloerplaatsen / 4)
    plekken_b = rijen_b * 4
    benutting_b = round((aantal_stuks / (plekken_b * max_stapel)) * 100)

    if benutting_a > benutting_b:
        st.success(f"💡 **Beste benutting: Kant A (3 diep)** — Je gebruikt **{rijen_a} rijen** ({benutting_a}% benut, tegenover {benutting_b}% aan Kant B).")
    elif benutting_b > benutting_a:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Je gebruikt **{rijen_b} rijen** ({benutting_b}% benut, tegenover {benutting_a}% aan Kant A).")
    else:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Beide kanten hebben **{benutting_b}%** benutting, maar aan Kant B heb je maar **{rijen_b} rijen** nodig i.p.v. {rijen_a}.")

    col_a, col_b = st.columns(2)

    def maak_stapel_verdeling(stuks, diepte, aantal_rijen, max_h):
        verdeling = []
        rest_stuks = stuks
        for r in range(aantal_rijen):
            rest_rijen_na_deze = aantal_rijen - 1 - r
            rest_plekken_na_deze = rest_rijen_na_deze * diepte
            rest_plekken_nu = (aantal_rijen - r) * diepte

            # Start met een volle rij op max_h zolang de rijen erna minstens 2H kunnen blijven (of als dit de laatste rij is)
            if rest_stuks >= diepte * max_h and (rest_plekken_na_deze == 0 or (rest_stuks - diepte * max_h) >= rest_plekken_na_deze * 2):
                for _ in range(diepte):
                    verdeling.append(max_h)
                rest_stuks -= diepte * max_h
            else:
                # Verdeel de overige pallets gelijkmatig (bijv. 3H en 2H) over de resterende plekken
                basis = rest_stuks // rest_plekken_nu
                extra = rest_stuks % rest_plekken_nu
                for _ in range(extra):
                    verdeling.append(basis + 1)
                for _ in range(rest_plekken_nu - extra):
                    verdeling.append(basis)
                break
        return verdeling

    def teken_kant(kolom, titel, diepte, aantal_rijen, benutting):
        totaal_plekken = aantal_rijen * diepte
        verdeling = maak_stapel_verdeling(aantal_stuks, diepte, aantal_rijen, max_stapel)

        tellingen = []
        for h in range(max_stapel, 0, -1):
            aantal_h = verdeling.count(h)
            if aantal_h > 0:
                tellingen.append(f"{aantal_h}x {h}H")
        uitleg_tekst = " + ".join(tellingen)

        with kolom:
            st.markdown(f"#### {titel}")
            k1, k2 = st.columns(2)
            k1.metric("Benodigde rijen", f"{aantal_rijen} rijen", uitleg_tekst)
            k2.metric("Stapel-benutting", f"{benutting}%", f"{totaal_plekken} vloerplekken gevuld")

            fig, ax = plt.subplots(figsize=(6, max(2.0, aantal_rijen * 0.75)))
            ax.set_xlim(0, diepte + 1.4)
            ax.set_ylim(0, aantal_rijen * 1.15)
            ax.axis('off')

            plek_idx = 0
            for r in range(aantal_rijen):
                y = (aantal_rijen - 1 - r) * 1.15 + 0.1
                ax.text(0, y + 0.45, f"Rij {r + 1}", va="center", fontweight="bold", fontsize=10)
                for d in range(diepte):
                    x = 1.1 + d * 0.95
                    h_nu = verdeling[plek_idx]
                    plek_idx += 1

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
                        label = "Leeg"

                    ax.add_patch(patches.Rectangle((x, y), 0.85, 0.85, linewidth=1.5, edgecolor="black", facecolor=kleur))
                    ax.text(x + 0.425, y + 0.425, label, ha="center", va="center", fontweight="bold", fontsize=10, color=tekst_kleur)
            st.pyplot(fig)

    teken_kant(col_a, "◀️ Kant A (3 diep)", 3, rijen_a, benutting_a)
    teken_kant(col_b, "▶️ Kant B (4 diep)", 4, rijen_b, benutting_b)

