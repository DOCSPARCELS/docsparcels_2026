# docsparcels_2026

Sistema di tracking e gestione spedizioni multi-corriere, con API e dashboard web. Supporta DHL, UPS, FedEx, TNT, SDA, GLS, BRT, SpediamoPro e altri corrieri.

## Struttura del progetto

```
docsparcels_2026/
|-- .env                          # Configurazione ambiente e credenziali locali
|-- .gitignore
|-- AVVIO SSH - SERVER.txt        # Istruzioni per tunnel e avvio servizi sul server
|-- OVH.txt                       # Note di accesso alla infrastruttura OVH
|-- api_server.py                 # Server Flask principale e viste web
|-- background_tracking.py        # Scheduler per aggiornamenti di tracking periodici
|-- brt_tracking.py
|-- config.py                     # Parametri e mapping per i corrieri
|-- db_connector.py               # Utility connessione MySQL tramite variabili di ambiente
|-- dhl_quote.py
|-- dhl_tracking.py
|-- fedex_tracking.py
|-- requirements.txt              # Dipendenze Python
|-- sda_tracking.py
|-- spediamopro_quote.py
|-- start_tunnel_and_server.sh    # Script helper per tunnel SSH e avvio server
|-- tnt_tracking.py
|-- tracking_service.py
|-- ups_quote.py
|-- ups_quote_n.py
|-- ups_tracking.py
|-- documentation/
|   `-- documentation.html        # Manuale interno dell'applicazione
|-- interface/                    # Interfacce dedicate ai singoli corrieri
|   |-- brt_tracking_interface.py
|   |-- dhl_quote_interface.py
|   |-- dhl_tracking_interface.py
|   |-- fedex_tracking_interface.py
|   |-- sda_tracking_interface.py
|   |-- spediamopro_quote_interface.py
|   |-- tnt_tracking_interface.py
|   |-- ups_quote_interface.py
|   |-- ups_quote_interface_n.py
|   `-- ups_tracking_interface.py
|-- manuale_API_DHL/
|   `-- manuale_API_DHL.pdf
|-- manuale_API_Poste Italiane SDA/
|   `-- manuale_API_Poste_Italiane.pdf
|-- manuale_API_TNT/
|   |-- Check_Price+tempi+serviziIN.xml
|   |-- Check_Price+tempi+serviziOUT.xml
|   |-- Manuale-ExpressConnect-FedEx compliant .pdf
|   |-- codifica_servizi.pdf
|   `-- Tracking_IN_example.xml
|-- static/                       # Asset frontend (CSS, JS, immagini, vendor, video)
|   |-- components/
|   |-- dist/
|   |-- img/
|   |-- vendors/
|   `-- videos/
|-- templates/                    # Template HTML usati dal server Flask
|   |-- base.html
|   |-- form-spedizione.html
|   `-- home.html
|-- theme_original/               # Tema originale completo con layout demo
|   |-- fixed-width-light/
|   |-- full-width-dark/
|   |-- full-width-light/
|   `-- rtl-light/
`-- __pycache__/                  # Cache bytecode Python generata a runtime
```

## Funzionalita principali
- Server Flask con API REST e dashboard web
- Supporto multi-corriere: DHL, UPS, FedEx, TNT, SDA, GLS, BRT, SpediamoPro
- Database MySQL per la gestione delle spedizioni
- Interfacce Python dedicate per ogni corriere
- Template HTML per dashboard e pagine web
- File statici (img, JS, CSS, vendor, video)
- Configurazione tramite `.env`

## Requisiti
- Python 3.12+
- MySQL server (porta di default 3306, configurabile tramite `.env`)
- Dipendenze Python in `requirements.txt` (Flask, flask-cors, mysql-connector-python, python-dotenv, requests, ecc.)

## Installazione
1. Clona il repository:
   ```
   git clone <repo-url>
   cd docsparcels_2026
   ```
2. Crea e attiva l'ambiente virtuale:
   ```
   python -m venv .venv
   .\.venv\Scripts\activate            # Windows
   source .venv/bin/activate           # macOS/Linux
   ```
3. Installa le dipendenze:
   ```
   pip install -r requirements.txt
   ```
4. Configura il file `.env` con le credenziali MySQL e le API dei corrieri.
5. Avvia il server Flask:
   ```
   python api_server.py
   ```

## Configurazione
- Tutte le variabili (DB, API, credenziali) sono lette da `.env`.
- Modifica `config.py` per personalizzare le API dei corrieri.
- I template HTML principali sono in `templates/`, mentre asset e risorse frontend sono in `static/`.

## Avvio e utilizzo
- Accedi alla dashboard su `http://<IP_SERVER>:5003/home`.
- Le API sono documentate nelle cartelle `manuale_API_*`.

## Note
- In produzione, utilizzare un web server (es. Nginx) come proxy per Flask.
- Proteggere il file `.env` e le credenziali sensibili.
- Consulta la documentazione nelle cartelle `manuale_API_*` per i dettagli specifici di ciascun corriere.
