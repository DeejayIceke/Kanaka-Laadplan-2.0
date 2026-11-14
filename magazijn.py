import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.subheader("🏭 Magazijn Stapeling — Lagen langs de muur (4H achteraan)")

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
        st.success(f"💡 **Beste benutting: Kant A (3 diep)** — Je gebruikt **{rijen_a} rijen naast elkaar** ({benutting_a}% benut, tegenover {benutting_b}% aan Kant B).")
    elif benutting_b > benutting_a:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Je gebruikt **{rijen_b} rijen naast elkaar** ({benutting_b}% benut, tegenover {benutting_a}% aan Kant A).")
    else:
        st.success(f"💡 **Beste benutting: Kant B (4 diep)** — Beide kanten hebben **{benutting_b}%** benutting, maar aan Kant B heb je maar **{rijen_b} rijen** naast elkaar nodig i.p.v. {rijen_a}.")

    col_a, col_b = st.columns(2)

    def maak_lagen_langs_muur(stuks, aantal_rijen, diepte, max_h):
        # d = 0 is de achterste lijn tegen de muur, d = diepte - 1 is de voorste lijn aan het gangpad
        # Elke horizontale lijn d (over alle rijen r) krijgt dezelfde hoogte, aflopend van muur naar gangpad
        grid = [[0 for _ in range(diepte)] for _ in range(aantal_rijen)]
        rest = stuks

        for d in range(diepte):
            lijnen_erna = diepte - 1 - d
            if rest <= 0:
                break

            gekozen_h = 0
            for h in range(max_h, 0, -1):
                nodig_voor_deze_lijn = h * aantal_rijen
                over_voor_later = rest - nodig_voor_deze_lijn
                if lijnen_erna == 0:
                    if over_voor_later <= 0:
                        gekozen_h = h
                else:
                    min_nodig_later = lijnen_erna * aantal_rijen * 2
                    if over_voor_later >= min_nodig_later:
                        gekozen_h = h
                        break

            if lijnen_erna > 0 and gekozen_h > 0:
                for r in range(aantal_rijen):
                    grid[r][d] = gekozen_h
                rest -= gekozen_h * aantal_rijen
            else:
                # Voorste lijn aan het gangpad: verdeel de overgebleven pallets zo gelijk mogelijk (bijv. 2H, 2H, 1H)
                basis = rest // aantal_rijen
                extra = rest % aantal_rijen
                for r in range(aantal_rijen):
                    grid[r][d] = basis + (1 if r < extra else 0)
                rest = 0
        return grid

    def teken_kant(kolom, titel, diepte, aantal_rijen, benutting):
        grid = maak_lagen_langs_muur(aantal_stuks, aantal_rijen, diepte, max_stapel)

        # Samenvatting van achter (muur) naar voor (gangpad)
        lijn_samenvatting = []
        for d in range(diepte):
            hoogtes_in_lijn = [grid[r][d] for r in range(aantal_rijen) if grid[r][d] > 0]
            if len(set(hoogtes_in_lijn)) == 1:
                lijn_samenvatting.append(f"Laag {d+1}: {hoogtes_in_lijn[0]}H")
            else:
                lijn_samenvatting.append(f"Laag {d+1}: {'/'.join(str(h)+'H' for h in hoogtes_in_lijn)}")
        uitleg_tekst = " | ".join(lijn_samenvatting)

        with kolom:
            st.markdown(f"#### {titel}")
            k1, k2 = st.columns(2)
            k1.metric("Rijen naast elkaar", f"{aantal_rijen} rijen", uitleg_tekst)
            k2.metric("Stapel-benutting", f"{benutting}%", f"{aantal_rijen * diepte} vloerplekken")

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


    teken_kant(col_a, "◀️ Kant A (3 diep)", 3, rijen_a, benutting_a)
    teken_kant(col_b, "▶️ Kant B (4 diep)", 4, rijen_b, benutting_b)

