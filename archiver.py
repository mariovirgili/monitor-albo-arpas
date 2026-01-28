import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import hashlib
import time

# --- Configurazione ---
TARGET_URL = "https://www.sardegnaambiente.it/arpas/arpas/albopretorio/"
BASE_DOMAIN = "https://www.sardegnaambiente.it"
DATA_DIR = "archive_data"
PDF_DIR = os.path.join(DATA_DIR, "pdfs")
HTML_DIR = os.path.join(DATA_DIR, "html_snapshots")
MEMO_DIR = os.path.join(DATA_DIR, "memos")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

# Assicura che le directory necessarie esistano
for d in [DATA_DIR, PDF_DIR, HTML_DIR, MEMO_DIR]:
    os.makedirs(d, exist_ok=True)

def load_history():
    """Carica la cronologia dei download da un file JSON."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    """Salva la cronologia dei download su un file JSON."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def get_filename_from_url(url):
    """Genera un nome file sicuro partendo da un URL."""
    # Usa l'MD5 dell'URL per garantire unicità e gestire stringhe complesse
    hash_object = hashlib.md5(url.encode())
    return f"{hash_object.hexdigest()}.pdf"

def download_file(url, filepath):
    """Scarica un file da un URL in un percorso specifico."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Errore durante il download di {url}: {e}")
        return False

def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"--- Avvio Job di Archiviazione: {today_str} ---")

    # 1. Recupera il contenuto della pagina principale
    try:
        response = requests.get(TARGET_URL, timeout=30)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"Errore Critico: Impossibile recuperare la pagina principale. {e}")
        return

    # 2. Salva l'istantanea HTML giornaliera (copia grezza)
    snapshot_filename = f"albo_{today_str}.html"
    snapshot_path = os.path.join(HTML_DIR, snapshot_filename)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Salvata istantanea HTML in {snapshot_path}")

    # 3. Analizza il contenuto e trova i documenti
    soup = BeautifulSoup(html_content, 'html.parser')
    history = load_history()
    
    new_items = []
    
    # Logica: Cerca tutti i tag 'a' (link).
    # Adatta i filtri in base alla struttura specifica del sito.
    # Pattern comune: link che finiscono in .pdf o contengono testo specifico.
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href']
        text = link.get_text(" ", strip=True)
        
        # Filtro: Cerchiamo link ai documenti.
        # Spesso identificati dall'estensione o da parole chiave nel testo come "[file.pdf]"
        is_document = False
        if href.lower().endswith('.pdf'):
            is_document = True
        elif "file.pdf" in text.lower():
            is_document = True
            
        # A volte i link sono relativi, li standardizziamo
        if href.startswith('/'):
            full_url = BASE_DOMAIN + href
        elif href.startswith('http'):
            full_url = href
        else:
            # Salta javascript: o ancore interne
            continue

        if is_document:
            # Controllo duplicati (se l'abbiamo già scaricato in passato)
            if full_url not in history:
                print(f"Trovato nuovo documento: {text}")
                
                # Crea un nome file locale univoco
                local_filename = f"{today_str}_{get_filename_from_url(full_url)}"
                local_path = os.path.join(PDF_DIR, local_filename)
                
                # Esegui il download
                if download_file(full_url, local_path):
                    # Aggiorna la Cronologia
                    history[full_url] = {
                        "first_seen": today_str,
                        "local_path": local_filename,
                        "link_text": text
                    }
                    
                    # Aggiungi al report giornaliero
                    new_items.append({
                        "text": text,
                        "url": full_url,
                        "file": local_filename
                    })
                    
                    # Pausa per essere gentili con il server
                    time.sleep(1) 

    # 4. Salva la cronologia aggiornata su disco
    save_history(history)

    # 5. Compila il Memo Giornaliero
    memo_filename = f"Memo_{today_str}.txt"
    memo_path = os.path.join(MEMO_DIR, memo_filename)
    
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(f"MEMO GIORNALIERO - {today_str}\n")
        f.write(f"Fonte: {TARGET_URL}\n")
        f.write("="*40 + "\n\n")
        
        if new_items:
            f.write(f"Totale Nuovi Documenti: {len(new_items)}\n\n")
            for item in new_items:
                f.write(f"Titolo: {item['text']}\n")
                f.write(f"URL: {item['url']}\n")
                f.write(f"Salvato come: {item['file']}\n")
                f.write("-" * 20 + "\n")
        else:
            f.write("Nessun nuovo documento trovato oggi.\n")
            
    print(f"Job completato. Memo salvato in {memo_path}")

if __name__ == "__main__":
    main()
