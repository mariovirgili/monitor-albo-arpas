# Archiviatore Albo Pretorio ARPAS (Sardegna Ambiente)

Questo progetto contiene uno script Python automatizzato, che si aggiorna di mattina, progettato per monitorare, scaricare e archiviare quotidianamente le determinazioni e i documenti pubblicati sull'Albo Pretorio di Sardegna Ambiente (ARPAS).

Lo script è pensato per garantire la **persistenza dei dati**: salva i file localmente con nomi leggibili e mantiene uno storico per evitare duplicati, anche se i documenti vengono rimossi dal sito originale.

## 🚀 Funzionalità Principali

* **Download Intelligente:** Scarica solo i nuovi PDF non presenti nell'archivio.
* **Rinominazione Automatica:** Converte nomi file generici (es. `21_490_2026.pdf`) in nomi parlanti basati sul titolo e sulla data (es. `2026-01-28_Determinazione_n_88.pdf`).
* **Estrazione Contenuto:** Analizza la pagina web per catturare non solo il titolo, ma anche il **testo descrittivo** (oggetto della determina) adiacente al link.
* **Snapshot HTML:** Salva una copia grezza della pagina web ogni giorno per certificare lo stato dell'albo in quella data.
* **Report Giornalieri (Memo):** Genera un file di testo riassuntivo con l'elenco dei nuovi documenti trovati, i link originali e il contenuto estratto.
* **Resilienza:** Se la data non è presente nel titolo del documento, applica automaticamente la data di download come fallback.

## 📂 Struttura delle Cartelle

Una volta eseguito, lo script crea e gestisce automaticamente la seguente struttura di directory:

```text
/
├── archiver.py             # Lo script principale (Il motore del sistema)
├── README.md               # Questo file di documentazione
└── archive_data/           # Cartella principale dei dati scaricati
    ├── pdfs/               # Contiene tutti i documenti PDF rinominati
    │   └── 2026-01-28_Determinazione_n_88.pdf
    │
    ├── memos/              # Report testuali giornalieri
    │   └── Memo_2026-01-28.txt
    │
    ├── html_snapshots/     # Copia integrale della pagina web del giorno
    │   └── albo_2026-01-28.html
    │
    └── history.json        # Database (non toccare): tiene traccia dei file già scaricati
```




📄 Descrizione dei File Generati
* 1. **i Documenti (archive_data/pdfs/)**

I file vengono salvati con la seguente convenzione di nomenclatura per facilitare l'ordinamento cronologico: AAAA-MM-GG_Titolo_Del_Documento_Normalizzato.pdf

Vengono rimossi caratteri speciali e diciture come [file.pdf].

Gli spazi sono sostituiti da underscore _.


* 2. **i Memo (archive_data/memos/)**

Ogni giorno in cui vengono trovati nuovi file, viene creato un file .txt strutturato così:

```---------------------

MEMO GIORNALIERO - 2026-01-28

Totale Nuovi Documenti: 1

Titolo Originale: Determinazione n. 88 del 28/01/2026 [file.pdf]
URL: https://.../documento_originale.pdf
Salvato come: 2026-01-28_Determinazione_n_88.pdf
Contenuto: IMPEGNO DI SPESA SPESE DI MISSIONE..
---------------------------
```



* 3. **Database Storico (archive_data/history.json)**

Un file JSON tecnico che mappa l'URL originale del file con il nome locale. Serve allo script per "ricordare" cosa ha già scaricato e non riscaricare gli stessi file il giorno successivo.

🛠️ Installazione e Utilizzo

* Prerequisiti

Python 3.x installato.

Librerie richieste: requests, beautifulsoup4.

* Installazione Dipendenze

Esegui questo comando nel terminale:

```Bash
pip install requests beautifulsoup4
```
Esecuzione Manuale

Per lanciare l'archiviazione immediatamente:

```Bash
python archiver.py
```

* Automazione (Opzionale)
Lo script è ottimizzato per essere eseguito una volta al giorno tramite:

Windows: Utilità di Pianificazione (Task Scheduler).

Linux/Mac: Crontab.

Cloud: GitHub Actions (tramite workflow .yml).


⚠️ Note Tecniche
Lo script include un ritardo di 1 secondo (time.sleep(1)) tra un download e l'altro per non sovraccaricare il server della PA.

La pulizia del nome file utilizza Regex avanzate per eliminare variazioni di etichette come [file. pdf] o [ file pdf ].

Questa repository si aggiorna una volta al giorno in automatico
