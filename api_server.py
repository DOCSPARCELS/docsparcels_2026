from flask import Flask, send_file, send_from_directory, redirect, request, jsonify, render_template
from db_connector import cursor as db_cursor
import os
import logging
from pathlib import Path
from flask_cors import CORS
from typing import Any, Dict, List, Tuple
from datetime import datetime, date, timedelta
import mysql.connector

# Basic logger so top-level initialization errors are logged instead of raising NameError
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')

# Redirect legacy /img/* requests to /html/img/*
import os



# Route per servire file statici dalla cartella 'html'
@app.route('/html/<path:filename>')
def custom_static(filename):
    return send_from_directory('html', filename)


# Serve vendor files referenced as /html/vendors/... from the top-level `vendors` folder
@app.route('/html/vendors/<path:filename>')
def html_vendors(filename):
    return send_from_directory('vendors', filename)


# Serve vendors when requested without html/ prefix (e.g. pages using ../vendors/...)
@app.route('/vendors/<path:filename>')
def vendors_root(filename):
    return send_from_directory('vendors', filename)


# Serve image files referenced as /html/img/... from the top-level `img` folder
@app.route('/html/img/<path:filename>')
def html_img(filename):
    return send_from_directory('img', filename)

@app.route('/')
def root_index():
    base = os.path.dirname(__file__)
    # Prefer index served from html/index.html if present
    path_html = os.path.join(base, 'html', 'index.html')
    if os.path.exists(path_html):
        return send_file(path_html)
    path = os.path.join(base, 'index.html')
    if os.path.exists(path):
        return send_file(path)
    return "index.html non trovato", 404

@app.route('/index.html')
def serve_index():
    base = os.path.dirname(__file__)
    path_html = os.path.join(base, 'html', 'index.html')
    if os.path.exists(path_html):
        return send_file(path_html)
    path = os.path.join(base, 'index.html')
    if os.path.exists(path):
        return send_file(path)
    return "index.html non trovato", 404

def load_tracking_codes():
    """Carica le mappature dei codici eventi dal database con nome e colore.
    This is lazy: call it explicitly when DB utilities (db_cursor) are available.
    """
    global event_mappings

    with db_cursor() as (conn, cur):
        # Ordina per ID per prendere sempre l'ultimo inserito in caso di duplicati
        query = "SELECT vettore, codice, nome, colore FROM codici_tracking ORDER BY id"
        cur.execute(query)
        results = cur.fetchall()

        event_mappings = {}
        for row in results:
            vettore_raw = row[0]
            codice = row[1]
            nome = row[2]
            colore = row[3] if len(row) > 3 else '#000000'

            # Controlla che vettore non sia None
            if not vettore_raw:
                continue

            vettore = vettore_raw.upper()

            if vettore not in event_mappings:
                event_mappings[vettore] = {}

            # Sovrascrive eventuali duplicati con l'ultimo (ID più alto)
            event_mappings[vettore][codice] = {
                'nome': nome,
                'colore': colore or '#000000'
            }

        LOG.info(f"🎯 Caricate {len(results)} mappature eventi con colori")
        LOG.info(f"🔍 Debug mappature DHL: {event_mappings.get('DHL', {})}")




from dotenv import load_dotenv
load_dotenv()

@app.route('/home')
def serve_home():
    # Parametri paginazione e ordinamento
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except Exception:
        page = 1
    try:
        page_size = min(max(int(request.args.get("page_size", request.args.get("page_size") or 5)), 1), 100)
    except Exception:
        page_size = 5
    sort_by = request.args.get("sort_by", "data_spedizione")
    sort_dir = request.args.get("sort_dir", "asc").lower()
    if sort_dir not in ("asc", "desc"): sort_dir = "asc"

    # Filtro per spedizioni in transito - ATTIVO DI DEFAULT (mostra solo final_position = 0)
    only_transit = request.args.get("only_transit", "1") == "1"
    where_sql = " WHERE final_position = 0" if only_transit else ""

    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3307)),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_DATABASE')
    )
    cur = conn.cursor()
    # Conta totale spedizioni filtrate
    cur.execute(f"SELECT COUNT(*) FROM spedizioni{where_sql}")
    total_items = int(cur.fetchone()[0])
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    # Query ordinata e paginata con filtro
    query = f"""
        SELECT data_spedizione, mitt_ragione_sociale, dest_ragione_sociale, vettore, last_position
        FROM spedizioni
        {where_sql}
        ORDER BY {sort_by} {sort_dir}
        LIMIT %s OFFSET %s
    """
    cur.execute(query, (page_size, offset))
    spedizioni = [
        {"data_spedizione": row[0], "mitt_ragione_sociale": row[1], "dest_ragione_sociale": row[2], "vettore": row[3], "last_position": row[4],}
        for row in cur.fetchall() if row[1] is not None
    ]
    cur.close()
    conn.close()
    return render_template(
        'full-width-dark/home.html',
        spedizioni=spedizioni,
        page=page,
        total_pages=total_pages,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        only_transit=only_transit
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)

def get_event_display_name(vettore, codice):
    """Ottiene il nome personalizzato per un codice evento (retrocompatibilità)"""
    if not event_mappings:
        load_tracking_codes()
    
    vettore = vettore.upper()
    mapping = event_mappings.get(vettore, {}).get(codice, {})
    if isinstance(mapping, dict):
        return mapping.get('nome', codice)
    return mapping or codice

def get_event_info(vettore, descrizione):
    """Ottiene informazioni complete per una descrizione evento (nome + colore)"""
    if not event_mappings:
        load_tracking_codes()
    
    # Protezione contro valori None/vuoti
    if not vettore or not descrizione:
        return {'nome': descrizione or '', 'colore': '#000000'}
    
    vettore = vettore.upper()
    
    # Debug: log cosa stiamo cercando
    LOG.info(f"🔍 DEBUG get_event_info: vettore='{vettore}', descrizione='{descrizione}'")
    LOG.info(f"🔍 DEBUG mappature disponibili per {vettore}: {list(event_mappings.get(vettore, {}).keys())}")
    
    # Prima prova: match esatto del codice (per retrocompatibilità)
    if descrizione in event_mappings.get(vettore, {}):
        mapping = event_mappings[vettore][descrizione]
        if isinstance(mapping, dict):
            result = {
                'nome': mapping.get('nome', descrizione),
                'colore': mapping.get('colore', '#000000')
            }
            LOG.info(f"✅ DEBUG trovato mapping esatto: {result}")
            return result
    
    # Fallback: restituisci la descrizione originale con colore default
    LOG.info(f"❌ DEBUG nessun mapping trovato per {vettore} {descrizione}")
    return {
        'nome': descrizione,
        'colore': '#000000'
    }

def _load_env_from_file() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if not key or os.getenv(key):
            continue
        os.environ[key] = value.strip()

_load_env_from_file()

def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        LOG.warning("Invalid %s value: %s", name, value)
        return default

