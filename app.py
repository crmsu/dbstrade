import streamlit as st
import pandas as pd
from io import BytesIO
from pandas.errors import EmptyDataError, ParserError

# Provo a importare reportlab solo se disponibile
try:
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4

    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    REPORTLAB_AVAILABLE = False

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

    rename_map = {
        "n.pgr": "n_pgr",
        "Nome Strada": "nome_strada",
        "codice": "codice",
        "Centro di costo": "centro_costo",
        "Denominazione intervento": "denominazione_intervento",
        "Determina": "determina",
        "Tipologia di intervento": "tipologia_intervento",
        "Stato della procedura": "stato_procedura",
        "RUP": "rup",
        "importo stanziato": "importo_stanziato",
        "Avviati?": "avviati",
        "PTLLPP": "ptllpp",
        "importo stimato": "importo_stimato",
        "Anno rif": "anno_rif",
        "CUP": "cup",
        "stato intervento - ultim atto": "stato_intervento_ultim_atto",
    }
    df = df.rename(columns=rename_map)

    def parse_importo(series):
        return (
            series.astype(str)
            .str.replace("€", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .replace({"": None})
            .astype(float)
        )

    if "importo_stanziato" in df.columns:
        df["importo_stanziato"] = parse_importo(df["importo_stanziato"])

    if "importo_stimato" in df.columns:
        df["importo_stimato"] = parse_importo(df["importo_stimato"])

    if "anno_rif" in df.columns:
        df["anno_rif"] = (
            df["anno_rif"]
            .astype(str)
            .str.extract(r"(\d{4})", expand=False)
            .astype("Int64")
        )

    for col in [
        "nome_strada",
        "codice",
        "centro_costo",
        "denominazione_intervento",
        "determina",
        "tipologia_intervento",
        "stato_procedura",
        "rup",
        "avviati",
        "ptllpp",
        "cup",
        "stato_intervento_ultim_atto",
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def apply_filters(df):
    """
    Applica i filtri scelti in sidebar e restituisce il dataframe filtrato.
    """
    if df.empty:
        return df

    with st.sidebar:
        st.header("Filtri")

        anni_disponibili = (
            df["anno_rif"].dropna().unique().tolist()
            if "anno_rif" in df.columns
            else []
        )
        anni_disponibili = sorted(anni_disponibili)

        if anni_disponibili:
            anno_min = int(min(anni_disponibili))
            anno_max = int(max(anni_disponibili))
            anno_range = st.slider(
                "Anno di riferimento",
                min_value=anno_min,
                max_value=anno_max,
                value=(anno_min, anno_max),
                step=1,
            )
        else:
            anno_range = None

        tipologie = (
            df["tipologia_intervento"].dropna().unique().tolist()
            if "tipologia_intervento" in df.columns
            else []
        )
        tipologia_sel = st.multiselect(
            "Tipologia di intervento",
            options=sorted(tipologie),
            default=sorted(tipologie),
        ) if tipologie else []

        stati_proc = (
            df["stato_procedura"].dropna().unique().tolist()
            if "stato_procedura" in df.columns
            else []
        )
        stato_proc_sel = st.multiselect(
            "Stato della procedura",
            options=sorted(stati_proc),
            default=sorted(stati_proc),
        ) if stati_proc else []

        rups = (
            df["rup"].dropna().unique().tolist()
            if "rup" in df.columns
            else []
        )
        rup_sel = st.multiselect(
            "RUP",
            options=sorted(rups),
            default=sorted(rups),
        ) if rups else []

        strada_text = st.text_input(
            "Ricerca per nome strada / codice",
            value="",
            help="Filtro testuale su nome strada o codice."
        )

    mask = pd.Series(True, index=df.index)

    if anno_range and "anno_rif" in df.columns:
        mask &= df["anno_rif"].between(anno_range[0], anno_range[1])

    if tipologia_sel and "tipologia_intervento" in df.columns:
        mask &= df["tipologia_intervento"].isin(tipologia_sel)

    if stato_proc_sel and "stato_procedura" in df.columns:
        mask &= df["stato_procedura"].isin(stato_proc_sel)

    if rup_sel and "rup" in df.columns:
        mask &= df["rup"].isin(rup_sel)

    if strada_text:
        strada_text_low = strada_text.lower()
        conds = []
        if "nome_strada" in df.columns:
            conds.append(df["nome_strada"].str.lower().str.contains(strada_text_low))
        if "codice" in df.columns:
            conds.append(df["codice"].str.lower().str.contains(strada_text_low))
        if conds:
            text_mask = conds[0]
            for c in conds[1:]:
                text_mask |= c
            mask &= text_mask

    return df[mask]


def build_pdf(df_filt) -> bytes:
    """
    Genera un PDF riepilogativo degli interventi filtrati.
    Restituisce il contenuto del PDF come bytes.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    # Titolo
    story.append(Paragraph("Provincia del Sud Sardegna", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Riepilogo interventi – Strade provinciali", styles["Heading2"]))
    story.append(Spacer(1, 12))

    # Info sintetiche
    n_interventi = len(df_filt)
    importo_tot = df_filt["importo_stanziato"].sum() if "importo_stanziato" in df_filt.columns else 0
    story.append(Paragraph(f"Numero interventi selezionati: {n_interventi}", styles["Normal"]))
    story.append(Paragraph(f"Importo stanziato complessivo (se presente): {importo_tot:,.2f} €", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Tabella principale (campi chiave)
    cols = [
        "n_pgr",
        "nome_strada",
        "codice",
        "denominazione_intervento",
        "tipologia_intervento",
        "stato_procedura",
        "rup",
        "anno_rif",
        "importo_stanziato",
    ]
    existing_cols = [c for c in cols if c in df_filt.columns]

    table_data = [existing_cols]
    for _, row in df_filt[existing_cols].iterrows():
        r = []
        for c in existing_cols:
            val = row[c]
            if pd.isna(val):
                r.append("")
            elif c in ["importo_stanziato"]:
                try:
                    r.append(f"{float(val):,.2f} €")
                except Exception:
                    r.append(str(val))
            else:
                r.append(str(val))
        table_data.append(r)

    table = Table(table_data, repeatRows=1)
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]
    )
    table.setStyle(table_style)

    story.append(table)

    doc.build(story)
    pdf_value = buffer.getvalue()
    buffer.close()
    return pdf_value


# -------------------------------------------------------
# MAIN APP
# -------------------------------------------------------

def main():
    st.sidebar.header("Dati interventi – Strade provinciali")

    uploaded_file = st.sidebar.file_uploader(
        "Carica il file STR_Strade-Provinciali-STRD_CMPLSS.csv",
        type=["csv"],
        help="Il file deve avere lo schema aggiornato (separatore ';')."
    )

    df = load_data(uploaded_file)

    if df.empty:
        st.warning(
            "Nessun dato disponibile. Carica un file CSV valido per procedere."
        )
        return

    df_filt = apply_filters(df)

    st.subheader("Anteprima dati filtrati")
    st.caption(f"Interventi selezionati: {len(df_filt)}")
    st.dataframe(df_filt, use_container_width=True)

    st.markdown("---")

    col_sx, col_dx = st.columns(2)

    with col_sx:
        st.subheader("Totali economici per tipologia")
        if (
            "tipologia_intervento" in df_filt.columns and
            "importo_stanziato" in df_filt.columns
        ):
            agg_tip = (
                df_filt.groupby("tipologia_intervento", dropna=False)["importo_stanziato"]
                .sum()
                .reset_index()
                .sort_values("importo_stanziato", ascending=False)
            )
            st.bar_chart(
                agg_tip,
                x="tipologia_intervento",
                y="importo_stanziato",
                use_container_width=True,
            )
            st.dataframe(agg_tip, use_container_width=True)
        else:
            st.info(
                "Dati non sufficienti per calcolare i totali per tipologia "
                "(manca tipologia_intervento o importo_stanziato)."
            )

    with col_dx:
        st.subheader("Totali economici per anno di riferimento")
        if (
            "anno_rif" in df_filt.columns and
            "importo_stanziato" in df_filt.columns
        ):
            agg_anno = (
                df_filt.groupby("anno_rif", dropna=False)["importo_stanziato"]
                .sum()
                .reset_index()
                .sort_values("anno_rif")
            )
            st.line_chart(
                agg_anno,
                x="anno_rif",
                y="importo_stanziato",
                use_container_width=True,
            )
            st.dataframe(agg_anno, use_container_width=True)
        else:
            st.info(
                "Dati non sufficienti per calcolare i totali per anno "
                "(manca anno_rif o importo_stanziato)."
            )

    st.markdown("---")
    st.subheader("Esportazioni")

    csv = df_filt.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Scarica dati filtrati in CSV",
        data=csv,
        file_name="interventi_strade_filtrati.csv",
        mime="text/csv",
    )

    if REPORTLAB_AVAILABLE and not df_filt.empty:
        pdf_bytes = build_pdf(df_filt)
        st.download_button(
            "Scarica riepilogo PDF (interventi filtrati)",
            data=pdf_bytes,
            file_name="riepilogo_interventi_strade.pdf",
            mime="application/pdf",
        )
    elif not REPORTLAB_AVAILABLE:
        st.info(
            "Report PDF non disponibile: il modulo 'reportlab' non è installato "
            "nell'ambiente di esecuzione."
        )


if __name__ == "__main__":
    main()
