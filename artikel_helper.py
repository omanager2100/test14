import pandas as pd

def enrich_missing_data(df, artikel_df, kunden_nr_eingabe=None):
    artikel_df = artikel_df.copy()
    artikel_df.columns = artikel_df.columns.str.upper()
    artikel_dict = artikel_df.set_index("ARTNR1").to_dict(orient="index")

    def enrich_row(row):
        artnr = str(row.get("sku", "")).strip()  # Wichtig: verwende die Spalte nach Mapping
        if artnr in artikel_dict:
            referenz = artikel_dict[artnr]
            # Beschreibung ergänzen
            if str(row.get("description", "")).strip().lower() in ["", "nicht bekannt", "nan", "none"]:
                row["description"] = referenz.get("ABEZ1", "")
            # EAN ergänzen
            if "EAN" in referenz and ("ean" not in row or pd.isna(row["ean"]) or row["ean"] == ""):
                row["ean"] = referenz.get("EAN", "")

            # Mengenumrechnung prüfen
            me = str(referenz.get("ME", "")).lower()
            try:
                anz_basis = float(referenz.get("ANZ_BASIS", 0))
                quantity = float(row.get("quantity", 0))
            except:
                anz_basis = 0
                quantity = 0

            if me == "kg" and anz_basis > 0:
                original_qty = quantity
                korrigiert = quantity / anz_basis
                row["quantity"] = round(korrigiert, 3)
                row["korrektur_hinweis"] = f"von {original_qty} Stück → {row['quantity']} kg (Basis: {anz_basis})"
        return row

    df = df.apply(enrich_row, axis=1)

    # Kundennummer ergänzen
    if kunden_nr_eingabe:
        if "customer_id" not in df.columns:
            df["customer_id"] = kunden_nr_eingabe
        else:
            df["customer_id"] = df["customer_id"].fillna("").replace("", kunden_nr_eingabe)

    return df

