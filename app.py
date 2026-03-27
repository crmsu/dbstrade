import streamlit as st
import pandas as pd
from pandas.errors import EmptyDataError, ParserError

# -------------------------------------------------------
# CONFIGURAZIONE BASE, COLORI E LOGO
# -------------------------------------------------------

st.set_page_config(
    layout="wide",
    page_title="Dashboard Interventi – Strade Provinciali"
)

LOGO_URL = (
    "https://provincia-sulcis-iglesiente-api.cloud.municipiumapp.it/"
    "s3/150x150/s3/20243/sito/stemma.jpg"
)

PRIMARY_HEX = "#6BE600"
PRIMARY_LIGHT = "#A8FF66"
PRIMARY_EXTRA_LIGHT = "#E8FFE0"

# Header con logo + titolo
col_logo, col_title = st.columns([1, 6])

with col_logo:
    st.image(LOGO_URL, width=70)

with col_title:
    st.markdown(
        """
        # Dashboard interventi – Strade provinciali
        Monitoraggio interventi su viabilità e infrastrutture stradali.
        """
    )

st.markdown("---")

# -------------------------------------------------------
# FUNZIONI DI SUPPORTO
# -------------------------------------------------------

@st.cache_data
def load_data(uploaded_file=None):
    """
    Carica il CSV delle strade provinciali con schema STRD_CMPLSS
    e restituisce un DataFrame pulito.
    """
    try:
        if uploaded_file is not None:
            df = pd.read_csv(
                uploaded_file,
                sep=";",
                decimal=",",
                encoding="utf-8",
                on_bad_lines="skip"
            )
        else:
            default_path = "STR_Strade-Provinciali-STRD_CMPLSS.csv"
            df = pd.read_csv(
                default_path,
                sep=";",
                decimal=",",
                encoding="utf-8",
                on_bad_lines="skip"
            )
    except FileNotFoundError:
        st.error(
            "File CSV non trovato. Carica il file "
            "STR_Strade-Provinciali-STRD_CMPLSS.csv."
        )
        return pd.DataFrame()
    except (EmptyDataError, ParserError):
        st.error("Errore nella lettura del file CSV. Verifica il formato del file.")
        return pd.DataFrame()

    rename_map
