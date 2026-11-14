import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.markdown("""
    <div class="modern-header">
        <div class="modern-title">MAGAZIJN STAPELING <span style="font-weight:400; font-size:1.3rem;">| Visueel op Pallets</span></div>
        <div class="modern-subtitle">Overzicht en stapelberekening per artikel (volledige lijnen gelijk, rest aan het gangpad)</div>
    </div>
""", unsafe_allow_html=True)

    mc1, mc2 = st.columns(2)
    with mc1:
        st.write("### 1. Aantal pallets van dit artikel:")
        aantal_stuks = st.number_input("Aantal pallets van dit artikel:", min_value=1, value=68, step=1, label_visibility="collapsed")
    with mc2:
        st.write("### 2. Max. stapelhoogte (lagen):")
        max_stapel = st.number_input("Max. stapelhoogte (lagen):", min_value=1, max_value=8, value=4, step=1, label_visibility="collapsed")

    def vul_gangpad_lijn(pallets, plekken, max_toegestane_h):
        lijn = * plekken
        if pallets <= 0 or plekken <= 0:
            return lijn

        # Gebruik zoveel mogelijk plekken op de gangpadlijn zodat er geen lege plekken overblijven als dat niet hoeft,
        # maar houd elke stapel minimaal 2H (tenzij er maar 1 pallet is) en nooit hoger dan max_toegestane_h
        max_bruikbare_plekken = min(plekken, pallets // 2) if pallets >= 2 else 1
        min_nodige_plekken = math.ceil(pallets / max_toegestane_h)
        k = max(min_nodige_plekken, max_bruikbare_plekken)
        k = min(k, plekken)

        if k > 0:
            basis = pallets // k
            extra = pallets % k
            if basis + (1 if extra > 0 else 0) <= max_toegestane_h:
                temp = [basis + 1] * extra + [basis] * (k - extra)
                for i, val in enumerate(temp):
                    lijn[i] = val
                return lijn

        # Fallback: vul van links naar rechts tot max_toegestane_h
        over = pallets
        for i in range(plekken):
            zet = min(max_toegestane_h, over)
            lijn[i] = zet
            over -= zet
            if over == 0:
                break
        return lijn

    def bereken_verdeling(totaal_pallets, max_h, diepte):
        min_plekken = math.ceil(totaal_pallets / max_h)
        aantal_rijen = math.ceil(min_plekken / diepte)
        totaal_plekken = aantal_rijen * diepte

        volle_lagen_max = min(diepte - 1, totaal_pallets // (aantal_rijen * max_h))
        pallets_achter = volle_lagen_max * aantal_rijen * max_h
        rest_pallets = totaal_pallets - pallets_achter

        achterste_lijnen = []
        for _ in range(volle_lagen_max):
            achterste_lijnen.extend([max_h] * aantal_rijen)

        hoogte_voorlaatste_lijn = max_h

        # Controleer of we de laatste volle lijn tegen de muur beter 1 niveau lager (bijv. 3H i.p.v. 4H) zetten
        # zodat de gangpadlijn ook goed gevuld is (en nooit hoger wordt dan de lijn erachter)
        if volle_lagen_max >= 1 and max_h >= 3 and rest_pallets > 0:
            nieuwe_rest = rest_pallets + aantal_rijen
            nieuwe_max_gangpad = max_h - 1
            if nieuwe_rest <= aantal_rijen * nieuwe_max_gangpad:
                huidige_plekken_nodig = math.ceil(rest_pallets / max_h)
                if huidige_plekken_nodig <= aantal_rijen // 2:
                    achterste_lijnen = ([max_h] * ((volle_lagen_max - 1) * aantal_rijen)) + ([nieuwe_max_gangpad] * aantal_rijen)
                    rest_pallets = nieuwe_rest
                    hoogte_voorlaatste_lijn = nieuwe_max_gangpad

        aantal_achterste_lijnen = len(achterste_lijnen) // aantal_rijen
        lege_tussenlijnen = (diepte - 1) - aantal_achterste_lijnen

        gangpad_lijn = vul_gangpad_lijn(rest_pallets, aantal_rijen, hoogte_voorlaatste_lijn)
        alle_hoogtes = achterste_lijnen + (* (lege_tussenlijnen * aantal_rijen)) + gangpad_lijn

        gebruikte_plekken = sum(1 for h in alle_hoogtes if h > 0)
        benutting = round((gebruikte_plekken / totaal_plekken) * 100)

        return aantal_rijen, benutting, gebruikte_plekken, totaal_plekken, alle_hoogtes

    rijen_a, benutting_a, gebr_a, tot_a, hoogtes_a = bereken_verdeling(aantal_stuks, max_stapel, 3)
    rijen_b, benutting_b, gebr_b, tot_b, hoogtes_b = bereken_verdeling(aantal_stuks, max_stapel, 4)

    if benutting_a > benutting_b:
        st.success(f"💡 **Beste keuze (strakste vulling): Kant A (3 diep)** — Je benut de rijen voor **{benutting_a}%** (tegenover {benutting_b}% aan Kant B), met **{rijen_a} rijen** (~{rijen_a * 1.20:.1f} m breed).")
    elif benutting_b > benutting_a:
        st.success(f"💡 **Beste keuze (strakste vulling): Kant B (4 diep)** — Je benut de rijen voor **{benutting_b}%** (tegenover {benutting_a}% aan Kant A), met **{rijen_b} rijen** (~{rijen_b * 1.20:.1f} m breed).")
    else:
        if rijen_b < rijen_a:
            st.success(f"💡 **Beste keuze (minste breedte): Kant B (4 diep)** — Beide kanten zijn **{benutting_b}%** gevuld, maar Kant B gebruikt maar **{rijen_b} rijen** (~{rijen_b * 1.20:.1f} m breed).")
        else:
            st.success(f"💡 **Beste keuze (minste breedte): Kant A (3 diep)** — Beide kanten zijn **{benutting_a}%** gevuld, met **{rijen_a} rijen** (~{rijen_a * 1.20:.1f} m breed).")

    col_a, col_b = st.columns(2)

    def teken_pallet_stapel(ax, x, y, breedte, hoogte, h_nu, max_h):
        if h_nu == 0:
            ax.add_patch(patches.Rectangle((x, y), breedte, hoogte, linewidth=1.2, linestyle="--", edgecolor="#94a3b8", facecolor="#f8fafc"))
            ax.text(x + breedte / 2, y + hoogte / 2, "Vrij", ha="center", va="center", fontweight="bold", fontsize=9, color="#94a3b8")
            return

        p_hoogte = hoogte * 0.20
        bovenplank_h = p_hoogte * 0.36
        klos_h = p_hoogte * 0.64

        ax.add_patch(patches.Rectangle((x, y + klos_h), breedte, bovenplank_h, linewidth=1, edgecolor="#5c3a21", facecolor="#c89d7c"))

        klos_b = breedte * 0.18
        for klos_x in [x, x + breedte / 2 - klos_b / 2, x + breedte - klos_b]:
            ax.add_patch(patches.Rectangle((klos_x, y), klos_b, klos_h, linewidth=1, edgecolor="#5c3a21", facecolor="#8d5b3c"))

        lading_y_start = y + p_hoogte
        beschikbare_hoogte = hoogte - p_hoogte
        totale_lading_h = beschikbare_hoogte * (h_nu / max_h)

        kleur_lading = "#1b5e20" if h_nu == max_h else "#2ecc71"
        tekst_kleur = "white" if h_nu == max_h else "black"

        ax.add_patch(patches.Rectangle((x, lading_y_start), breedte, totale_lading_h, linewidth=1, edgecolor="#144517", facecolor=kleur_lading))

        ax.text(x + breedte / 2, lading_y_start + totale_lading_h / 2, f"{h_nu}H", ha="center", va="center", fontweight="bold", fontsize=10, color=tekst_kleur)

    def teken_kant(kolom, titel, diepte, aantal_rijen, benutting, gebruikte_plekken, totaal_plekken, hoogtes):
        benodigde_meters = aantal_rijen * 1.20

        grid = [[0 for _ in range(diepte)] for _ in range(aantal_rijen)]
        idx = 0
        for d in range(diepte):
            for r in range(aantal_rijen):
                if idx < len(hoogtes):
                    grid[r][d] = hoogtes[idx]
                    idx += 1

        tellingen = []
        for h in range(max_stapel, 0, -1):
            aantal_h = hoogtes.count(h)
            if aantal_h > 0:
                tellingen.append(f"{aantal_h}x {h}H")
        uitleg_tekst = " + ".join(tellingen)

        with kolom:
            st.markdown(f"#### {titel}")
            k1, k2 = st.columns(2)
            k1.metric("Breedte (rijen naast elkaar)", f"{aantal_rijen} rijen (~{benodigde_meters:.1f} m)", uitleg_tekst)
            k2.metric("Vloerbenutting", f"{benutting}%", f"{gebruikte_plekken} van {totaal_plekken} plekken")

            stap_x = 1.12
            stap_y = 1.04
            breedte_fig = max(5.2, aantal_rijen * stap_x + 0.2)
            hoogte_fig = diepte * stap_y + 1.35
            fig, ax = plt.subplots(figsize=(breedte_fig, hoogte_fig))
            ax.set_xlim(0, aantal_rijen * stap_x + 0.15)
            ax.set_ylim(-0.45, diepte * stap_y + 0.65)
            ax.axis('off')

            ax.plot([0.1, aantal_rijen * stap_x], [diepte * stap_y + 0.35, diepte * stap_y + 0.35], color="#334155", linewidth=4)
            ax.text((aantal_rijen * stap_x) / 2, diepte * stap_y + 0.45, "🧱 MUUR (Achterkant)", ha="center", va="bottom", fontweight="bold", fontsize=10, color="#334155")

            ax.text((aantal_rijen * stap_x) / 2, -0.25, f"⬇️ GANGPAD — Breedte nodig: ~{benodigde_meters:.1f} meter ⬇️", ha="center", va="top", fontweight="bold", fontsize=10, color="#64748b")

            for r in range(aantal_rijen):
                x = 0.12 + r * stap_x
                ax.text(x + 0.46, diepte * stap_y + 0.08, f"Rij {r + 1}", ha="center", va="bottom", fontweight="bold", fontsize=10)

                for d in range(diepte):
                    y = (diepte - 1 - d) * stap_y + 0.02
                    teken_pallet_stapel(ax, x, y, 0.92, 0.94, grid[r][d], max_stapel)

            st.pyplot(fig, bbox_inches="tight")

    teken_kant(col_a, "◀️ Kant A (3 diep)", 3, rijen_a, benutting_a, gebr_a, tot_a, hoogtes_a)
    teken_kant(col_b, "▶️ Kant B (4 diep)", 4, rijen_b, benutting_b, gebr_b, tot_b, hoogtes_b)
