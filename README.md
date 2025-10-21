# docsparcels_2026

Sistema di tracking e gestione spedizioni multi-corriere, con API e dashboard web. Supporta DHL, UPS, FedEx, TNT, SDA, GLS, BRT, SpediamoPro e altri corrieri.

## Struttura del progetto

```
docsparcels_2026/
├── .env                  # Configurazione ambiente e credenziali
├── .gitignore
├── .venv/                # Virtualenv Python
├── .vscode/              # Configurazioni VS Code
├── api_server.py         # Server Flask principale
├── background_tracking.py
├── brt_tracking.py
├── config.py             # Configurazione API corrieri
├── db_connector.py       # Utility connessione MySQL
├── dhl_quote.py
├── dhl_tracking.py
├── fedex_tracking.py
├── interface/
│   ├── brt_tracking_interface.py
│   ├── dhl_quote_interface.py
│   ├── dhl_tracking_interface.py
│   ├── fedex_tracking_interface.py
│   ├── sda_tracking_interface.py
│   ├── spediamopro_quote_interface.py
│   ├── tnt_tracking_interface.py
│   ├── ups_quote_interface.py
│   ├── ups_quote_interface_n.py
│   └── ups_tracking_interface.py
├── manuale_API_BRT/
├── manuale_API_DHL/
├── manuale_API_FedEx/
├── manuale_API_Poste Italiane SDA/
├── manuale_API_TNT/
├── OVH.txt               # Credenziali OVH e SSH
├── requirements.txt      # Dipendenze Python
├── sda_tracking.py
├── spediamopro_quote.py
├── start_tunnel_and_server.sh
├── static/
│   ├── dist/
│   ├── img/
│   ├── vendors/
│   └── videos/
├── templates/
│   ├── fixed-width-light/
│   ├── full-width-dark/
│   │   ├── home.html
│   │   ├── index.html
│   │   └── ... (altri file html)
│   ├── full-width-light/
│   └── rtl-light/
├── tnt_tracking.py
├── tracking_service.py
├── ups_quote.py
├── ups_quote_n.py
├── ups_tracking.py
└── __pycache__/
```

## Funzionalità principali
- Server Flask con API REST e dashboard web
- Supporto multi-corriere: DHL, UPS, FedEx, TNT, SDA, GLS, BRT, SpediamoPro
- Database MySQL per gestione spedizioni
- Interfacce Python dedicate per ogni corriere
- Template HTML per dashboard e pagine web
- File statici (img, js, css, vendor, video)
- Configurazione tramite `.env`

## Requisiti
- Python 3.12+
- MySQL server (porta di default 3306)
- Dipendenze Python in `requirements.txt` (Flask, flask-cors, mysql-connector-python, python-dotenv, requests, ecc.)

## Installazione
1. Clona il repository:
   ```
   git clone <repo-url>
   cd docsparcels_2026
   ```
2. Crea e attiva il virtualenv:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Installa le dipendenze:
   ```
   pip install -r requirements.txt
   ```
4. Configura il file `.env` con le credenziali MySQL e API corrieri.
5. Avvia il server Flask:
   ```
   python3 api_server.py
   ```

## Configurazione
- Tutte le variabili (DB, API, credenziali) sono in `.env`.
- Modifica `config.py` per personalizzare le API dei corrieri.
- I template HTML sono in `templates/full-width-dark/` e simili.

## Avvio e utilizzo
- Accedi alla dashboard su:
  `http://<IP_SERVER>:5003/home`
- Le API sono documentate nei file `manuale_API_*`.

## Note
- Per la produzione, usa un web server (es. Nginx) come proxy per Flask.
- Proteggi il file `.env` e le credenziali.
- Consulta la documentazione nelle cartelle `manuale_API_*` per ogni corriere.
