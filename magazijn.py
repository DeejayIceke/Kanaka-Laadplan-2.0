import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.markdown("""
    <div class="modern-header">
        <div class="modern-title">MAGAZIJN STAPELING <span style="font-weight:400; font-size:1.3rem;">| Vooraanzicht</span></div>
        <div class="modern-subtitle">Overzicht vanuit het gangpad &amp; benodigde breedte</div>
    </div>
""", unsafe_allow_html=True)

    mc1, mc2 = st.columns(2)
    with mc1:
        st.write("### 1. Aantal pallets van dit artikel:")
        aantal_stuks = st.number_input("Aantal pallets van dit artikel:", min_value=1, value=48, step=1, label_visibility="collapsed")
    with mc2:
        st.write("### 2. Max. stapelhoogte (lagen):")
        max_stapel = st.number_input("Max. stapelhoogte (lagen):", min_value=1, max_value=8, value=2, step=1, label_visibility="collapsed")

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
        st.success(f"💡 **Beste keuze (minste breedte): Kant B (4 diep)** — Je gebruikt maar **{rijen_b} rijen naast elkaar** (~{rijen_b * 1.20:.1f} m breed, tegenover {rijen_a} rijen aan Kant A).")
    elif rijen_a < rijen_b:
        st.success(f"💡 **Beste keuze (minste breedte): Kant A (3 diep)** — Je gebruikt maar **{rijen_a} rijen naast elkaar** (~{rijen_a * 1.20:.1f} m breed, tegenover {rijen_b} rijen aan Kant B).")
    else:
        if benutting_a >= benutting_b:
            st.success(f"💡 **Beste keuze: Kant A (3 diep)** — Beide kanten gebruiken **{rijen_a} rijen breed** (~{rijen_a * 1.20:.1f} m), maar Kant A benut de rijen strakker ({benutting_a}% tegenover {benutting_b}%).")
        else:
            st.success(f"💡 **Beste keuze: Kant B (4 diep)** — Beide kanten gebruiken **{rijen_b} rijen breed** (~{rijen_b * 1.20:.1f} m), maar Kant B benut de rijen strakker ({benutting_b}% tegenover {benutting_a}%).")

    col_a, col_b = st.columns(2)
    def teken_enkele_pallet_laag(ax, x, y, breedte, hoogte, kleur_lading):
        p_hoogte = hoogte * 0.24
        bovenplank_h = p_hoogte * 0.36
        klos_h = p_hoogte * 0.64

        # Houten pallet onderaan de laag
        ax.add_patch(patches.Rectangle((x, y + klos_h), breedte, bovenplank_h, linewidth=1, edgecolor="#5c3a21", facecolor="#c89d7c"))
        klos_b = breedte * 0.18
        for klos_x in [x, x + breedte / 2 - klos_b / 2, x + breedte - klos_b]:
            ax.add_patch(patches.Rectangle((klos_x, y), klos_b, klos_h, linewidth=1, edgecolor="#5c3a21", facecolor="#8d5b3c"))

        # Lading op deze pallet
        lading_y = y + p_hoogte
        lading_h = hoogte - p_hoogte
        ax.add_patch(patches.Rectangle((x, lading_y), breedte, lading_h, linewidth=1, edgecolor="#144517", facecolor=kleur_lading))

    def teken_kant(kolom, titel, diepte, aantal_rijen, benutting):
        totaal_plekken = aantal_rijen * diepte
        lege_plekken = [0] * (totaal_plekken - len(basis_hoogtes))
        hoogtes = basis_hoogtes + lege_plekken

        benodigde_meters = aantal_rijen * 1.20

        # Grid opbouwen: [rij][diepte]
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
            k1.metric("Breedte (rijen naast elkaar)", f"{aantal_rijen} rijen (~{benodigde_meters:.1f} m)", uitleg_tekst)
            k2.metric("Vloerbenutting", f"{benutting}%", f"{totaal_vloerplaatsen} van {totaal_plekken} plekken")

            stap_x = 1.10
            laag_h = 0.85
            breedte_fig = max(5.2, aantal_rijen * stap_x + 0.3)
            hoogte_fig = max(2.8, max_stapel * laag_h + 1.2)
            fig, ax = plt.subplots(figsize=(breedte_fig, hoogte_fig))
            ax.set_xlim(0, aantal_rijen * stap_x + 0.2)
            ax.set_ylim(-0.45, max_stapel * laag_h + 0.75)
            ax.axis('off')

            # Vloerlijn onderaan
            ax.plot([0.08, aantal_rijen * stap_x + 0.08], [0, 0], color="#334155", linewidth=3)
            ax.text((aantal_rijen * stap_x + 0.16) / 2, -0.22, f"⬅️ Vooraanzicht vanuit gangpad — Breedte nodig: ~{benodigde_meters:.1f} m ({diepte} diep) ➡️", ha="center", va="top", fontweight="bold", fontsize=9.5, color="#475569")

            for r in range(aantal_rijen):
                x = 0.12 + r * stap_x
                # Aantal gevulde stapels achter elkaar in deze rij
                gevuld_in_rij = sum(1 for h in grid[r] if h > 0)
                hoogte_vooraan = max(grid[r]) if gevuld_in_rij > 0 else 0

                # Titel boven de rij (Rijnummer + hoeveel diep gevuld)
                ax.text(x + 0.46, max_stapel * laag_h + 0.15, f"Rij {r + 1}\n({gevuld_in_rij}/{diepte} diep)", ha="center", va="bottom", fontweight="bold", fontsize=8.5, color="#1e293b")

                if hoogte_vooraan == 0:
                    ax.add_patch(patches.Rectangle((x, 0.02), 0.92, laag_h - 0.04, linewidth=1.2, linestyle="--", edgecolor="#94a3b8", facecolor="#f8fafc"))
                    ax.text(x + 0.46, laag_h / 2, "Vrij", ha="center", va="center", fontweight="bold", fontsize=9, color="#94a3b8")
                else:
                    kleur = "#1b5e20" if hoogte_vooraan == max_stapel else "#2ecc71"
                    tekst_kleur = "white" if hoogte_vooraan == max_stapel else "black"
                    for laag in range(hoogte_vooraan):
                        y = laag * laag_h + 0.02
                        teken_enkele_pallet_laag(ax, x, y, 0.92, laag_h - 0.03, kleur)
                        ax.text(x + 0.46, y + (laag_h * 0.62), f"Laag {laag + 1}", ha="center", va="center", fontweight="bold", fontsize=8, color=tekst_kleur)

            st.pyplot(fig, bbox_inches="tight")

    teken_kant(col_a, "◀️ Kant A (3 diep)", 3, rijen_a, benutting_a)
    teken_kant(col_b, "▶️ Kant B (4 diep)", 4, rijen_b, benutting_b)
