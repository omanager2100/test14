import os
from openai import OpenAI

# API-Key sicher aus Umgebungsvariable laden
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def suggest_mapping_with_samples(df, artikel_df=None, max_rows=5):
    """
    Analysiert ein DataFrame und schlägt ein Mapping zu:
    sku, quantity, customer_id, description (und ggf. delivery_date) vor.
    Nutzt OpenAI GPT (z. B. gpt-3.5-turbo).
    """

    col_infos = []
    artikel_werte = set()
    if artikel_df is not None and "ARTNR1" in artikel_df.columns:
        artikel_werte = set(artikel_df["ARTNR1"].dropna().astype(str).str.strip())

    for col in df.columns:
        values = df[col].dropna().astype(str).str.strip().tolist()
        sample_values = values[:max_rows]
        match_score = sum(1 for v in sample_values if v in artikel_werte)
        unique_count = len(set(sample_values))
        beispiel_str = ", ".join(sample_values)
        col_infos.append(
            f"Spalte: '{col}' | Beispiele: {beispiel_str} | "
            f"Artikel-Matches: {match_score}/{len(sample_values)} | "
            f"Eindeutige Werte: {unique_count}"
        )

    prompt = f"""
Du analysierst eine Kunden-Bestellliste. Ordne jede Spalte einer der folgenden Ziel-Kategorien zu:

- sku (Artikelnummer → intern, d.h. muss mit Artikelstamm übereinstimmen)
- quantity (Menge)
- customer_id (Kundennummer)
- description (Artikelname)
- delivery_date (Lieferdatum, optional)

Nutze dazu auch die Anzahl von Artikelnummern-Matches mit dem Artikelstamm und die Einzigartigkeit der Werte.

Spaltenanalyse:
{chr(10).join(col_infos)}

Antworte NUR im JSON-Format, z. B.:
{{"sku": "Bestell-Nr", "quantity": "Anzahl", "customer_id": "Kunde", "description": "Artikel"}}
"""

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