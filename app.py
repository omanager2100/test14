import streamlit as st
import pandas as pd
import os
import csv
from io import StringIO
from gpt_mapper import suggest_mapping_with_samples
from artikel_helper import enrich_missing_data

st.set_page_config(page_title="Kunden-Orderlisten Umwandler mit Artikelabgleich", layout="wide")
st.title("📦 Kunden-Orderlisten Umwandler mit Artikelabgleich")

uploaded_file = st.file_uploader("📁 Kunden-Bestelldatei (.xlsx oder .csv)", type=["xlsx", "csv"])
kunden_input = st.text_input("📝 Kundennummer (optional):")
apply_customer = st.button("🔁 Auf alle Zeilen anwenden")

# Datei robust einlesen
def read_input_file(uploaded_file):
    try:
        if uploaded_file.name.endswith(".csv"):
            sample = uploaded_file.read(2048).decode("utf-8", errors="ignore")
            uploaded_file.seek(0)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            sep = dialect.delimiter
            df = pd.read_csv(uploaded_file, sep=sep, engine="python", on_bad_lines="skip")
        else:
            df = pd.read_excel(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Fehler beim Einlesen der Datei: {e}")
        return None

# Hauptlogik
if uploaded_file is not None:
    df = read_input_file(uploaded_file)
    if df is not None:
        st.success(f"📥 Datei erfolgreich geladen: {uploaded_file.name}")
        st.subheader("📄 Vorschau der Datei")
        st.dataframe(df.head())

        # GPT-Vorschlag anzeigen
        if st.button("🧠 GPT-Mapping-Vorschlag anzeigen"):
            with st.spinner("Analysiere Struktur mit GPT..."):
                try:
                    artikel_df = pd.read_csv("artikel.csv", sep=";", encoding="utf-8")
                    mapping = suggest_mapping_with_samples(df, artikel_df)
                    st.session_state["mapping"] = mapping
                except:
                    st.error("Artikel.csv konnte nicht gelesen werden.")

        # Manuelles Mapping
        if "mapping" in st.session_state:
            st.subheader("🛠 Spalten-Mapping überprüfen/bearbeiten")
            new_mapping = {}
            for field in ["customer_id", "sku", "description", "quantity"]:
                new_mapping[field] = st.selectbox(
                    f"{field} zuordnen:",
                    df.columns.tolist(),
                    index=df.columns.get_loc(st.session_state["mapping"].get(field)) if st.session_state["mapping"].get(field) in df.columns else 0
                )
            st.session_state["mapping"] = new_mapping

            # Spalten umbenennen
            mapped_df = df.rename(columns={
                new_mapping["customer_id"]: "customer_id",
                new_mapping["sku"]: "sku",
                new_mapping["description"]: "description",
                new_mapping["quantity"]: "quantity"
            })[["customer_id", "sku", "description", "quantity"]]

            # Optional: Kundennummer auf alle anwenden
            if apply_customer and kunden_input:
                mapped_df["customer_id"] = kunden_input

            # Zeilen mit leerer SKU entfernen
            mapped_df = mapped_df[mapped_df["sku"].notna() & (mapped_df["sku"].astype(str).str.strip() != "")]

            # Artikeldaten laden & EAN ergänzen
            try:
                artikel_df = pd.read_csv("artikel.csv", sep=";", encoding="utf-8")
                artikel_df.columns = artikel_df.columns.str.upper()
                enrich = artikel_df.set_index("ARTNR1").to_dict(orient="index")

                def add_ean(row):
                    sku = str(row.get("sku", "")).strip()
                    if sku in enrich:
                        row["ean_me"] = enrich[sku].get("EAN", "")
                    return row

                mapped_df = mapped_df.apply(add_ean, axis=1)
                mapped_df = enrich_missing_data(mapped_df, artikel_df, kunden_nr_eingabe=None)

            except Exception as e:
                st.warning(f"Artikelstammdaten konnten nicht geladen werden: {e}")

            # Anzeige + Export
            spalten_export = ["customer_id", "sku", "ean_me", "description", "quantity"]
            spalten_anzeige = spalten_export + (["korrektur_hinweis"] if "korrektur_hinweis" in mapped_df.columns else [])

            st.subheader("📋 Ergebnis nach Anreicherung")
            st.dataframe(mapped_df[spalten_anzeige])

            csv_out = mapped_df[spalten_export].to_csv(index=False).encode("utf-8")
            st.download_button("📤 Ergebnis herunterladen", csv_out, "konvertierte_bestellung.csv", "text/csv")
