import os
import requests
from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
import json
import hashlib
import time
import re

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
    """Carica la cronologia dei download dal file JSON."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    """Salva la cronologia dei download nel file JSON."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def clean_filename_from_title(title):
    """
    Genera un nome file pulito basato sul titolo del documento e la sua data.
    Rimuove etichette come [file.pdf] e gestisce il formato della data.
    """
    # 1. Pulizia Aggressiva (Regex): Rimuove qualsiasi variante di [file.pdf]
    clean_title = re.sub(r"\[\s*file.*?pdf\s*\]?", "", title, flags=re.IGNORECASE).strip()
    
    # Fallback predefinito: Usa la data di oggi se non si trova una data nel testo
    file_date_prefix = datetime.now().strftime("%Y-%m-%d")
    
    # 2. Estrae la data (gg/mm/aaaa) dal titolo pulito
    date_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", clean_title)
    
    if date_match:
        day, month, year = date_match.groups()
        # Crea la data in formato ISO: AAAA-MM-GG
        file_date_prefix = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # 3. Rimuove la data e la parola "del" dal titolo per evitare duplicazioni
        clean_title = re.sub(r"\s*(del)?\s*" + re.escape(date_match.group(0)), "", clean_title, flags=re.IGNORECASE)

    # 4. Sanifica il titolo rimanente per il filesystem
    clean_title = re.sub(r'[\\/*?:"<>|]', "", clean_title)
    clean_title = clean_title.replace(" ", "_")
    clean_title = re.sub(r"_+", "_", clean_title)
    clean_title = clean_title.strip("_. ")

    return f"{file_date_prefix}_{clean_title}.pdf"

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

def get_description_after_link(link_element):
    """
    Tenta di recuperare il testo descrittivo che segue immediatamente il link.
    Es. <a...>Titolo</a>: DESCRIZIONE...
    """
    description = ""
    next_node = link_element.next_sibling
    
    # Continua a cercare finché non trova testo significativo o un nuovo tag blocco
    while next_node:
        if isinstance(next_node, NavigableString):
            text = str(next_node).strip()
            if text and len(text) > 1: # Ignora punteggiatura singola isolata
                description += text + " "
                # Se abbiamo trovato un testo lungo, probabilmente è la descrizione, ci fermiamo
                if len(description) > 5: 
                    break
        elif getattr(next_node, 'name', '') in ['br', 'span', 'strong']:
            # Se è uno span o un a capo, prendiamo il testo dentro
            text = next_node.get_text(" ", strip=True)
            if text:
                description += text + " "
        else:
            # Se incontriamo un altro link o un div, ci fermiamo
            break
        
        next_node = next_node.next_sibling

    # Pulizia finale della descrizione (rimuove : o - iniziali)
    description = description.strip(" :-\n\t")
    if not description:
        return "Descrizione non disponibile nel testo adiacente."
    return description

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

    # 2. Salva l'istantanea HTML giornaliera
    snapshot_filename = f"albo_{today_str}.html"
    snapshot_path = os.path.join(HTML_DIR, snapshot_filename)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Salvata istantanea HTML in {snapshot_path}")

    # 3. Analizza il contenuto e trova i documenti
    soup = BeautifulSoup(html_content, 'html.parser')
    history = load_history()
    
    new_items = []
    
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href']
        text = link.get_text(" ", strip=True)
        
        # Filtro: cerca estensione .pdf o testo contenente "file" e "pdf"
        is_document = False
        if href.lower().endswith('.pdf'):
            is_document = True
        elif "file" in text.lower() and "pdf" in text.lower():
            is_document = True
            
        # Standardizzazione URL
        if href.startswith('/'):
            full_url = BASE_DOMAIN + href
        elif href.startswith('http'):
            full_url = href
        else:
            continue

        if is_document:
            # Controllo se già scaricato
            if full_url not in history:
                print(f"Trovato nuovo documento: {text}")
                
                # Recupera la descrizione (contenuto) dopo il link
                content_desc = get_description_after_link(link)
                
                # Generazione nome file pulito
                filename = clean_filename_from_title(text)
                local_path = os.path.join(PDF_DIR, filename)
                
                # Gestione duplicati nome file
                counter = 1
                while os.path.exists(local_path):
                    name, ext = os.path.splitext(filename)
                    local_path = os.path.join(PDF_DIR, f"{name}_v{counter}{ext}")
                    counter += 1
                    
                # Download
                if download_file(full_url, local_path):
                    saved_filename = os.path.basename(local_path)
                    
                    history[full_url] = {
                        "first_seen": today_str,
                        "local_path": saved_filename,
                        "link_text": text,
                        "content_preview": content_desc[:100] # Salviamo un'anteprima nella history
                    }
                    
                    new_items.append({
                        "text": text,
                        "url": full_url,
                        "file": saved_filename,
                        "content": content_desc
                    })
                    
                    time.sleep(1) 

    # 4. Salva la cronologia aggiornata
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
                f.write(f"Titolo Originale: {item['text']}\n")
                f.write(f"URL: {item['url']}\n")
                f.write(f"Salvato come: {item['file']}\n")
                f.write(f"Contenuto: {item['content']}\n")
                f.write("-" * 20 + "\n")
        else:
            f.write("Nessun nuovo documento trovato oggi.\n")
            
    print(f"Job completato. Memo salvato in {memo_path}")

if __name__ == "__main__":
    main()