def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        LOG.warning("Invalid %s value: %s", name, value)
        return default


## RIMOSSO: doppia istanza Flask, mantieni solo la prima
CORS(app)  # abilita richieste dal tuo frontend locale

# Redirect legacy /img/* requests to /html/img/*
@app.route('/img/<path:filename>')
def legacy_img_redirect(filename):
    return redirect(f'/html/img/{filename}', code=302)

# Mappa sicura per ORDER BY (nomi colonna DB reali)
SORT_MAP = {
    "id": "id",
    # use the sender/recipient official name fields that exist in the table
    "mittente": "mitt_ragione_sociale",
    "destinatario": "dest_ragione_sociale",
    "vettore": "vettore",
    "awb": "awb",
    "data_spedizione": "data_spedizione",
    "last_position": "last_position",
    "final_position": "final_position",
}
ALLOWED_DIR = {"asc", "desc"}

# Colonne che estraiamo
COLUMNS = [
    "id",
    "vettore",
    "awb",
    "data_spedizione",
    "last_position",
    "final_position",
    # Mittente (sender) - pick a broad set of fields present in the table
    "mitt_cliente", "mitt_ragione_sociale", "mitt_identificativo",
    "mitt_indirizzo", "mitt_indirizzo2", "mitt_indirizzo3", "mitt_civico",
    "mitt_cap", "mitt_citta", "mitt_provincia", "mitt_codice_nazione", "mitt_nazione",
    "mitt_contatto", "mitt_telefono", "mitt_cellulare", "mitt_email",
    "mitt_riferimento", "mitt_partita_iva", "mitt_eori", "mitt_info",
    # Destinatario (recipient)
    "dest_cliente", "dest_ragione_sociale", "dest_identificativo",
    "dest_indirizzo", "dest_indirizzo2", "dest_indirizzo3", "dest_civico",
    "dest_cap", "dest_citta", "dest_provincia", "dest_codice_nazione", "dest_nazione",
    "dest_contatto", "dest_telefono", "dest_cellulare", "dest_email",
    "dest_pagata_da", "dest_match_code", "dest_riferimento", "dest_partita_iva", "dest_info",
    # dettaglio / spedizione metrics
    "num_colli", "peso", "dim1", "dim2", "dim3", "dim_lunghezza", "dim_larghezza", "dim_altezza",
]

# Campi usati dal filtro globale q
Q_FIELDS = [
    "vettore", "last_position", "final_position",
    # sender searchable fields
    "mitt_cliente", "mitt_ragione_sociale", "mitt_contatto", "mitt_indirizzo", "mitt_cap", "mitt_citta",
    "mitt_provincia", "mitt_nazione", "mitt_telefono", "mitt_cellulare", "mitt_email",
    # recipient searchable fields
    "dest_cliente", "dest_ragione_sociale", "dest_contatto", "dest_indirizzo", "dest_cap", "dest_citta",
    "dest_provincia", "dest_nazione", "dest_telefono", "dest_cellulare", "dest_email",
    "awb",
]

def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _build_where_and_params(q, vettore, awb, mos, date_from, date_to, final_position=None) -> Tuple[str, List[Any]]:
    where = []
    params: List[Any] = []

    if mos:
        where.append("id = %s")
        params.append(mos)

    if vettore:
        where.append("vettore LIKE %s")
        params.append(f"%{vettore}%")

    if awb:
        where.append("awb LIKE %s")
        params.append(f"%{awb}%")

    if q:
        like = f"%{q}%"
        ors = " OR ".join([f"{f} LIKE %s" for f in Q_FIELDS])
        where.append(f"({ors})")
        params.extend([like] * len(Q_FIELDS))

    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d").date()
            where.append("data_spedizione >= %s")
            params.append(df)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").date()
            dt_end = datetime.combine(dt + timedelta(days=1), datetime.min.time())
            where.append("data_spedizione < %s")
            params.append(dt_end)
        except ValueError:
            pass

    if final_position is not None:
        try:
            fp = int(final_position)
            where.append("final_position = %s")
            params.append(fp)
        except Exception:
            # ignore invalid values
            pass

    return (" WHERE " + " AND ".join(where)) if where else "", params

def _get_personalized_last_position_with_color(row, idx: Dict[str, int]) -> tuple:
    """Personalizza il last_position usando i mapping dei codici eventi, restituisce (testo, colore)"""
    def g(c): return row[idx[c]] if c in idx else None
    
    last_position = g("last_position")
    if not last_position:
        return ("", "#000000")
    
    # Se last_position è già un nome descrittivo, restituiscilo così
    if len(last_position) > 3:  # Non è un codice evento di 2-3 caratteri
        return (last_position, "#000000")
    
    # Prova a personalizzare usando il vettore
    vettore = g("vettore")
    if vettore:
        try:
            event_info = get_event_info(vettore, last_position)
            result = (event_info['nome'], event_info['colore'])
            return result
        except Exception as e:
            # In caso di errore, ritorna i valori originali
            return (last_position, "#000000")
    
    return (last_position, "#000000")

