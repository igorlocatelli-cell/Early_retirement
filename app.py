"""
=====================================================================
 SIMULATORE FIRE ITALIA — Motore Monte Carlo Multivariato
=====================================================================
Istruzioni di installazione (terminale):

    pip install streamlit plotly numpy pandas

Esecuzione:

    streamlit run app.py

---------------------------------------------------------------------
NOTA IMPORTANTE
Questo strumento è un simulatore didattico/quantitativo. Le assunzioni
fiscali (bollo 0,20%, tassazione 26%/12,5%, aliquota Fondo Pensione
15%->9%) sono semplificazioni della normativa italiana e NON
costituiscono consulenza fiscale, previdenziale o finanziaria. Per
decisioni reali rivolgersi a un consulente finanziario indipendente
e/o a un commercialista.
=====================================================================
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# =====================================================================
# CONFIG PAGINA
# =====================================================================
st.set_page_config(
    page_title="FIRE Italia — Simulatore Monte Carlo",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Matrice di correlazione fissa tra i 5 fattori stocastici della Bucket Strategy:
# [Risk7 Moneyfarm, Immobiliare, Conto Deposito, Altro, Inflazione]
# Nota: il Fondo Pensione Moneyfarm (stesso profilo Rischio 7) condivide lo stesso
# fattore "Risk7 Moneyfarm" (correlazione 1:1), quindi non compare come fattore separato.
CORR = np.array([
    [1.00, 0.20, -0.05, 0.10, 0.10],
    [0.20, 1.00, 0.00, 0.10, 0.30],
    [-0.05, 0.00, 1.00, 0.10, 0.15],
    [0.10, 0.10, 0.10, 1.00, 0.00],
    [0.10, 0.30, 0.15, 0.00, 1.00],
])

# =====================================================================
# SIDEBAR — INPUT UTENTE
# =====================================================================
st.sidebar.title("🔥 Parametri FIRE")
st.sidebar.caption("Simulazione Monte Carlo multivariata per l'Early Retirement in Italia")

with st.sidebar.expander("👤 Anagrafica & Orizzonte Temporale", expanded=True):
    current_age = st.number_input("Età attuale", 18, 70, 40, step=1)
    fire_age = st.number_input("Età FIRE (uscita dal lavoro)", int(current_age) + 1, 80, 53, step=1)
    inps_age = st.number_input("Età pensione INPS", int(fire_age), 75, 67, step=1)
    life_exp = st.number_input("Aspettativa di vita", int(inps_age) + 1, 110, 90, step=1)

with st.sidebar.expander("💰 Contributi", expanded=True):
    annual_saving = st.number_input("Risparmio annuo pre-FIRE (€)", 0, step=500, value=18000)
    fp_contrib = st.number_input("Versamento annuo Fondo Pensione (€)", 0, 5165, 5164, step=1,
                                  help="Limite di deducibilità fiscale: 5.164,57 €/anno. Va ad alimentare "
                                       "il bucket 'Fondo Pensione Moneyfarm' definito più sotto.")

with st.sidebar.expander("📉 Spese & Entrate Future", expanded=True):
    target_expense = st.number_input("Spesa annua target post-FIRE (€, valore reale/odierno)",
                                      0, step=500, value=28000)
    inps_pension_month = st.number_input("Assegno INPS netto stimato (€/mese)", 0, step=50, value=1200)
    inps_pension_annual = inps_pension_month * 12
    st.caption(f"Pensione INPS annua stimata: **{inps_pension_annual:,.0f} €** dai {int(inps_age)} anni "
               f"(valore reale, si assume indicizzata all'inflazione)")

with st.sidebar.expander("🏠 Rendite Immobiliari", expanded=False):
    rental_annual = st.number_input("Rendita annua da immobile (€, valore reale)", 0, step=500, value=0)
    rental_start_age = st.number_input("Età inizio rendita immobiliare", int(current_age), int(life_exp),
                                        int(fire_age), step=1)
    rental_end_age = st.number_input("Età fine rendita immobiliare", int(rental_start_age), int(life_exp),
                                      int(life_exp), step=1)
    rental_tax = st.number_input("Aliquota cedolare secca %", 0.0, 50.0, 21.0, step=0.5) / 100

    st.divider()
    sale_amount = st.number_input("Vendita immobile una tantum (€, valore reale)", 0, step=5000, value=0)
    sale_age = st.number_input("Età della vendita", int(current_age), int(life_exp), int(fire_age), step=1)
    sale_tax = st.number_input("Aliquota tassazione plusvalenza vendita %", 0.0, 50.0, 0.0, step=0.5,
                                help="0% se prima casa o immobile posseduto da oltre 5 anni (tipicamente esente)") / 100

with st.sidebar.expander("🦢 Eventi Cigno Nero", expanded=False):
    n_black_swans = st.number_input("Numero atteso di cigni neri nell'orizzonte", 0, 10, 0, step=1,
                                     help="Eventi di crollo di mercato improvvisi e imprevedibili, distribuiti "
                                          "casualmente lungo l'intero orizzonte temporale di ogni simulazione")
    bs_impact_mean = st.number_input("Impatto medio sul rendimento annuo (%)", -80.0, 0.0, -35.0, step=1.0) / 100
    bs_impact_vol = st.number_input("Volatilità dell'impatto (%)", 0.0, 40.0, 10.0, step=1.0) / 100

with st.sidebar.expander("💼 Reddito da Lavoro Extra (part-time / P.IVA forfettaria)", expanded=False):
    work_income = st.number_input("Reddito annuo netto extra (€, valore reale)", 0, step=500, value=0)
    work_start_age = st.number_input("Età inizio reddito extra", int(current_age), int(life_exp),
                                      int(fire_age), step=1)
    work_end_age = st.number_input("Età fine reddito extra", int(work_start_age), int(life_exp),
                                    int(inps_age), step=1)

with st.sidebar.expander("🪣 Bucket Strategy — Patrimonio & Fondo Pensione", expanded=True):
    st.caption("**1️⃣ Portafoglio Moneyfarm (Rischio 7)**")
    mf_amount = st.number_input("Importo investito (€)", 0, step=5000, value=250000, key="mf_amt")
    cc1, cc2 = st.columns(2)
    with cc1:
        mf_ret = st.number_input("Rendimento atteso %", value=6.5, step=0.1, key="mf_ret") / 100
    with cc2:
        mf_vol = st.number_input("Volatilità %", value=16.0, step=0.1, key="mf_vol") / 100

    st.divider()
    st.caption("**2️⃣ Fondo Pensione Moneyfarm (Rischio 7)**")
    fp_mf_amount = st.number_input("Importo accumulato (€)", 0, step=1000, value=50000, key="fp_amt")
    cc3, cc4 = st.columns(2)
    with cc3:
        fp_mf_ret = st.number_input("Rendimento atteso %", value=6.0, step=0.1, key="fp_ret") / 100
    with cc4:
        fp_mf_vol = st.number_input("Volatilità %", value=15.0, step=0.1, key="fp_vol") / 100
    st.caption("Stesso profilo di rischio del portafoglio Moneyfarm → simulato con correlazione 1:1")

    st.divider()
    st.caption("**3️⃣ Investimento Immobiliare (es. Trusters)**")
    re_amount = st.number_input("Importo investito (€)", 0, step=5000, value=0, key="re_amt")
    cc5, cc6 = st.columns(2)
    with cc5:
        re_ret = st.number_input("Rendimento atteso %", value=5.0, step=0.1, key="re_ret") / 100
    with cc6:
        re_vol = st.number_input("Volatilità %", value=8.0, step=0.1, key="re_vol") / 100

    st.divider()
    st.caption("**4️⃣ Conto Deposito**")
    dep_amount = st.number_input("Importo depositato (€)", 0, step=1000, value=0, key="dep_amt")
    cc7, cc8 = st.columns(2)
    with cc7:
        dep_ret = st.number_input("Rendimento %", value=3.0, step=0.1, key="dep_ret") / 100
    with cc8:
        dep_vol = st.number_input("Volatilità %", value=0.5, step=0.1, key="dep_vol") / 100

    st.divider()
    st.caption("**5️⃣ Altro**")
    alt_amount = st.number_input("Importo (€)", 0, step=1000, value=0, key="alt_amt")
    cc9, cc10 = st.columns(2)
    with cc9:
        alt_ret = st.number_input("Rendimento %", value=2.0, step=0.1, key="alt_ret") / 100
    with cc10:
        alt_vol = st.number_input("Volatilità %", value=5.0, step=0.1, key="alt_vol") / 100

    st.divider()
    capital_gain_tax = st.number_input("Aliquota fiscale su plusvalenze/rendimenti %", 0.0, 50.0, 26.0, step=0.5,
                                        help="Applicata sulla quota di prelievo stimata come plusvalenza") / 100

    st.caption("**Inflazione**")
    ic1, ic2 = st.columns(2)
    with ic1:
        infl_mean = st.number_input("Inflazione media %", value=2.0, step=0.1) / 100
    with ic2:
        infl_vol = st.number_input("Volatilità inflazione %", value=1.2, step=0.1) / 100

    total_liquid = mf_amount + re_amount + dep_amount + alt_amount
    st.info(f"💼 Patrimonio liquido totale (esclusa Fondo Pensione): **{total_liquid:,.0f} €**\n\n"
            f"📐 Ordine di prelievo in decumulo: Conto Deposito → Altro → Portafoglio Moneyfarm → Immobiliare")

with st.sidebar.expander("⚙️ Parametri Simulazione", expanded=True):
    n_sims = st.slider("Numero simulazioni Monte Carlo", 1000, 10000, 5000, step=500)
    rule = st.selectbox("Regola di prelievo", ["SWR Fisso (spesa reale costante)", "Guardrails (Guyton-Klinger)"])
    gain_ratio = st.slider("Quota plusvalenza stimata sul prelievo (%)", 0, 100, 50,
                            help="Percentuale del prelievo lordo considerata plusvalenza tassabile "
                                 "(il resto è rimborso di capitale, non tassato)") / 100
    seed = st.number_input("Seed casuale (per riproducibilità)", 0, 999999, 42, step=1)

st.sidebar.divider()
st.sidebar.caption("⚠️ Strumento didattico. Non costituisce consulenza finanziaria, fiscale o previdenziale.")


# =====================================================================
# MOTORE MONTE CARLO (cache per evitare ricalcoli inutili)
# =====================================================================
@st.cache_data(show_spinner="⏳ Esecuzione simulazioni Monte Carlo in corso...")
def run_simulation(current_age, fire_age, inps_age, life_exp,
                    mf_amount, mf_ret, mf_vol,
                    fp_mf_amount, fp_mf_ret, fp_mf_vol, fp_contrib,
                    re_amount, re_ret, re_vol,
                    dep_amount, dep_ret, dep_vol,
                    alt_amount, alt_ret, alt_vol,
                    capital_gain_tax, annual_saving,
                    target_expense, inps_pension_annual,
                    infl_mean, infl_vol, n_sims, rule, gain_ratio, seed,
                    rental_annual, rental_start_age, rental_end_age, rental_tax,
                    sale_amount, sale_age, sale_tax,
                    n_black_swans, bs_impact_mean, bs_impact_vol,
                    work_income, work_start_age, work_end_age):

    rng = np.random.default_rng(int(seed))

    n_years_total = int(life_exp - current_age)
    n_acc_years = int(fire_age - current_age)

    # ---- Fattori stocastici correlati (standardizzati, media 0 / varianza 1) ----
    # ordine: Risk7 Moneyfarm, Immobiliare, Conto Deposito, Altro, Inflazione
    draws = rng.multivariate_normal(np.zeros(5), CORR, size=(n_sims, n_years_total))
    risk7_z, re_z, dep_z, alt_z, infl_z = (draws[:, :, i] for i in range(5))

    mf_return = mf_ret + mf_vol * risk7_z
    fp_return = fp_mf_ret + fp_mf_vol * risk7_z  # stesso profilo di rischio del Portafoglio Moneyfarm
    re_return = re_ret + re_vol * re_z
    dep_return = dep_ret + dep_vol * dep_z
    alt_return = alt_ret + alt_vol * alt_z
    infl_r = np.clip(infl_mean + infl_vol * infl_z, -0.5, None)

    # ---- CIGNI NERI: shock di crollo aggiuntivi distribuiti casualmente nell'orizzonte ----
    # Colpiscono i bucket collegati ai mercati finanziari (Moneyfarm, FP, Immobiliare in misura ridotta)
    bs_hit = np.zeros((n_sims, n_years_total), dtype=bool)
    if n_black_swans > 0 and n_years_total > 0:
        p_bs = min(n_black_swans / n_years_total, 1.0)
        bs_hit = rng.random((n_sims, n_years_total)) < p_bs
        bs_shock = rng.normal(bs_impact_mean, bs_impact_vol, size=(n_sims, n_years_total))
        mf_return = np.where(bs_hit, mf_return + bs_shock, mf_return)
        fp_return = np.where(bs_hit, fp_return + bs_shock, fp_return)
        re_return = np.where(bs_hit, re_return + bs_shock * 0.6, re_return)

    cum_infl = np.cumprod(1 + infl_r, axis=1)

    # ---- Stato dei bucket ----
    mf_w = np.full(n_sims, float(mf_amount))
    fp_w = np.full(n_sims, float(fp_mf_amount))
    re_w = np.full(n_sims, float(re_amount))
    dep_w = np.full(n_sims, float(dep_amount))
    alt_w = np.full(n_sims, float(alt_amount))

    wealth = np.zeros((n_sims, n_years_total + 1))
    wealth[:, 0] = mf_amount + re_amount + dep_amount + alt_amount

    withdrawals_nominal = np.zeros((n_sims, n_years_total))
    expenses_nominal = np.zeros((n_sims, n_years_total))
    pension_nominal_track = np.zeros((n_sims, n_years_total))
    rental_nominal_track = np.zeros((n_sims, n_years_total))
    work_nominal_track = np.zeros((n_sims, n_years_total))

    initial_wd_rate = None
    guardrail_mult = np.ones(n_sims)

    BOLLO = 0.002  # 0,20% imposta di bollo annua (non applicata al Conto Deposito, per semplicità)

    for t in range(n_years_total):
        age = current_age + t
        cum_i = cum_infl[:, t - 1] if t > 0 else np.ones(n_sims)

        # ---- Entrate extra valide in ogni fase: rendita immobiliare e lavoro extra ----
        rental_nom = np.where((age >= rental_start_age) & (age <= rental_end_age),
                               rental_annual * (1 - rental_tax) * cum_i, 0.0)
        work_nom = np.where((age >= work_start_age) & (age <= work_end_age),
                             work_income * cum_i, 0.0)

        # ---- Vendita immobile una tantum (si attiva una sola volta, all'età indicata) ----
        if age == sale_age:
            mf_w = mf_w + sale_amount * cum_i * (1 - sale_tax)

        if t < n_acc_years:
            # ---- FASE DI ACCUMULO: ogni bucket cresce col proprio rendimento ----
            mf_w = mf_w * (1 + mf_return[:, t]) * (1 - BOLLO) + annual_saving + rental_nom + work_nom
            fp_w = fp_w * (1 + fp_return[:, t]) + fp_contrib
            re_w = re_w * (1 + re_return[:, t]) * (1 - BOLLO)
            dep_w = dep_w * (1 + dep_return[:, t])
            alt_w = alt_w * (1 + alt_return[:, t]) * (1 - BOLLO)
        else:
            # ---- CONVERSIONE FONDO PENSIONE (una tantum, all'uscita FIRE) → confluisce nel bucket Moneyfarm ----
            if t == n_acc_years:
                years_contrib = max(n_acc_years, 1)
                fp_tax_rate = max(0.09, 0.15 - 0.003 * max(0, years_contrib - 15))
                mf_w = mf_w + fp_w * (1 - fp_tax_rate)
                fp_w = np.zeros(n_sims)

            # ---- FASE DI DECUMULO ----
            total_w_before = mf_w + re_w + dep_w + alt_w
            target_nom = target_expense * cum_i
            pension_nom = np.where(age >= inps_age, inps_pension_annual * cum_i, 0.0)
            total_income = pension_nom + rental_nom + work_nom

            need = np.maximum(target_nom - total_income, 0.0)

            if rule.startswith("Guardrails"):
                cur_rate = need / np.maximum(total_w_before, 1.0)
                if initial_wd_rate is None:
                    initial_wd_rate = cur_rate.copy()
                upper = initial_wd_rate * 1.20
                lower = initial_wd_rate * 0.80
                guardrail_mult = np.where(cur_rate > upper, guardrail_mult * 0.90, guardrail_mult)
                guardrail_mult = np.where(cur_rate < lower, guardrail_mult * 1.10, guardrail_mult)
                guardrail_mult = np.clip(guardrail_mult, 0.5, 1.5)
                need = need * guardrail_mult

            gross_need = need / (1 - gain_ratio * capital_gain_tax)

            # ---- WATERFALL DI PRELIEVO: Deposito → Altro → Moneyfarm → Immobiliare ----
            take_dep = np.minimum(gross_need, np.maximum(dep_w, 0.0))
            dep_w = dep_w - take_dep
            remaining = gross_need - take_dep

            take_alt = np.minimum(remaining, np.maximum(alt_w, 0.0))
            alt_w = alt_w - take_alt
            remaining = remaining - take_alt

            take_mf = np.minimum(remaining, np.maximum(mf_w, 0.0))
            mf_w = mf_w - take_mf
            remaining = remaining - take_mf

            take_re = np.minimum(remaining, np.maximum(re_w, 0.0))
            re_w = re_w - take_re
            remaining = remaining - take_re

            withdrawal_actual = gross_need - remaining

            # ---- crescita del residuo di ciascun bucket ----
            mf_w = np.maximum(mf_w, 0.0) * (1 + mf_return[:, t]) * (1 - BOLLO)
            re_w = np.maximum(re_w, 0.0) * (1 + re_return[:, t]) * (1 - BOLLO)
            dep_w = np.maximum(dep_w, 0.0) * (1 + dep_return[:, t])
            alt_w = np.maximum(alt_w, 0.0) * (1 + alt_return[:, t]) * (1 - BOLLO)

            withdrawals_nominal[:, t] = withdrawal_actual
            expenses_nominal[:, t] = target_nom
            pension_nominal_track[:, t] = pension_nom
            rental_nominal_track[:, t] = rental_nom
            work_nominal_track[:, t] = work_nom

        mf_w = np.maximum(mf_w, 0.0)
        re_w = np.maximum(re_w, 0.0)
        dep_w = np.maximum(dep_w, 0.0)
        alt_w = np.maximum(alt_w, 0.0)
        wealth[:, t + 1] = mf_w + re_w + dep_w + alt_w

    ages = np.arange(current_age, life_exp + 1)

    # Max drawdown per simulazione (sul percorso di patrimonio)
    running_max = np.maximum.accumulate(wealth, axis=1)
    running_max[running_max == 0] = 1.0
    drawdown = (wealth - running_max) / running_max
    max_dd_per_sim = drawdown.min(axis=1)

    return {
        "wealth": wealth,
        "ages": ages,
        "n_acc_years": n_acc_years,
        "n_years_total": n_years_total,
        "withdrawals": withdrawals_nominal,
        "expenses": expenses_nominal,
        "pension": pension_nominal_track,
        "rental": rental_nominal_track,
        "work": work_nominal_track,
        "cum_infl": cum_infl,
        "max_dd_per_sim": max_dd_per_sim,
        "bs_hit_count": bs_hit.sum(axis=1),
        "corr": CORR,
    }


results = run_simulation(
    current_age, fire_age, inps_age, life_exp,
    mf_amount, mf_ret, mf_vol,
    fp_mf_amount, fp_mf_ret, fp_mf_vol, fp_contrib,
    re_amount, re_ret, re_vol,
    dep_amount, dep_ret, dep_vol,
    alt_amount, alt_ret, alt_vol,
    capital_gain_tax, annual_saving,
    target_expense, inps_pension_annual,
    infl_mean, infl_vol, int(n_sims), rule, gain_ratio, int(seed),
    rental_annual, int(rental_start_age), int(rental_end_age), rental_tax,
    sale_amount, int(sale_age), sale_tax,
    int(n_black_swans), bs_impact_mean, bs_impact_vol,
    work_income, int(work_start_age), int(work_end_age),
)

wealth = results["wealth"]
ages = results["ages"]
n_acc_years = results["n_acc_years"]

# =====================================================================
# KPI
# =====================================================================
final_wealth = wealth[:, -1]
success_rate = float(np.mean(final_wealth > 0) * 100)

idx_inps = int(inps_age - current_age)
idx_inps = min(max(idx_inps, 0), wealth.shape[1] - 1)
median_wealth_inps = float(np.median(wealth[:, idx_inps]))
median_wealth_final = float(np.median(final_wealth))
median_max_dd = float(np.median(results["max_dd_per_sim"]) * 100)

# =====================================================================
# HEADER
# =====================================================================
st.title("🔥 Simulatore FIRE Italia")
st.caption("Piano di Early Retirement — Motore Monte Carlo multivariato con fiscalità italiana integrata")

k1, k2, k3, k4 = st.columns(4)
k1.metric("✅ Success Rate", f"{success_rate:.1f}%")
k2.metric(f"💼 Patrimonio Mediano a {int(inps_age)} anni", f"{median_wealth_inps:,.0f} €")
k3.metric(f"🏁 Patrimonio Mediano a {int(life_exp)} anni", f"{median_wealth_final:,.0f} €")
k4.metric("📉 Max Drawdown Mediano", f"{median_max_dd:.1f}%")

if n_black_swans > 0:
    avg_bs = float(np.mean(results["bs_hit_count"]))
    st.caption(f"🦢 In media ogni simulazione ha sperimentato **{avg_bs:.1f}** eventi di cigno nero "
               f"(atteso impostato: {int(n_black_swans)}).")

if success_rate < 80:
    st.warning(f"⚠️ Il tasso di successo ({success_rate:.1f}%) è sotto la soglia prudenziale dell'80%. "
               "Valuta di posticipare l'età FIRE, ridurre la spesa target o aumentare il risparmio.")
elif success_rate >= 95:
    st.success(f"✅ Piano molto solido: {success_rate:.1f}% delle simulazioni non esauriscono il patrimonio.")

st.divider()

tab1, tab2 = st.tabs(["📊 Dashboard", "🔍 Dettagli & Export"])

# =====================================================================
# TAB 1 — DASHBOARD
# =====================================================================
with tab1:
    st.subheader("📈 Traiettorie di Patrimonio (percentili)")
    percentiles = {p: np.percentile(wealth, p, axis=0) for p in [10, 25, 50, 75, 90]}

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=ages, y=percentiles[90], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig1.add_trace(go.Scatter(x=ages, y=percentiles[10], fill="tonexty", fillcolor="rgba(99,110,250,0.12)",
                               line=dict(width=0), name="Range 10°-90°", hoverinfo="skip"))
    fig1.add_trace(go.Scatter(x=ages, y=percentiles[75], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig1.add_trace(go.Scatter(x=ages, y=percentiles[25], fill="tonexty", fillcolor="rgba(99,110,250,0.25)",
                               line=dict(width=0), name="Range 25°-75°", hoverinfo="skip"))
    fig1.add_trace(go.Scatter(x=ages, y=percentiles[50], line=dict(color="#EF553B", width=3), name="Mediana (50°)"))

    fire_x = current_age + n_acc_years
    fig1.add_vline(x=fire_x, line_dash="dash", line_color="green", annotation_text="FIRE")
    fig1.add_vline(x=inps_age, line_dash="dash", line_color="gray", annotation_text="INPS")

    fig1.update_layout(xaxis_title="Età", yaxis_title="Patrimonio (€, nominale)",
                        hovermode="x unified", height=440, margin=dict(l=10, r=10, t=30, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig1, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📊 Distribuzione Patrimonio Finale")
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(x=final_wealth, nbinsx=60, marker_color="#636EFA", name="Distribuzione"))
        fig2.add_vline(x=float(np.mean(final_wealth)), line_color="orange", line_dash="dash",
                       annotation_text="Media")
        fig2.add_vline(x=0, line_color="red", line_width=2, annotation_text="Fallimento (€0)")
        fig2.update_layout(xaxis_title=f"Patrimonio a {int(life_exp)} anni (€)", yaxis_title="Frequenza",
                            height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.subheader("💶 Spese, Prelievi e Pensione (valori reali)")
        dec_slice = slice(n_acc_years, results["n_years_total"])
        ages_dec = ages[n_acc_years:results["n_years_total"]]

        cum_i_dec = np.maximum(results["cum_infl"][:, dec_slice], 1e-6)
        real_expense = np.median(results["expenses"][:, dec_slice] / cum_i_dec, axis=0)
        real_withdrawal = np.median(results["withdrawals"][:, dec_slice] / cum_i_dec, axis=0)
        real_pension = np.median(results["pension"][:, dec_slice] / cum_i_dec, axis=0)
        real_rental = np.median(results["rental"][:, dec_slice] / cum_i_dec, axis=0)
        real_work = np.median(results["work"][:, dec_slice] / cum_i_dec, axis=0)

        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=ages_dec, y=real_withdrawal, name="Prelievo da portafoglio", marker_color="#636EFA"))
        fig3.add_trace(go.Bar(x=ages_dec, y=real_pension, name="Pensione INPS", marker_color="#00CC96"))
        fig3.add_trace(go.Bar(x=ages_dec, y=real_rental, name="Rendita immobiliare", marker_color="#FFA15A"))
        fig3.add_trace(go.Bar(x=ages_dec, y=real_work, name="Reddito lavoro extra", marker_color="#AB63FA"))
        fig3.add_trace(go.Scatter(x=ages_dec, y=real_expense, name="Spesa target", line=dict(color="black", dash="dot")))
        fig3.update_layout(barmode="stack", xaxis_title="Età", yaxis_title="€/anno (valore reale)",
                            height=400, margin=dict(l=10, r=10, t=30, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig3, use_container_width=True)

    st.caption("Il 'bridge' pre-INPS corrisponde agli anni tra l'uscita FIRE e l'età pensionabile, in cui l'intera "
               "spesa target grava sul portafoglio privato; dai {} anni la pensione INPS riduce il prelievo necessario."
               .format(int(inps_age)))

# =====================================================================
# TAB 2 — DETTAGLI & EXPORT
# =====================================================================
with tab2:
    st.subheader("🔗 Matrice di Correlazione (fattori stocastici)")
    corr_df = pd.DataFrame(results["corr"],
                            index=["Risk7 Moneyfarm", "Immobiliare", "Conto Deposito", "Altro", "Inflazione"],
                            columns=["Risk7 Moneyfarm", "Immobiliare", "Conto Deposito", "Altro", "Inflazione"])
    st.dataframe(corr_df.style.format("{:.2f}"), use_container_width=True)

    st.subheader("📋 Percorso Mediano Anno per Anno")
    median_path = np.median(wealth, axis=0)
    p10_path = np.percentile(wealth, 10, axis=0)
    p90_path = np.percentile(wealth, 90, axis=0)

    df_years = pd.DataFrame({
        "Età": ages,
        "Fase": ["Accumulo" if a < fire_age else ("Bridge (pre-INPS)" if a < inps_age else "Post-INPS") for a in ages],
        "Patrimonio Mediano (€)": np.round(median_path, 0),
        "Patrimonio 10° perc. (€)": np.round(p10_path, 0),
        "Patrimonio 90° perc. (€)": np.round(p90_path, 0),
    })
    st.dataframe(df_years, use_container_width=True, height=350)

    csv_years = df_years.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Scarica percorso mediano (CSV)", data=csv_years,
                        file_name="fire_simulazione_percorso_mediano.csv", mime="text/csv")

    st.subheader("🧮 Export Simulazioni Complete")
    st.caption(f"Matrice completa {wealth.shape[0]} simulazioni × {wealth.shape[1]} anni "
               "(può essere pesante da scaricare con molte simulazioni).")
    full_df = pd.DataFrame(wealth, columns=[f"età_{a}" for a in ages])
    csv_full = full_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Scarica matrice completa simulazioni (CSV)", data=csv_full,
                        file_name="fire_simulazione_completa.csv", mime="text/csv")

    st.divider()
    st.markdown("""
    **Assunzioni metodologiche principali:**
    - Ogni bucket (Portafoglio Moneyfarm, Fondo Pensione Moneyfarm, Immobiliare, Conto Deposito, Altro) cresce con un proprio rendimento stocastico, generato da fattori normali correlati (Portafoglio e Fondo Pensione Moneyfarm condividono lo stesso fattore "Rischio 7", correlazione 1:1).
    - Imposta di bollo dello 0,20% applicata annualmente sul controvalore dei bucket Moneyfarm, Immobiliare e Altro (esclusa, per semplificazione, dal Conto Deposito).
    - Tassazione plusvalenze: aliquota unica configurabile (default 26%) applicata sulla quota di prelievo stimata come plusvalenza.
    - Fondo Pensione: liquidato in un'unica soluzione all'uscita FIRE, tassato con aliquota decrescente dal 15% (fino a 15 anni di versamento) al 9% (oltre 35 anni), il netto confluisce nel bucket Portafoglio Moneyfarm.
    - Ordine di prelievo in decumulo (bucket strategy a cascata): Conto Deposito → Altro → Portafoglio Moneyfarm → Immobiliare (il meno liquido, prelevato per ultimo).
    - Pensione INPS attivata all'età impostata, assunta indicizzata all'inflazione in termini reali.
    - Regola "Guardrails": taglio del 10% della spesa se il tasso di prelievo corrente supera del 20% quello iniziale; incremento del 10% se scende sotto il 20%.
    - Rendita immobiliare: importo reale annuo tra le età impostate, tassato con cedolare secca configurabile; riduce il prelievo necessario dal portafoglio negli anni di decumulo, si aggiunge al risparmio negli anni di accumulo.
    - Vendita immobile una tantum: importo reale accreditato al bucket Portafoglio Moneyfarm nell'anno dell'età impostata, al netto dell'aliquota di plusvalenza configurata.
    - Cigni neri: in ciascuna simulazione, ogni anno ha una probabilità pari a (numero atteso / durata orizzonte) di subire uno shock di rendimento aggiuntivo sui bucket collegati ai mercati finanziari (Moneyfarm, Fondo Pensione, Immobiliare in misura ridotta), con impatto medio e volatilità configurabili.
    - Reddito da lavoro extra (part-time/P.IVA forfettaria): importo netto reale tra le età impostate, riduce il prelievo necessario durante il bridge pre-INPS, si aggiunge al risparmio se percepito prima del FIRE.
    """)
