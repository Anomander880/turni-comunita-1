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
        # UNEBA: dalle 00:00 alle 06:00 è attesa (non si conta nel monte ore)
        # Se la notte è 20-08 (12h totali), togliamo le 6 ore centrali = 6h effettive
        ore_effettive = max(0, ore_totali - 6)
        return ore_totali, ore_effettive
    return ore_totali, ore_totali

# --- CONFIGURAZIONE ---
st.title("📅 Gestione Turni Comunità - H24 (Notte 20-08)")

staff = {"Antonella": 30, "Margherita": 30, "Marika": 30, "Antonio": 30, "Domenico": 30, "Claudio": 38, "Fabio": 12}
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# Slot aggiornati: 3 Mattine e 4 Pomeriggi (per gestire Claudio + Fabio + 2 educatori)
slot_turni = ["Mattina 1", "Mattina 2", "Mattina 3", "Pomeriggio 1", "Pomeriggio 2", "Pomeriggio 3", "Pomeriggio 4", "Notte"]
slot_extra = ["SMONTO", "RIPOSO"]
slot_nomi = slot_turni + slot_extra

DB_FILE = "dati_turni_v9.csv"

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
            
            # Orari di default aggiornati
            if "Mattina" in s:
                def_in = time(9,0) if scelta == "Claudio" else time(8,0)
                def_fi = time(14,0)
            elif "Pomeriggio" in s:
                def_in = time(14,0)
                # Claudio educatore finisce alle 16:00 o 19:00 a seconda del giorno, 
                # ma qui impostiamo il default generale a 20:00 per la nuova notte
                def_fi = time(20,0) 
            else: # Notte (Aggiornata alle 20:00)
                def_in = time(20,0)
                def_fi = time(8,0)
            
            c_ora1, c_ora2 = st.columns(2)
            ora_in = c_ora1.time_input("In", def_in, key=f"in_{gg}_{s}", label_visibility="collapsed")
            ora_fi = c_ora2.time_input("Out", def_fi, key=f"fi_{gg}_{s}", label_visibility="collapsed")
            
            is_notte = "Notte" in s
            h_tot, h_eff = calcola_durata(ora_in, ora_fi, sottrai_notturne=is_notte)
            
            if scelta != "Seleziona...":
                # Logica Claudio
                if scelta == "Claudio":
                    is_c = st.checkbox("Coord?", value=("Mattina" in s), key=f"c_{gg}_{s}")
                    if is_c: claudio_coord += h_eff
                    else: claudio_edu += h_eff
                
                # Conteggio presenze per alert
                if "Mattina" in s: presenze_mattina.append(scelta)
                if "Pomeriggio" in s: presenze_pomeriggio.append(scelta)
                
                ore_lavorate_settimana[scelta] += h_eff
                st.caption(f"{h_eff}h" if not is_notte else f"Eff: {h_eff}h (UNEBA)")
            st.divider()

        # Alert Compresenze aggiornati
        if len(presenze_mattina) > 2:
            st.warning(f"⚠️ Mattina: {len(presenze_mattina)} pers.")
        
        # Massimo 3 persone al pomeriggio (inclusi coordinatore ed educatore 12h)
        if len(presenze_pomeriggio) > 3:
            st.warning(f"⚠️ Pome: {len(presenze_pomeriggio)} pers. (Max 3)")

        st.info(f"**STATO {gg}**")
        for s in slot_extra:
            val_prec_ex = df_salvato.at[s, gg] if s in df_salvato.index else "Seleziona..."
            idx_ex = lista_nomi.index(val_prec_ex) if val_prec_ex in lista_nomi else 0
            st.selectbox(f"{s}", lista_nomi, index=idx_ex, key=f"p_{gg}_{s}")

# --- TASTI E REPORT ---
st.divider()
c1, c2 = st.columns(2)

with c1:
    if st.button("💾 SALVA CONFIGURAZIONE"):
        df_da_salvare = pd.DataFrame(index=slot_nomi, columns=giorni)
        for g in giorni:
            for s in slot_nomi:
                df_da_salvare.at[s, g] = st.session_state[f"p_{g}_{s}"]
        df_da_salvare.to_csv(DB_FILE)
        st.success("Dati salvati correttamente!")

with c2:
    output = io.BytesIO()
    df_export = pd.DataFrame(index=slot_nomi, columns=giorni)
    for g in giorni:
        for s in slot_nomi:
            df_export.at[s, g] = st.session_state[f"p_{g}_{s}"]
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Turni')
    st.download_button(label="📥 SCARICA EXCEL", data=output.getvalue(), file_name="turni_comunita_v9.xlsx")

# --- REPORT ORE ---
st.header("📊 Verifica Monte Ore Settimanale")
col_c1, col_c2 = st.columns(2)
with col_c1:
    colore_c = "green" if claudio_coord <= 15 else "red"
    st.markdown(f"#### Claudio Coordinamento: :{colore_c}[{round(claudio_coord,1)}h / 15h]")
with col_c2:
    colore_e = "green" if claudio_edu <= 23 else "orange"
    st.markdown(f"#### Claudio Educatore: :{colore_e}[{round(claudio_edu,1)}h / 23h]")

st.write("---")
r_cols = st.columns(len(staff))
for i, (nome, ore) in enumerate(ore_lavorate_settimana.items()):
    contratto = staff[nome]
    diff = round(ore-contratto, 2)
    # Colore basato sullo scostamento dal contratto
    color = "normal" if abs(diff) <= 1 else "inverse" 
    r_cols[i].metric(nome, f"{round(ore,1)}h", f"{diff}h", delta_color=color)
