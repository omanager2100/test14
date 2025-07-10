import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def suggest_mapping_with_samples(df, artikel_df=None, max_rows=5):
    """
    Analysiert ein DataFrame und schlägt ein Mapping zu:
    sku, quantity, customer_id, description (und ggf. delivery_date) vor.
    Nutzt OpenAI GPT (z. B. gpt-3.5-turbo).
    """

    col_infos = []
    artikel_werte = set()
    if artikel_df is not None and "ARTNR1" in artikel_df.columns:
        artikel_werte = set(artikel_df["ARTNR1"].dropna().astype(str).str.strip())

    for col in df.columns:
        values = df[col].dropna().astype(str).str.strip().tolist()
        sample_values = values[:max_rows]
        match_score = sum(1 for v in sample_values if v in artikel_werte)
        match_percent = round((match_score / max_rows) * 100) if max_rows > 0 else 0
        unique_count = len(set(sample_values))
        beispiel_str = ", ".join(sample_values)
        col_infos.append(
            f"Spalte: '{col}' | Beispiele: {beispiel_str} | "
            f"Artikel-Matches: {match_score}/{max_rows} ({match_percent}%) | "
            f"Eindeutige Werte: {unique_count}"
        )

    prompt = "\n".join([
        "Du analysierst eine Kunden-Bestellliste als DataFrame. Ordne jede Spalte einer der folgenden Ziel-Kategorien zu:",
        "",
        "- sku (interne Artikelnummer, muss möglichst stark mit ARTNR1-Liste aus Artikelstamm übereinstimmen)",
        "- quantity (Menge)",
        "- customer_id (Kundennummer)",
        "- description (Artikelname)",
        "- delivery_date (Lieferdatum, optional)",
        "",
        "Wähle als 'sku' NICHT die Spalte mit dem Namen 'Artikel-Nr.' nur weil es so heißt - entscheide nach inhaltlicher Übereinstimmung mit bekannten Artikeldaten (ARTNR1).",
        "",
        "Spaltenanalyse:",
        *col_infos,
        "",
        "Antworte **nur** im JSON-Format, z. B.:",
        '{"sku": "Bestell-Nr", "quantity": "Menge", "customer_id": "Kunde", "description": "Artikel"}'
    ])

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        message = response.choices[0].message.content
        return eval(message)
    except Exception as e:
        print("Fehler bei OpenAI:", e)
        return {}