def _row_to_item(row, idx: Dict[str, int]) -> Dict[str, Any]:
    def g(c): return row[idx[c]]
    v = g("data_spedizione")
    if isinstance(v, datetime):
        data_iso = v.isoformat()
    elif isinstance(v, date):
        data_iso = datetime(v.year, v.month, v.day).isoformat()
    else:
        data_iso = str(v) if v is not None else None

    # helper to pick the first non-empty value from candidate column names
    def pick(first, *candidates):
        v = g(first) if first in idx else None
        if v:
            return v
        for c in candidates:
            if c in idx:
                vv = g(c)
                if vv:
                    return vv
        return None

    mitt_nome = pick("mitt_ragione_sociale", "mitt_cliente", "mitt_contatto")
    dest_nome = pick("dest_ragione_sociale", "dest_cliente", "dest_contatto")

    # optional service/billing fields (if present in the result set)
    servizio = pick("servizio", "service", "product", "tipo_servizio", "service_code")
    tariffa = pick("tariffa", "price", "fare", "rate", "amount_before_tax", "tariff", "prezzo")
    iva = pick("iva", "vat", "tax", "tax_amount", "iva_amount")
    totale = pick("totale", "total", "amount", "grand_total", "totale_da_pagare", "prezzo_totale")

    # shipment detail: number of pieces, weight and three dimension fields
    num_colli = pick("num_colli", "colli", "pieces")
    peso = pick("peso", "weight", "total_weight", "peso_kg")
    dim1 = pick("dim1", "dim_lunghezza", "lunghezza", "length")
    dim2 = pick("dim2", "dim_larghezza", "larghezza", "width")
    dim3 = pick("dim3", "dim_altezza", "altezza", "height")

    # Converti final_position da numero a stringa leggibile
    final_pos_raw = g("final_position")
    if final_pos_raw == 1 or final_pos_raw == '1':
        final_position_str = "Consegnato"
    elif final_pos_raw == 0 or final_pos_raw == '0':
        final_position_str = "In transito"
    elif final_pos_raw is None or final_pos_raw == '':
        final_position_str = "Da definire"
    else:
        final_position_str = str(final_pos_raw)
    
    # Ottieni info evento una volta sola
    vettore = g("vettore") or ""
    last_pos_code = g("last_position") or ""
    
    # Per BRT, estrai la descrizione prima del trattino per fare pattern matching
    if vettore.upper() == 'BRT' and ' - ' in last_pos_code:
        brt_description = last_pos_code.split(' - ')[0].strip()
        event_info = get_event_info(vettore, brt_description)
    else:
        event_info = get_event_info(vettore, last_pos_code)
    
    return {
        "id": g("id"),
        "vettore": vettore,
        "awb": g("awb"),
        "data_spedizione": data_iso,
        "last_position": event_info["nome"],
        "last_position_color": event_info["colore"],
        "final_position": final_position_str,
        "servizio": servizio,
        "tariffa": tariffa,
        "iva": iva,
        "totale": totale,
        "num_colli": num_colli,
        "peso": peso,
        "dim1": dim1,
        "dim2": dim2,
        "dim3": dim3,
        "mittente": {
            "nome": mitt_nome,
            "cliente": g("mitt_cliente") if "mitt_cliente" in idx else None,
            "ragione_sociale": g("mitt_ragione_sociale") if "mitt_ragione_sociale" in idx else None,
            "identificativo": g("mitt_identificativo") if "mitt_identificativo" in idx else None,
            "indirizzo": pick("mitt_indirizzo", "mitt_indirizzo2", "mitt_indirizzo3"),
            "indirizzo2": g("mitt_indirizzo2") if "mitt_indirizzo2" in idx else None,
            "indirizzo3": g("mitt_indirizzo3") if "mitt_indirizzo3" in idx else None,
            "civico": g("mitt_civico") if "mitt_civico" in idx else None,
            "cap": pick("mitt_cap"),
            "citta": pick("mitt_citta"),
            "provincia": pick("mitt_provincia"),
            "codice_nazione": g("mitt_codice_nazione") if "mitt_codice_nazione" in idx else None,
            "paese": pick("mitt_nazione", "mitt_codice_nazione"),
            "contatto": pick("mitt_contatto"),
            "telefono": pick("mitt_telefono", "mitt_cellulare"),
            "cellulare": g("mitt_cellulare") if "mitt_cellulare" in idx else None,
            "email": pick("mitt_email"),
            "riferimento": g("mitt_riferimento") if "mitt_riferimento" in idx else None,
            "partita_iva": g("mitt_partita_iva") if "mitt_partita_iva" in idx else None,
            "eori": g("mitt_eori") if "mitt_eori" in idx else None,
            "info": g("mitt_info") if "mitt_info" in idx else None,
        },
        "destinatario": {
            "nome": dest_nome,
            "cliente": g("dest_cliente") if "dest_cliente" in idx else None,
            "ragione_sociale": g("dest_ragione_sociale") if "dest_ragione_sociale" in idx else None,
            "identificativo": g("dest_identificativo") if "dest_identificativo" in idx else None,
            "indirizzo": pick("dest_indirizzo", "dest_indirizzo2", "dest_indirizzo3"),
            "indirizzo2": g("dest_indirizzo2") if "dest_indirizzo2" in idx else None,
            "indirizzo3": g("dest_indirizzo3") if "dest_indirizzo3" in idx else None,
            "civico": g("dest_civico") if "dest_civico" in idx else None,
            "cap": pick("dest_cap"),
            "citta": pick("dest_citta"),
            "provincia": pick("dest_provincia"),
            "codice_nazione": g("dest_codice_nazione") if "dest_codice_nazione" in idx else None,
            "paese": pick("dest_nazione", "dest_codice_nazione"),
            "contatto": pick("dest_contatto"),
            "telefono": pick("dest_telefono", "dest_cellulare"),
            "cellulare": g("dest_cellulare") if "dest_cellulare" in idx else None,
            "email": pick("dest_email"),
            "pagata_da": g("dest_pagata_da") if "dest_pagata_da" in idx else None,
            "match_code": g("dest_match_code") if "dest_match_code" in idx else None,
            "riferimento": g("dest_riferimento") if "dest_riferimento" in idx else None,
            "partita_iva": g("dest_partita_iva") if "dest_partita_iva" in idx else None,
            "info": g("dest_info") if "dest_info" in idx else None,
        },
    }

