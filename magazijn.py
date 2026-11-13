import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.subheader("🏭 Magazijn Stapeling — Vergelijking Kant A (3 diep) vs. Kant B (4 diep)")

    mc1, mc2 = st.columns(2)
    with mc1:
        aantal_stuks = st.number_input("Aantal pallets van dit artikel:", min_value=1, value=50, step=1)
    with mc2:
        max_stapel = st.number_input("Max. stapelhoogte (lagen):", min_value=1, max_value=8, value=3, step=1)

    totaal_vloerplaatsen = math.ceil(aantal_stuks / max_stapel)
    volle_stapels = aantal_stuks // max_stapel
    rest_hoogte = aantal_stuks % max_stapel
    stapel_uitleg = f"{volle_stapels}x {max_stapel}H" + (f" + 1x {rest_hoogte}H" if rest_hoogte > 0 else "")

    # Berekening Kant A (3 diep)
    rijen_a = math.ceil(totaal_vloerplaatsen / 3)
    plekken_a = rijen_a * 3
    loze_a = plekken_a - totaal_vloerplaatsen
    benutting_a = round((totaal_vloerplaatsen / plekken_a) * 100)

    # Berekening Kant B (4 diep)
    rijen_b = math.ceil(totaal_vloerplaatsen / 4)
    plekken_b = rijen_b * 4
    loze_b = plekken_b - totaal_vloerplaatsen
    benutting_b = round((totaal_vloerplaatsen / plekken_b) * 100)

    # Beste keuze bepalen op basis van hoogste ruimtebenutting (minste loze vloerplekken)
    if loze_a < loze_b:
        st.success(f"💡 **Beste benutting: Kant A (3 diep)** — Je hebt **{rijen_a} rijen** nodig ({benutting_a}% benut, slechts **{loze_a} loze plek(ken)** tegenover {loze_b} aan Kant B).")
    elif loze_b < loze_a:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Je hebt **{rijen_b} rijen** nodig ({benutting_b}% benut, slechts **{loze_b} loze plek(ken)** tegenover {loze_a} aan Kant A).")
    else:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Beide kanten hebben **{loze_b} loze plek(ken)**, maar aan Kant B heb je maar **{rijen_b} rijen** nodig i.p.v. {rijen_a}.")

    # Twee kolommen naast elkaar: Links Kant A, Rechts Kant B
    col_a, col_b = st.columns(2)
    stapel_lijst = [max_stapel] * volle_stapels + ([rest_hoogte] if rest_hoogte > 0 else [])

    def teken_kant(kolom, titel, diepte, aantal_rijen, benutting, loze_plekken):
        with kolom:
            st.markdown(f"#### {titel}")
            k1, k2 = st.columns(2)
            k1.metric("Benodigde rijen", f"{aantal_rijen} rijen", f"Totaal {totaal_vloerplaatsen} stapels ({stapel_uitleg})")
            k2.metric("Ruimtebenutting", f"{benutting}%", f"{loze_plekken} lege plek(ken) in laatste rij")

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
                    if plek_idx < len(stapel_lijst):
                        h_nu = stapel_lijst[plek_idx]
                        plek_idx += 1
                        kleur = "#1b5e20" if h_nu == max_stapel else "#2ecc71"
                        tekst_kleur = "white" if h_nu == max_stapel else "black"
                        label = f"{h_nu}H"
                    else:
                        kleur = "#e2e8f0"
                        tekst_kleur = "#64748b"
                        label = "Leeg"

                    ax.add_patch(patches.Rectangle((x, y), 0.85, 0.85, linewidth=1.5, edgecolor="black", facecolor=kleur))
                    ax.text(x + 0.425, y + 0.425, label, ha="center", va="center", fontweight="bold", fontsize=10, color=tekst_kleur)
            st.pyplot(fig)

    teken_kant(col_a, "◀️ Kant A (3 diep)", 3, rijen_a, benutting_a, loze_a)
    teken_kant(col_b, "▶️ Kant B (4 diep)", 4, rijen_b, benutting_b, loze_b)
