import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def toon_magazijn_tab():
    st.subheader("🏭 Magazijn Stapeling (Volledige partij aan één kant)")

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        aantal_stuks = st.number_input("Aantal pallets van dit artikel:", min_value=1, value=50, step=1)
    with mc2:
        max_stapel = st.number_input("Max. stapelhoogte (lagen):", min_value=1, max_value=8, value=3, step=1)
    with mc3:
        vrij_kant_a = st.number_input("Vrije rijen Kant A (3 diep):", min_value=0, value=6, step=1)
    with mc4:
        vrij_kant_b = st.number_input("Vrije rijen Kant B (4 diep):", min_value=0, value=6, step=1)

    totaal_vloerplaatsen = math.ceil(aantal_stuks / max_stapel)
    volle_stapels = aantal_stuks // max_stapel
    rest_hoogte = aantal_stuks % max_stapel

    nodig_rijen_a = math.ceil(totaal_vloerplaatsen / 3)
    nodig_rijen_b = math.ceil(totaal_vloerplaatsen / 4)

    loze_plekken_a = (nodig_rijen_a * 3) - totaal_vloerplaatsen
    loze_plekken_b = (nodig_rijen_b * 4) - totaal_vloerplaatsen

    past_a = nodig_rijen_a <= vrij_kant_a
    past_b = nodig_rijen_b <= vrij_kant_b

    if past_a and past_b:
        if loze_plekken_a < loze_plekken_b:
            beste_kant = "A"
            reden = f"slechts {loze_plekken_a} lege plek(ken) over in de laatste rij (tegenover {loze_plekken_b} aan Kant B)."
        elif loze_plekken_b < loze_plekken_a:
            beste_kant = "B"
            reden = f"slechts {loze_plekken_b} lege plek(ken) over in de laatste rij (tegenover {loze_plekken_a} aan Kant A)."
        else:
            beste_kant = "B"
            reden = f"evenveel lege plekken ({loze_plekken_b}), maar minder rijen nodig ({nodig_rijen_b} i.p.v. {nodig_rijen_a})."
        st.success(f"💡 **Beste keuze: Kant {beste_kant} ({'3 diep' if beste_kant == 'A' else '4 diep'}).** Volledige partij blijft samen met {reden}")
    elif past_a:
        beste_kant = "A"
        st.success(f"💡 **Beste keuze: Kant A (3 diep).** Volledige partij past hier in **{nodig_rijen_a} van de {vrij_kant_a} rijen**.")
    elif past_b:
        beste_kant = "B"
        st.success(f"💡 **Beste keuze: Kant B (4 diep).** Volledige partij past hier in **{nodig_rijen_b} van de {vrij_kant_b} rijen**.")
    else:
        beste_kant = "A"
        st.error(f"❌ **Past niet volledig aan één kant!** Nodig: **{nodig_rijen_a} rijen** aan Kant A of **{nodig_rijen_b} rijen** aan Kant B.")

    keuze_weergave = st.radio(
        "Weergave van gekozen kant:",
        [f"Kant A — 3 diep (Nodig: {nodig_rijen_a} | Vrij: {vrij_kant_a})", f"Kant B — 4 diep (Nodig: {nodig_rijen_b} | Vrij: {vrij_kant_b})"],
        index=0 if beste_kant == "A" else 1,
        horizontal=True
    )

    is_kant_a = "Kant A" in keuze_weergave
    diepte = 3 if is_kant_a else 4
    vrije_rijen = vrij_kant_a if is_kant_a else vrij_kant_b
    nodige_rijen = nodig_rijen_a if is_kant_a else nodig_rijen_b
    loze_plekken = loze_plekken_a if is_kant_a else loze_plekken_b
    te_tekenen_rijen = max(vrije_rijen, nodige_rijen, 1)

    stapel_uitleg = f"{volle_stapels}x {max_stapel}H" + (f" + 1x {rest_hoogte}H" if rest_hoogte > 0 else "")
    k1, k2, k3 = st.columns(3)
    k1.metric("Benodigde rijen", f"{nodige_rijen} rijen", f"Alles samen aan Kant {'A (3 diep)' if is_kant_a else 'B (4 diep)'}")
    k2.metric("Vloerplaatsen bezet", f"{totaal_vloerplaatsen} plekken", stapel_uitleg)
    k3.metric("Onbenutte plekken in rij", f"{loze_plekken} plekken", f"Nog {max(0, vrije_rijen - nodige_rijen)} rijen vrij")

    fig_mag, ax_mag = plt.subplots(figsize=(10, max(2.2, te_tekenen_rijen * 0.75)))
    ax_mag.set_xlim(0, diepte + 1.5)
    ax_mag.set_ylim(0, te_tekenen_rijen * 1.15)
    ax_mag.axis('off')

    stapel_lijst = [max_stapel] * volle_stapels + ([rest_hoogte] if rest_hoogte > 0 else [])
    plek_idx = 0

    for r in range(te_tekenen_rijen):
        y = (te_tekenen_rijen - 1 - r) * 1.15 + 0.1
        rij_past = r < vrije_rijen
        rij_label = f"Rij {r + 1}" if rij_past else f"Rij {r + 1} (TEKORT)"
        ax_mag.text(0, y + 0.45, rij_label, va="center", fontweight="bold", fontsize=10, color="black" if rij_past else "#e74c3c")

        for d in range(diepte):
            x = 1.3 + d * 0.95
            if plek_idx < len(stapel_lijst):
                h_nu = stapel_lijst[plek_idx]
                plek_idx += 1
                kleur = "#e74c3c" if not rij_past else ("#1b5e20" if h_nu == max_stapel else "#2ecc71")
                tekst_kleur = "white" if (not rij_past or h_nu == max_stapel) else "black"
                label = f"{h_nu}H"
            else:
                kleur = "#e2e8f0"
                tekst_kleur = "#64748b"
                label = "Vrij"

            ax_mag.add_patch(patches.Rectangle((x, y), 0.85, 0.85, linewidth=1.5, edgecolor="black", facecolor=kleur))
            ax_mag.text(x + 0.425, y + 0.425, label, ha="center", va="center", fontweight="bold", fontsize=10, color=tekst_kleur)

    st.pyplot(fig_mag)
