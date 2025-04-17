import streamlit as st
import pandas as pd
import datetime
# --- Remova essas linhas ---
# import streamlit_authenticator as stauth
# import yaml
# -------------------------------

# --- Autenticação simples ---
st.sidebar.header("🔒 Login")
username = st.sidebar.text_input("Usuário")
password = st.sidebar.text_input("Senha", type="password")
if username != "admin" or password != "admin123":
    st.sidebar.error("Usuário ou senha incorretos")
    st.stop()

# --- O resto do app permanece igual ---
st.title('Sistema PCP - Roteiros de Produção')
# ...


# --- Title ---
st.title('Sistema PCP - Roteiros de Produção')

# --- File upload ---
uploaded_file = st.file_uploader('Carregar base Excel', type=['xlsx','xlsm','xlsb'])
if not uploaded_file:
    st.info('Por favor, carregue um arquivo Excel')
    st.stop()

# --- Read Excel ---
@st.cache_data
def load_data(file):
    import os
    fname = file.name.lower()
    if fname.endswith('.xlsb'):
        xls = pd.ExcelFile(file, engine='pyxlsb')
    else:
        xls = pd.ExcelFile(file)
    pedidos = xls.parse('Pedidos_Gerais')
    skus    = xls.parse('Base_SKUs')
    # concatena data+hora (ajuste nomes de colunas conforme seu Excel)
    pedidos['Timestamp'] = pd.to_datetime(pedidos['DataEntrada'].astype(str) + ' ' + pedidos['HoraEntrada'].astype(str))
    return pedidos, skus


# --- Settings ---
st.sidebar.header('Configuração de Cortes')
cut_rp1 = datetime.time(16,30)
cut_rp2 = datetime.time(10,30)
cut_rp3 = datetime.time(15,30)

today = datetime.date.today()

def generate_rp(pedidos, flag_col, cutoff_datetime):
    # filter not yet generated and before cutoff
    df = pedidos[(pedidos[flag_col]!=True) & (pedidos['Timestamp']<=cutoff_datetime)].copy()
    # mark
    pedidos.loc[df.index, flag_col] = True
    return df

# --- Initialize flags ---
for col in ['Gerado_RP1','Gerado_RP2','Gerado_RP3']:
    if col not in pedidos.columns:
        pedidos[col] = False

# --- Generate Roteiros ---
st.header('Geração de Roteiros')
if st.button('Gerar RP1'):
    dt1 = datetime.datetime.combine(today - datetime.timedelta(days=1), cut_rp1)
    rp1 = generate_rp(pedidos, 'Gerado_RP1', dt1)
    st.success(f'RP1 gerado: {len(rp1)} pedidos')
    st.dataframe(rp1)

if st.button('Gerar RP2'):
    dt2 = datetime.datetime.combine(today, cut_rp2)
    rp2 = generate_rp(pedidos, 'Gerado_RP2', dt2)
    st.success(f'RP2 gerado: {len(rp2)} pedidos')
    st.dataframe(rp2)

if st.button('Gerar RP3'):
    dt3 = datetime.datetime.combine(today, cut_rp3)
    rp3 = generate_rp(pedidos, 'Gerado_RP3', dt3)
    st.success(f'RP3 gerado: {len(rp3)} pedidos')
    st.dataframe(rp3)

# --- Download updated database ---
st.header('Banco Atualizado')
buffer = pd.ExcelWriter('db_atualizado.xlsx', engine='xlsxwriter')
pedidos.to_excel(buffer, index=False, sheet_name='Pedidos_Gerais')
skus.to_excel(buffer, index=False, sheet_name='Base_SKUs')
buffer.save()
st.download_button('Baixar base atualizada', 'db_atualizado.xlsx')
