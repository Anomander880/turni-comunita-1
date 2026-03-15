import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Gestione Turni Comunità", layout="wide")

# --- FUNZIONI DI CALCOLO ---
def calcola_durata(inizio, fine, sottrai_notturne=False):
    """Calcola le ore tra due orari, gestendo il superamento della mezzanotte."""
    t1 = datetime.combine(datetime.today(), inizio)
    t2 = datetime.combine(datetime.today(), fine)
    if t2 <= t1:
        t2 += timedelta(days=1)
    
    ore_totali = (t2 - t1).total_seconds() / 3600
    
    if sottrai_notturne:
        # Sottrae le 6 ore di attesa (00:00 - 06:00) se il turno le comprende
        ore_effettive = max(0, ore_totali - 6)
        return ore_totali, ore_effettive
    return ore_totali, ore_totali

# --- CONFIGURAZIONE ---
st.title("📅 Gestione Turni - Pomeriggio a 3 Postazioni")

staff = {"Antonella": 30, "Margherita": 30, "Marika": 30, "Antonio": 30, "Domenico": 30, "Claudio": 38, "Fabio": 12}
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# AGGIUNTO: Pomeriggio 3
slot_nomi = ["Mattina 1", "Mattina 2", "Pomeriggio 1", "Pomeriggio 2", "Pomeriggio 3", "Notte"]

DB_FILE = "dati_turni_v5.csv"

# Caricamento dati persistenti
if os.path.exists(DB_FILE):
    df_salvato = pd.read_csv(DB_FILE, index_col=0)
else:
    df_salvato = pd.DataFrame("Seleziona...", index=slot_nomi, columns=giorni)

# --- INTERFACCIA ---
ore_lavorate_settimana = {nome: 0.0 for nome in staff.keys()}
claudio_coord = 0.0
claudio_edu = 0.0

cols = st.columns(7)

for i, gg in enumerate(giorni):
    with cols[i]:
        st.error(f"### {gg}")
        for s in slot_nomi:
            st.markdown(f"**{s}**")
            
            # 1. Selezione Educatore
            val_prec = df_salvato.at[s, gg] if s in df_salvato.index else "Seleziona..."
            lista_nomi = ["Seleziona..."] + list(staff.keys())
            idx_prec = lista_nomi.index(val_prec) if val_prec in lista_nomi else 0
            scelta = st.selectbox(f"Chi?", lista_nomi, index=idx_prec, key=f"p_{gg}_{s}", label_visibility="collapsed")
            
            # 2. Selezione Orari
            def_in = time(7,0) if "Mattina" in s else time(14,0) if "Pomeriggio" in s else time(22,0)
            def_fi = time(14,0) if "Mattina" in s else time(22,0) if "Pomeriggio" in s else time(7,0)
            
            c_ora1, c_ora2 = st.columns(2)
            ora_in = c_ora1.time_input("Inizio", def_in, key=f"in_{gg}_{s}", label_visibility="collapsed")
            ora_fi = c_ora2.time_input("Fine", def_fi, key=f"fi_{gg}_{s}", label_visibility="collapsed")
            
            # 3. Calcolo ore
            is_notte = "Notte" in s
            h_tot, h_eff = calcola_durata(ora_in, ora_fi, sottrai_notturne=is_notte)
            
            # 4. Opzioni Speciali Claudio
            if scelta == "Claudio":
                is_c = st.checkbox("Coord?", value=True, key=f"c_{gg}_{s}")
                if is_c: claudio_coord += h_eff
                else: claudio_edu += h_eff
            
            if scelta != "Seleziona...":
                ore_lavorate_settimana[scelta] += h_eff
                if is_notte:
                    st.caption(f"Ore: {h_tot} (Eff: {h_eff})")
                else:
                    st.caption(f"Ore: {h_eff}")
            
            st.divider()

if st.button("💾 SALVA CONFIGURAZIONE SETTIMANALE"):
    df_da_salvare = pd.DataFrame(index=slot_nomi, columns=giorni)
    for g in giorni:
        for s in slot_nomi:
            df_da_salvare.at[s, g] = st.session_state[f"p_{g}_{s}"]
    df_da_salvare.to_csv(DB_FILE)
    st.success("Turni salvati con successo!")

# --- REPORT FINALE ---
st.divider()
st.header("📊 Resoconto Ore Effettive")
st.info("💡 Notte: calcolo automatico ore attive (totale meno 6 ore di attesa).")

r_cols = st.columns(len(staff))
for i, (nome, ore) in enumerate(ore_lavorate_settimana.items()):
    contratto = staff[nome]
    r_cols[i].metric(nome, f"{ore}h", f"{ore-contratto}h vs contr.")

st.warning(f"🔎 **Focus Claudio:** {claudio_coord}h Coordinamento | {claudio_edu}h Educatore")
