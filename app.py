import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, time
import io

st.set_page_config(page_title="Gestione Turni Comunità", layout="wide")

# --- FUNZIONI DI CALCOLO ---
def calcola_durata(inizio, fine, sottrai_notturne=False):
    t1 = datetime.combine(datetime.today(), inizio)
    t2 = datetime.combine(datetime.today(), fine)
    if t2 <= t1:
        t2 += timedelta(days=1)
    ore_totali = (t2 - t1).total_seconds() / 3600
    if sottrai_notturne:
        # Contratto UNEBA: dalle 00:00 alle 06:00 ore di attesa (non contate)
        # Notte 20-08 = 12h totali - 6h attesa = 6h effettive
        ore_effettive = max(0, ore_totali - 6)
        return ore_totali, ore_effettive
    return ore_totali, ore_totali

# --- CONFIGURAZIONE ---
st.title("📅 Gestione Turni Comunità - Versione con Pomeriggio 4")

staff = {"Antonella": 30, "Margherita": 30, "Marika": 30, "Antonio": 30, "Domenico": 30, "Claudio": 38, "Fabio": 12}
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# AGGIORNAMENTO: 4 slot per il pomeriggio
slot_turni = [
    "Mattina 1", "Mattina 2", "Mattina 3", 
    "Pomeriggio 1", "Pomeriggio 2", "Pomeriggio 3", "Pomeriggio 4", 
    "Notte"
]
slot_extra = ["SMONTO", "RIPOSO"]
slot_nomi = slot_turni + slot_extra

DB_FILE = "dati_turni_v_finale.csv"

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
    presenze_mattina = []
    presenze_pomeriggio = []
    
    with cols[i]:
        st.error(f"### {gg}")
        
        for s in slot_turni:
            st.markdown(f"**{s}**")
            val_prec = df_salvato.at[s, gg] if s in df_salvato.index else "Seleziona..."
            lista_nomi = ["Seleziona..."] + list(staff.keys())
            idx_prec = lista_nomi.index(val_prec) if val_prec in lista_nomi else 0
            
            scelta = st.selectbox(f"Chi?", lista_nomi, index=idx_prec, key=f"p_{gg}_{s}", label_visibility="collapsed")
            
            # Impostazione orari di default
            if "Mattina" in s:
                def_in, def_fi = (time(9,0), time(14,0)) if scelta == "Claudio" else (time(8,0), time(14,0))
            elif "Pomeriggio" in s:
                # Default a 20:00 perché la notte inizia alle 20:00
                def_in, def_fi = (time(14,0), time(20,0))
            else: # Notte 20-08
                def_in, def_fi = (time(20,0), time(8,0))
            
            c_ora1, c_ora2 = st.columns(2)
            ora_in = c_ora1.time_input("In", def_in, key=f"in_{gg}_{s}", label_visibility="collapsed")
            ora_fi = c_ora2.time_input("Out", def_fi, key=f"fi_{gg}_{s}", label_visibility="collapsed")
            
            is_notte = "Notte" in s
            h_tot, h_eff = calcola_durata(ora_in, ora_fi, sottrai_notturne=is_notte)
            
            if scelta != "Seleziona...":
                if scelta == "Claudio":
                    is_c = st.checkbox("Coord?", value=("Mattina" in s), key=f"c_{gg}_{s}")
                    if is_c: claudio_coord += h_eff
                    else: claudio_edu += h_eff
                
                if "Mattina" in s: presenze_mattina.append(scelta)
                if "Pomeriggio" in s: presenze_pomeriggio.append(scelta)
                
                ore_lavorate_settimana[scelta] += h_eff
                st.caption(f"{h_eff}h" if not is_notte else f"Eff: {h_eff}h (UNEBA)")
            st.divider()

        # Alert Compresenze (Rigoroso: Max 3 al pomeriggio)
        if len(presenze_mattina) > 2:
            st.warning(f"⚠️ Mattina: {len(presenze_mattina)} pers.")
        
        if len(presenze_pomeriggio) > 3:
            st.warning(f"⚠️ Pome: {len(presenze_pomeriggio)} pers! (Max 3)")

        st.info(f"**STATO {gg}**")
        for s in slot_extra:
            val_prec_ex = df_salvato.at[s, gg] if s in df_salvato.index else "Seleziona..."
            idx_ex = lista_nomi.index(val_prec_ex) if val_prec_ex in lista_nomi else 0
            st.selectbox(f"{s}", lista_nomi, index=idx_ex, key=f"p_{gg}_{s}")

# --- SALVATAGGIO E REPORT ---
st.divider()
c1, c2 = st.columns(2)

with c1:
    if st.button("💾 SALVA TURNI"):
        df_da_salvare = pd.DataFrame(index=slot_nomi, columns=giorni)
        for g in giorni:
            for s in slot_nomi:
                df_da_salvare.at[s, g] = st.session_state[f"p_{g}_{s}"]
        df_da_salvare.to_csv(DB_FILE)
        st.success("Configurazione salvata!")

with c2:
    output = io.BytesIO()
    df_export = pd.DataFrame(index=slot_nomi, columns=giorni)
    for g in giorni:
        for s in slot_nomi:
            df_export.at[s, g] = st.session_state[f"p_{g}_{s}"]
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Turni_Comunita')
    st.download_button(label="📥 EXPORT EXCEL", data=output.getvalue(), file_name="turni_v_finale.xlsx")

# --- MONITORAGGIO ORE ---
st.header("📊 Resoconto Ore Settimanali")
r_cols = st.columns(len(staff))
for i, (nome, ore) in enumerate(ore_lavorate_settimana.items()):
    contratto = staff[nome]
    diff = round(ore-contratto, 1)
    r_cols[i].metric(nome, f"{round(ore,1)}h", f"{diff}h vs contr.")

st.info(f"Claudio: Coordinamento {round(claudio_coord,1)}h / Educatore {round(claudio_edu,1)}h")