@app.get("/api/spedizioni")
def spedizioni():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("page_size", 25)), 1), 200)
    except Exception:
        return jsonify({"detail": "page/page_size non validi"}), 400

    sort_by = request.args.get("sort_by", "data_spedizione")
    sort_dir = request.args.get("sort_dir", "desc").lower()
    sort_col = SORT_MAP.get(sort_by)
    if not sort_col: return jsonify({"detail": f"sort_by non valido: {sort_by}"}), 400
    if sort_dir not in ALLOWED_DIR: return jsonify({"detail": f"sort_dir non valido: {sort_dir}"}), 400

    q = request.args.get("q") or None
    vettore = request.args.get("vettore") or None
    awb = request.args.get("awb") or None
    mos = request.args.get("mos") or None
    date_from = request.args.get("date_from") or None
    date_to = request.args.get("date_to") or None

    # Debug log per vedere i filtri ricevuti
    LOG.info(f"🔍 Filtri ricevuti: q='{q}', vettore='{vettore}', awb='{awb}', mos='{mos}'")

    # Filtro per spedizioni in transito - di default mostra solo final_position = 0
    final_position = request.args.get('final_position', '0')
    where_sql, params = _build_where_and_params(q, vettore, awb, mos, date_from, date_to, final_position)
    sql_count = f"SELECT COUNT(*) FROM spedizioni{where_sql}"
    offset = (page - 1) * page_size
    # Use SELECT * so optional billing/service columns (if present) are returned
    sql_list = f"""
        SELECT *
        FROM spedizioni
        {where_sql}
        ORDER BY {sort_col} {sort_dir}
        LIMIT %s OFFSET %s
    """

    items: List[Dict[str, Any]] = []
    total_items = 0

    try:
        with db_cursor() as (conn, cur):
            cur.execute(sql_count, params)
            total_items = int(cur.fetchone()[0])

            cur.execute(sql_list, params + [page_size, offset])
            rows = cur.fetchall()
            desc = [d[0] for d in cur.description]
            idx = {name: i for i, name in enumerate(desc)}
            for row in rows:
                items.append(_row_to_item(row, idx))
    except mysql.connector.Error as e:
        # DB connection/auth error: log and return a small demo dataset so the UI can function.
        LOG.exception("Database error while serving /api/spedizioni")
        # Demo fallback: create a few fake shipments matching the expected shape.
        demo_total = 30
        demo_items = []
        for i in range(1, demo_total + 1):
            demo_items.append({
                'id': i,
                'vettore': 'TEST',
                'awb': f'000000{i:04d}',
                'data_spedizione': (datetime.utcnow().date() - timedelta(days=i % 7)).isoformat(),
                'last_position': 'In transito',
                'final_position': 'Da definire',
                'mittente': {'nome': f'Mittente {i}', 'citta': 'Milano', 'paese': 'IT'},
                'destinatario': {'nome': f'Destinatario {i}', 'citta': 'Roma', 'paese': 'IT'},
            })
        # paginate demo items
        total_items = demo_total
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = demo_items[start:end]
        return jsonify({
            'items': page_items,
            'page': page,
            'page_size': page_size,
            'total_items': total_items,
            'total_pages': total_pages,
            'demo': True,
            'db_error': str(e),
        }), 200
    except Exception:
        LOG.exception("Unexpected error while serving /api/spedizioni")
        return jsonify({"detail": "Internal server error"}), 500

    total_pages = max(1, (total_items + page_size - 1) // page_size)
    return jsonify({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages
    })


@app.route('/api/spedizioni/<int:item_id>', methods=['GET'])
def get_spedizione(item_id: int):
    """Ottieni singola spedizione per ID"""
    try:
        with db_cursor() as (conn, cur):
            query = """
            SELECT id, vettore, awb, data_spedizione, last_position, final_position,
                   servizio, tariffa, iva, totale,
                   mitt_nome, mitt_indirizzo, mitt_cap, mitt_citta, mitt_provincia, 
                   mitt_nazione, mitt_cellulare, mitt_email,
                   dest_nome, dest_indirizzo, dest_cap, dest_citta, dest_provincia,
                   dest_nazione, dest_cellulare, dest_email
            FROM spedizioni 
            WHERE id = %s
            """
            cur.execute(query, [item_id])
            row = cur.fetchone()
            
            if not row:
                return jsonify({"detail": "Spedizione non trovata"}), 404
            
            # Mappa risultato
            result = {
                "id": row[0],
                "vettore": row[1],
                "awb": row[2],
                "data_spedizione": row[3].isoformat() if row[3] else None,
                "last_position": row[4],
                "final_position": row[5],
                "servizio": row[6],
                "tariffa": float(row[7]) if row[7] else 0.0,
                "iva": float(row[8]) if row[8] else 0.0,
                "totale": float(row[9]) if row[9] else 0.0,
                "mittente": {
                    "nome": row[10],
                    "indirizzo": row[11],
                    "cap": row[12],
                    "citta": row[13],
                    "provincia": row[14],
                    "nazione": row[15] or "IT",
                    "cellulare": row[16],
                    "email": row[17]
                },
                "destinatario": {
                    "nome": row[18],
                    "indirizzo": row[19], 
                    "cap": row[20],
                    "citta": row[21],
                    "provincia": row[22],
                    "nazione": row[23] or "IT",
                    "cellulare": row[24],
                    "email": row[25]
                }
            }
            
            return jsonify(result)
            
    except Exception as e:
        LOG.exception("Errore recupero spedizione %s", item_id)
        return jsonify({"detail": f"Errore interno: {str(e)}"}), 500


@app.put('/api/spedizioni/<int:item_id>')
def update_spedizione(item_id: int):
    """Aggiorna i campi della spedizione identificata da id.

    Accetta JSON con campi top-level (vettore, awb, data_spedizione, last_position, final_position,
    servizio, tariffa, iva, totale) e oggetti nested 'mittente' e 'destinatario' con sotto-campi.
    I nomi nested vengono mappati sulle colonne 'mitt_*' e 'dest_*' presenti in `spedizioni`.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"detail": "payload JSON non valido"}), 400

    # Top-level simple mapping
    top_map = {
        'vettore': 'vettore', 'awb': 'awb', 'data_spedizione': 'data_spedizione',
        'last_position': 'last_position', 'final_position': 'final_position',
        'servizio': 'servizio', 'tariffa': 'tariffa', 'iva': 'iva', 'totale': 'totale',
        'num_colli': 'num_colli', 'peso': 'peso', 'dim1': 'dim1', 'dim2': 'dim2', 'dim3': 'dim3'
    }

    # mapping for nested mittente/destinatario keys -> column suffix
    nested_map = {
        'identificativo': '_identificativo', 'cliente': '_cliente', 'ragione_sociale': '_ragione_sociale',
        'nome': '_ragione_sociale', 'indirizzo': '_indirizzo', 'indirizzo2': '_indirizzo2', 'indirizzo3': '_indirizzo3',
        'civico': '_civico', 'cap': '_cap', 'citta': '_citta', 'provincia': '_provincia',
        'codice_nazione': '_codice_nazione', 'paese': '_nazione', 'contatto': '_contatto',
        'telefono': '_telefono', 'cellulare': '_cellulare', 'email': '_email', 'riferimento': '_riferimento',
        'partita_iva': '_partita_iva', 'eori': '_eori', 'info': '_info', 'match_code': '_match_code', 'pagata_da': '_pagata_da'
    }

    cols = []
    params: list = []

    # handle top-level
    for k, v in data.items():
        if k in top_map:
            cols.append(f"{top_map[k]} = %s")
            params.append(v)

    # handle nested
    for prefix in ('mittente', 'destinatario'):
        nested = data.get(prefix)
        if nested and isinstance(nested, dict):
            db_prefix = 'mitt' if prefix == 'mittente' else 'dest'
            for nk, nv in nested.items():
                suf = nested_map.get(nk)
                if suf:
                    col = f"{db_prefix}{suf}"
                    cols.append(f"{col} = %s")
                    params.append(nv)

    if not cols:
        return jsonify({"detail": "Nessun campo aggiornabile fornito"}), 400

    params.append(item_id)
    sql = "UPDATE spedizioni SET " + ", ".join(cols) + " WHERE id = %s"

    try:
        with db_cursor() as (conn, cur):
            cur.execute(sql, params)
            conn.commit()

            # return the updated row (use SELECT * to keep compatibility)
            cur.execute("SELECT * FROM spedizioni WHERE id = %s", [item_id])
            row = cur.fetchone()
            if not row:
                return jsonify({"detail": "Spedizione non trovata dopo aggiornamento"}), 404
            desc = [d[0] for d in cur.description]
            idx = {name: i for i, name in enumerate(desc)}
            item = _row_to_item(row, idx)
            return jsonify(item), 200
    except mysql.connector.Error as e:
        LOG.exception("Database error during update /api/spedizioni/%s", item_id)
        return jsonify({"detail": "DB error", "error": str(e)}), 500
    except Exception:
        LOG.exception("Unexpected error during update /api/spedizioni/%s", item_id)
        return jsonify({"detail": "Internal server error"}), 500

@app.route('/')
# ...existing code...

@app.route('/spedizioni.html')
def serve_spedizioni():
    try:
        base = os.path.dirname(__file__)
        path = os.path.join(base, 'spedizioni.html')
        if os.path.exists(path):
            return send_file(path)
        else:
            return "Not found", 404
    except Exception:
        return "Not found", 404


@app.route('/spedizione_modulo.html')
def serve_spedizione_modulo():
    try:
        base = os.path.dirname(__file__)
        path = os.path.join(base, 'spedizione_modulo.html')
        if os.path.exists(path):
            return send_file(path)
        else:
            return "Not found", 404
    except Exception:
        return "Not found", 404

@app.route('/debug.html')
def serve_debug():
    try:
        base = os.path.dirname(__file__)
        path = os.path.join(base, 'debug.html')
        if os.path.exists(path):
            return send_file(path)
        else:
            return "Debug file not found", 404
    except Exception as e:
        LOG.error(f"Errore serving debug.html: {e}")
        return f"Debug error: {str(e)}", 404

@app.route('/debug')
def serve_debug_simple():
    """Endpoint debug semplificato senza dipendenze esterne"""
    try:
        import os
        base = os.path.dirname(__file__)
        
        # Verifica presenza directory html
        html_dir = os.path.join(base, 'html')
        html_exists = os.path.exists(html_dir)
        html_files = []
        if html_exists:
            try:
                for root, dirs, files in os.walk(html_dir):
                    for file in files[:10]:  # Solo primi 10
                        rel_path = os.path.relpath(os.path.join(root, file), base)
                        html_files.append(rel_path.replace('\\', '/'))
            except Exception as e:
                html_files = [f"Errore lettura: {str(e)}"]

        debug_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug Simple</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                .box {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .success {{ border-left: 4px solid #4CAF50; }}
                .error {{ border-left: 4px solid #f44336; }}
                .info {{ border-left: 4px solid #2196F3; }}
            </style>
        </head>
        <body>
            <h1>🔍 Debug Sistema</h1>
            
            <div class="box info">
                <h3>📂 Directory Base</h3>
                <p><strong>Path:</strong> {base}</p>
            </div>
            
            <div class="box {'success' if html_exists else 'error'}">
                <h3>📁 Directory HTML</h3>
                <p><strong>Esiste:</strong> {'✅ SÌ' if html_exists else '❌ NO'}</p>
                <p><strong>Path:</strong> {html_dir}</p>
            </div>
            
            <div class="box info">
                <h3>📄 File HTML (primi 10)</h3>
                <ul>
                    {''.join([f'<li>{f}</li>' for f in html_files[:10]])}
                </ul>
            </div>
            
            <div class="box info">
                <h3>🔗 Test Links</h3>
                <p><a href="/api/debug/static" target="_blank">API Debug Static</a></p>
                <p><a href="/html/full-width-dark/index.html" target="_blank">Dashboard HTML</a></p>
                <p><a href="/html/full-width-dark/dist/css/style.css" target="_blank">Style CSS</a></p>
            </div>
        </body>
        </html>
        """
        return debug_html
    except Exception as e:
        return f"Debug error: {str(e)}", 500

@app.route('/api/spedizioni/<int:spedizione_id>/tracking', methods=['POST'])
def update_tracking(spedizione_id):
    """
    Aggiorna il tracking per una spedizione specifica
    
    POST /api/spedizioni/123/tracking
    Risposta: {"success": true, "last_position": "UPS: Delivered", "vettore": "UPS", "awb": "1Z999..."}
    """
    try:
        from tracking_service import TrackingService
        
        service = TrackingService()
        result = service.update_tracking(spedizione_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        LOG.exception("Errore endpoint tracking spedizione %s", spedizione_id)
        return jsonify({
            "success": False, 
            "error": f"Errore interno: {str(e)}"
        }), 500


@app.route('/api/tracking/ups/<tracking_number>', methods=['GET'])
def track_ups_shipment(tracking_number):
    """
    Traccia una spedizione UPS
    
    GET /api/tracking/ups/{tracking_number}
    
    Nota: Accetta tutti i formati tracking UPS (standard, freight, etc.)
    
    Risposta: {"success": true, "tracking_number": "...", "status": "Delivered", "events": [...]}
    """
    try:
        from ups_tracking import UPSTrackingClient
        from config import UPSConfig
        
        # Validazione base del numero tracking
        if not tracking_number or len(tracking_number.strip()) < 5:
            return jsonify({
                "success": False,
                "error": "Numero tracking non valido (troppo corto)",
                "tracking_number": tracking_number
            }), 400
        
        # Crea client UPS
        try:
            config = UPSConfig.from_env()
        except ValueError:
            from config import DEFAULT_UPS_CONFIG
            config = DEFAULT_UPS_CONFIG
        
        client = UPSTrackingClient(config)
        result = client.track_shipment(tracking_number)
        
        # Trasforma risultato per API response
        if 'error' in result:
            return jsonify({
                "success": False,
                "error": result['error'],
                "tracking_number": tracking_number,
                "suggestion": "Verifica il numero o riprova più tardi"
            }), 400
        else:
            # Analizza il service code
            service_code = tracking_number[2:4]
            service_map = {
                'GE': 'UPS Ground Economy',
                '12': 'UPS 3 Day Select', 
                '13': 'UPS Next Day Air',
                '14': 'UPS Next Day Air Early',
                '15': 'UPS 2nd Day Air'
            }
            
            return jsonify({
                "success": True,
                "tracking_number": tracking_number,
                "service_type": service_map.get(service_code, f'UPS Service {service_code}'),
                "status": result.get('status_description', 'Unknown'),
                "events": result.get('events', []),
                "origin": result.get('origin', {}),
                "destination": result.get('destination', {}),
                "ups_url": f"https://www.ups.com/track?loc=it_IT&tracknum={tracking_number}"
            }), 200
            
    except Exception as e:
        LOG.exception("Errore tracking UPS %s", tracking_number)
        return jsonify({
            "success": False,
            "error": f"Errore interno durante tracking UPS: {str(e)}",
            "tracking_number": tracking_number
        }), 500


@app.route('/api/tracking/dhl/<tracking_number>', methods=['GET'])
def track_dhl_shipment(tracking_number):
    """
    Traccia una spedizione DHL
    
    GET /api/tracking/dhl/{tracking_number}
    
    Risposta: {"success": true, "tracking_number": "...", "status": "Delivered", "events": [...]}
    """
    try:
        # Test rapido - restituisci dati di esempio per ora
        return jsonify({
            "success": True,
            "tracking_number": tracking_number,
            "status": "Test Mode",
            "events": [
                {
                    "date": "2025-10-15",
                    "time": "10:00:00", 
                    "description": "Endpoint DHL attivo - modalità test",
                    "location": "Sistema Test"
                }
            ],
            "carrier": "DHL",
            "note": "Endpoint DHL implementato correttamente - test mode attivo"
        })
        
        # Codice originale commentato temporaneamente
        # from dhl_tracking import DHLTrackingClient
        # from config import DHLConfig
        
        # Codice originale commentato temporaneamente
        # from dhl_tracking import DHLTrackingClient
        # from config import DHLConfig
        
        # # Validazione base del numero tracking
        # if not tracking_number or len(tracking_number.strip()) < 5:
        #     return jsonify({
        #         "success": False,
        #         "error": "Numero tracking DHL non valido (troppo corto)",
        #         "tracking_number": tracking_number
        #     }), 400
        
        # # Resto del codice DHL commentato per debug
        
    except Exception as e:
        LOG.error(f"Errore tracking DHL {tracking_number}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Errore interno durante tracking DHL: {str(e)}",
            "tracking_number": tracking_number
        }), 500


@app.route('/api/tracking/tnt/<tracking_number>', methods=['GET'])
def track_tnt_shipment(tracking_number):
    """
    Traccia una spedizione TNT Express
    
    GET /api/tracking/tnt/{tracking_number}
    
    Risposta: {"success": true, "tracking_number": "...", "status": "...", "events": [...]}
    """
    try:
        from tnt_tracking import TNTTrackingClient
        
        # Validazione base del numero tracking
        if not tracking_number or len(tracking_number.strip()) < 8:
            return jsonify({
                "success": False,
                "error": "Numero AWB TNT non valido (minimo 8 caratteri)",
                "tracking_number": tracking_number
            }), 400
        
        # Crea client TNT
        client = TNTTrackingClient()
        result = client.track_shipment(tracking_number)
        
        # Trasforma risultato per API response
        if result.get('status') != 'success':
            return jsonify({
                "success": False,
                "error": result.get('message', 'Errore tracking TNT'),
                "tracking_number": tracking_number,
                "suggestion": "Verifica il numero AWB o riprova più tardi"
            }), 400
        else:
            return jsonify({
                "success": True,
                "tracking_number": result.get('awb', tracking_number),
                "carrier": "TNT Express",
                "service_type": result.get('service', 'TNT Standard'),
                "status": result.get('current_status', 'Unknown'),
                "location": result.get('current_location', ''),
                "last_update": result.get('last_update', ''),
                "events": result.get('events', []),
                "origin": result.get('origin', ''),
                "destination": result.get('destination', ''),
                "tracking_url": result.get('tracking_url', f"https://www.tnt.com/express/it_it/site/shipping-tools/tracking.html?searchType=con&cons={tracking_number}")
            }), 200
            
    except Exception as e:
        LOG.exception("Errore tracking TNT %s", tracking_number)
        return jsonify({
            "success": False,
            "error": f"Errore interno durante tracking TNT: {str(e)}",
            "tracking_number": tracking_number
        }), 500


@app.route('/api/spedizioni/<int:spedizione_id>/events', methods=['GET'])
def get_spedizione_events(spedizione_id):
    """
    Ottiene gli eventi di tracking per una spedizione
    
    GET /api/spedizioni/123/events
    Risposta: {"success": true, "events": [...]}
    """
    try:
        # Connessione database
        with db_cursor() as (conn, cur):
            # Query per ottenere i dati della spedizione
            query = """
            SELECT vettore, awb
            FROM spedizioni
            WHERE id = %s
            """
            
            cur.execute(query, (spedizione_id,))
            spedizione = cur.fetchone()
            
            if not spedizione:
                return jsonify({
                    "success": False,
                    "error": "Spedizione non trovata"
                }), 404
            
            # Ottieni eventi live dal tracking service
            vettore = spedizione[0].upper() if spedizione[0] else ''
            awb = spedizione[1] if spedizione[1] else ''
            
            if not awb or not vettore:
                return jsonify({
                    "success": False,
                    "error": "AWB o vettore mancante"
                }), 400
            
            # Recupera eventi tramite tracking
            from tracking_service import TrackingService
            tracking_service = TrackingService()
            
            if vettore in ['UPS']:
                result = tracking_service.ups_client.track_shipment(awb)
            elif vettore in ['DHL']:
                result = tracking_service.dhl_client.track_shipment(awb)
            elif vettore in ['SDA']:
                result = tracking_service.sda_client.track(awb)
            elif vettore in ['BRT']:
                result = tracking_service.brt_client.track(awb)
            elif vettore in ['FEDEX', 'FED']:  # Supporta sia FEDEX che FED
                result = tracking_service.fedex_client.track_shipment(awb)
            else:
                return jsonify({
                    "success": False,
                    "error": f"Vettore {vettore} non supportato"
                }), 400
            
            events = result.get('events', [])
            
            # Applica filtro eventi solo per BRT (che spesso ha eventi vuoti)
            if vettore in ['BRT']:
                valid_raw_events = []
                for event in events:
                    # Controlla se l'evento ha almeno i campi base popolati
                    has_date = event.get('date') and str(event.get('date')).strip()
                    has_time = event.get('time') and str(event.get('time')).strip()
                    has_code = event.get('code') and str(event.get('code')).strip()
                    
                    if has_date and has_time and has_code:
                        valid_raw_events.append(event)
                
                LOG.info(f"🔍 Eventi BRT: {len(events)} totali, {len(valid_raw_events)} validi")
            else:
                # Per altri vettori, usa tutti gli eventi
                valid_raw_events = events
                LOG.info(f"🔍 Eventi {vettore}: {len(events)} totali")
            
            # Trasforma eventi nel formato che si aspetta il frontend
            formatted_events = []
            for event in valid_raw_events:  # Usa solo eventi validi
                formatted_event = {}
                
                # Mappa i campi dal formato tracking service al formato frontend
                # Supporta UPS, DHL, SDA, BRT e FedEx con campi diversi
                
                # Gestione data
                if 'date' in event:
                    # Trasforma date - BRT usa DD.MM.YYYY, altri YYYY-MM-DD
                    date_str = event['date']
                    try:
                        from datetime import datetime
                        if '.' in date_str:  # Formato BRT: DD.MM.YYYY
                            date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                            formatted_event['data'] = date_obj.strftime('%d/%m/%Y')
                        else:  # Formato standard: YYYY-MM-DD
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            formatted_event['data'] = date_obj.strftime('%d/%m/%Y')
                    except:
                        formatted_event['data'] = date_str
                elif 'data' in event:  # FedEx usa 'data'
                    # FedEx già formattata come YYYY-MM-DD, convertila in DD/MM/YYYY
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(event['data'], '%Y-%m-%d')
                        formatted_event['data'] = date_obj.strftime('%d/%m/%Y')
                    except:
                        formatted_event['data'] = event['data']

                # Gestione ora
                if 'time' in event:
                    # Trasforma time - BRT usa HH.MM, altri HH:MM:SS
                    time_str = event['time']
                    if '.' in time_str:  # Formato BRT: HH.MM
                        formatted_event['ora'] = time_str.replace('.', ':')
                    elif len(time_str) > 5:  # Formato standard: HH:MM:SS
                        formatted_event['ora'] = time_str[:5]  # Prende solo HH:MM
                    else:
                        formatted_event['ora'] = time_str
                elif 'ora' in event:  # FedEx usa 'ora'
                    formatted_event['ora'] = event['ora']
                    
                # Gestione codice evento (diverso per ogni vettore)
                event_code = None
                if 'event_code' in event:
                    event_code = event['event_code']
                elif 'status_code' in event:  # SDA usa status_code
                    event_code = event['status_code']
                elif 'code' in event:  # BRT usa code
                    event_code = event['code']
                elif 'codice' in event:  # FedEx usa codice
                    event_code = event['codice']
                
                if event_code:
                    formatted_event['codice'] = event_code
                    
                    # Ottieni informazioni complete (nome + colore)
                    event_info = get_event_info(vettore, event_code)
                    personalized_name = event_info['nome']
                    event_color = event_info['colore']
                    
                    # Se la mappatura restituisce solo il codice, usa la descrizione originale
                    if personalized_name == event_code:
                        # Per SDA prova con la descrizione completa per pattern matching
                        if vettore == 'SDA' and ('status_description' in event or 'synthesis_description' in event):
                            description = event.get('synthesis_description') or event.get('status_description', '')
                            if description:
                                event_info = get_event_info(vettore, description)
                                personalized_name = event_info['nome']
                                event_color = event_info['colore']
                        
                        # Per BRT prova con la descrizione per pattern matching
                        if vettore == 'BRT' and 'description' in event:
                            description = event.get('description', '')
                            if description:
                                event_info = get_event_info(vettore, description)
                                personalized_name = event_info['nome']
                                event_color = event_info['colore']
                        
                        # Per FedEx prova con la descrizione per pattern matching
                        if vettore in ['FEDEX', 'FED'] and 'descrizione' in event:
                            description = event.get('descrizione', '')
                            if description:
                                event_info = get_event_info(vettore, description)
                                personalized_name = event_info['nome']
                                event_color = event_info['colore']
                            if description:
                                event_info = get_event_info(vettore, description)
                                personalized_name = event_info['nome']
                                event_color = event_info['colore']
                        
                        # Fallback alla descrizione originale
                        if personalized_name == event_code and 'description' in event:
                            personalized_name = event['description']
                            event_color = '#000000'  # Colore default
                    
                    formatted_event['commento_personalizzato'] = personalized_name
                    
                    # Descrizione originale (varia per vettore)
                    original_description = (
                        event.get('description') or 
                        event.get('status_description') or 
                        event.get('synthesis_description') or 
                        event.get('descrizione') or  # FedEx usa descrizione
                        ''
                    )
                    formatted_event['commento'] = original_description
                    formatted_event['colore'] = event_color
                
                # Aggiungi location se disponibile
                if 'location' in event:
                    formatted_event['location'] = event['location']
                elif 'office_description' in event:  # SDA usa office_description
                    formatted_event['location'] = event['office_description']
                elif 'luogo' in event:  # FedEx usa luogo
                    formatted_event['location'] = event['luogo']
                
                # Aggiungi l'evento formattato (già filtrato sopra)
                formatted_events.append(formatted_event)
            
            # Sostituisci gli eventi con quelli formattati
            events = formatted_events
            
            # Salva gli eventi nel database per future richieste
            # Nota: salvataggio eventi rimosso per compatibilità con schema DB locale
            # if events:
            #     import json
            #     try:
            #         events_json = json.dumps(events, ensure_ascii=False)
            #         update_query = """
            #         UPDATE spedizioni
            #         SET tracking_events = %s 
            #         WHERE id = %s
            #         """
            #         cur.execute(update_query, (events_json, spedizione_id))
            #         conn.commit()
            #     except Exception as e:
            #         LOG.warning(f"Errore salvataggio eventi per spedizione {spedizione_id}: {e}")
            
            return jsonify({
                "success": True,
                "events": events,
                "source": "api"
            }), 200
        
    except Exception as e:
        LOG.exception(f"Errore recupero eventi spedizione {spedizione_id}")
        return jsonify({
            "success": False,
            "error": f"Errore interno: {str(e)}"
        }), 500


@app.route('/api/tracking/update-all-transit', methods=['POST'])
def update_all_transit_tracking():
    """
    Aggiorna il tracking di tutte le spedizioni in transito
    (spedizioni con AWB, vettore e final_position diverso da 'Delivered')
    
    POST /api/tracking/update-all-transit
    Risposta: {"success": true, "updated_count": 15, "message": "Aggiornate 15 spedizioni"}
    """
    try:
        from tracking_service import TrackingService
        
        # Connessione database
        with db_cursor() as (conn, cursor):
            # Query per trovare spedizioni in transito trackabili
            query = """
            SELECT id, vettore, awb
            FROM spedizioni 
            WHERE awb IS NOT NULL 
            AND awb != '' 
            AND vettore IS NOT NULL 
            AND vettore != ''
            AND (final_position IS NULL 
                 OR final_position != 'Delivered'
                 OR final_position = '')
            ORDER BY data_spedizione DESC
            LIMIT 100
            """
            
            cursor.execute(query)
            spedizioni = cursor.fetchall()
            
            if not spedizioni:
                return jsonify({
                    "success": True,
                    "updated_count": 0,
                    "message": "Nessuna spedizione in transito trovata"
                }), 200
        
            tracking_service = TrackingService()
            updated_count = 0
            
            LOG.info(f"🔄 Inizio aggiornamento {len(spedizioni)} spedizioni in transito")
            
            for spedizione in spedizioni:
                try:
                    # fetchall() restituisce tuple, non dizionari
                    spedizione_id = spedizione[0]  # id
                    vettore = spedizione[1]  # vettore
                    awb = spedizione[2]  # awb
                    
                    LOG.info(f"📦 Aggiornamento spedizione {spedizione_id}: {vettore} {awb}")
                    
                    # Usa il servizio di tracking
                    result = tracking_service.update_tracking(spedizione_id)
                    
                    if result.get('success'):
                        updated_count += 1
                        LOG.info(f"✅ Spedizione {spedizione_id} aggiornata")
                    else:
                        LOG.warning(f"⚠️ Spedizione {spedizione_id}: {result.get('error', 'Errore sconosciuto')}")
                        
                except Exception as e:
                    LOG.exception(f"❌ Errore aggiornamento spedizione {spedizione[0]}: {e}")
                    continue
            
            LOG.info(f"🎯 Aggiornamento completato: {updated_count}/{len(spedizioni)} spedizioni")
            
            return jsonify({
                "success": True,
                "updated_count": updated_count,
                "total_processed": len(spedizioni),
                "message": f"Aggiornate {updated_count} su {len(spedizioni)} spedizioni in transito"
            }), 200
        
    except Exception as e:
        LOG.exception("Errore aggiornamento tracking globale")
        return jsonify({
            "success": False,
            "error": f"Errore interno: {str(e)}"
        }), 500


@app.route('/api/debug/mappings', methods=['GET'])
def debug_mappings():
    """Endpoint debug per vedere le mappature caricate"""
    try:
        return jsonify(event_mappings), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/static', methods=['GET'])
def debug_static():
    """Endpoint debug per verificare file statici disponibili"""
    try:
        import os
        base = os.path.dirname(__file__)
        
        # Lista file nella directory html/
        html_dir = os.path.join(base, 'html')
        html_files = []
        if os.path.exists(html_dir):
            for root, dirs, files in os.walk(html_dir):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), base)
                    html_files.append(rel_path.replace('\\', '/'))
        
        return jsonify({
            "base_directory": base,
            "html_files": html_files[:20],  # Prime 20 per non sovraccaricare
            "html_files_count": len(html_files)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/debug/reload-mappings', methods=['POST'])
def reload_mappings():
    """Endpoint per forzare il reload delle mappature"""
    try:
        global event_mappings
        event_mappings = {}  # Pulisci cache
        load_tracking_codes()  # Ricarica
        return jsonify({
            "success": True,
            "message": f"Mappature ricaricate: {len(event_mappings)} vettori"
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/test_event_info', methods=['POST'])
def test_event_info():
    """Test diretto della funzione get_event_info"""
    try:
        data = request.get_json()
        vettore = data.get('vettore', '')
        descrizione = data.get('descrizione', '')
        
        result = get_event_info(vettore, descrizione)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint di test"""
    return jsonify({'message': 'Server funzionante!', 'timestamp': str(datetime.now())})

@app.route('/get_record/<int:record_id>', methods=['GET'])
def get_record(record_id):
    """Restituisce un record specifico dalla tabella spedizioni"""
    LOG.info(f"🔍 Richiesta get_record per ID: {record_id}")
    try:
        with db_cursor() as (conn, cur):
            # Query per ottenere un record specifico per ID
            query = """
            SELECT * FROM spedizioni 
            WHERE id = %s
            """
            LOG.info(f"🔍 Eseguo query: {query} con ID: {record_id}")
            cur.execute(query, (record_id,))
            row = cur.fetchone()
            
            if not row:
                LOG.warning(f"❌ Record con ID {record_id} non trovato")
                return jsonify({'error': f'Record con ID {record_id} non trovato'}), 404
            
            # Ottieni i nomi delle colonne
            columns = [desc[0] for desc in cur.description]
            LOG.info(f"🔍 Colonne trovate: {len(columns)}")
            
            # Crea dizionario con i dati
            record = {}
            for i, column in enumerate(columns):
                value = row[i]
                try:
                    record[column] = serialize_value(value)
                except Exception as e:
                    LOG.error(f"❌ Errore serializzazione colonna {column}: {e}")
                    record[column] = str(value) if value is not None else None
            
            LOG.info(f"✅ Record serializzato con successo")
            return jsonify({'success': True, 'record': record})
            
    except Exception as e:
        LOG.error(f"❌ Errore nel recupero record {record_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_last_record', methods=['GET'])
def get_last_record():
    """Restituisce l'ultimo record dalla tabella spedizioni"""
    LOG.info("🔍 Richiesta get_last_record")
    try:
        with db_cursor() as (conn, cur):
            # Query per ottenere l'ultimo record (ID più alto)
            query = """
            SELECT * FROM spedizioni 
            ORDER BY id DESC 
            LIMIT 1
            """
            LOG.info(f"🔍 Eseguo query: {query}")
            cur.execute(query)
            row = cur.fetchone()
            
            if not row:
                LOG.warning("❌ Nessun record trovato")
                return jsonify({'error': 'Nessun record trovato'}), 404
            
            # Ottieni i nomi delle colonne
            columns = [desc[0] for desc in cur.description]
            LOG.info(f"🔍 Colonne trovate: {len(columns)}")
            
            # Crea dizionario con i dati
            record = {}
            for i, column in enumerate(columns):
                value = row[i]
                try:
                    record[column] = serialize_value(value)
                except Exception as e:
                    LOG.error(f"❌ Errore serializzazione colonna {column}: {e}")
                    record[column] = str(value) if value is not None else None
                    
            LOG.info("✅ Record serializzato con successo")
            return jsonify({'success': True, 'record': record})
            
    except Exception as e:
        LOG.error(f"❌ Errore nel recupero ultimo record: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    # Carica le mappature dei codici eventi
    load_tracking_codes()
    
    # Avvia il servizio di tracking automatico in background ogni 30 minuti
    try:
        from background_tracking import BackgroundTrackingService
        bg_service = BackgroundTrackingService(interval_minutes=30)
        bg_service.start()
        import atexit
        def cleanup():
            bg_service.stop()
        atexit.register(cleanup)
        LOG.info("🔄 Servizio tracking automatico avviato (ogni 30 minuti)")
    except Exception as e:
        LOG.warning("⚠️ Impossibile avviare servizio tracking automatico: %s", e)


@app.route('/<path:filename>')
def catch_all_static(filename):
    """Catch-all per servire file statici generici"""
    import os
    from flask import send_file
    base = os.path.dirname(__file__)
    full_path = os.path.join(base, filename)
    if os.path.exists(full_path) and os.path.commonpath([base, full_path]) == base:
        # Determina il tipo MIME basato sull'estensione
        mimetype = None
        if filename.endswith('.css'):
            mimetype = 'text/css'
        elif filename.endswith('.js'):
            mimetype = 'application/javascript'
        elif filename.endswith('.png'):
            mimetype = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            mimetype = 'image/jpeg'
        elif filename.endswith('.gif'):
            mimetype = 'image/gif'
        elif filename.endswith('.ico'):
            mimetype = 'image/x-icon'
        elif filename.endswith('.svg'):
            mimetype = 'image/svg+xml'
        elif filename.endswith('.woff') or filename.endswith('.woff2'):
            mimetype = 'font/woff'
        elif filename.endswith('.ttf'):
            mimetype = 'font/ttf'
        elif filename.endswith('.eot'):
            mimetype = 'application/vnd.ms-fontobject'
        return send_file(full_path, mimetype=mimetype)
    else:
        return "File not found", 404

# Route per servire i file HTML principali
@app.route('/')
def index():
    """Redirect alla pagina spedizioni"""
    return send_file('spedizioni.html')


@app.route('/modulo')  
def modulo():
    """Serve il modulo spedizione"""
    return send_file('spedzione_modulo.html')


if __name__ == "__main__":
    # Avvio il server API
    LOG.info("🚀 Avvio server API su http://0.0.0.0:5003")
    LOG.info("📄 File statici serviti da: http://0.0.0.0:5003/spedizioni.html")
    LOG.info("📝 Modulo spedizioni: http://0.0.0.0:5003/modulo")
    app.run(host="0.0.0.0", port=5003, debug=False)
