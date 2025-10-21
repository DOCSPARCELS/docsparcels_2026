"""
Interfaccia web per testing del tracking FedEx
"""

from flask import Flask, render_template_string, request, jsonify
import sys
import os

# Aggiungi il percorso del progetto per importare i moduli
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fedex_tracking import FedExTracking

app = Flask(__name__)

# Template HTML per l'interfaccia
TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test FedEx Tracking API</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            color: #4C2C8B;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        input[type="text"]:focus {
            border-color: #4C2C8B;
            outline: none;
        }
        .btn {
            background-color: #4C2C8B;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }
        .btn:hover {
            background-color: #3A1E6B;
        }
        .btn:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .results {
            margin-top: 30px;
        }
        .event {
            background: #f8f9fa;
            border-left: 4px solid #4C2C8B;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 0 5px 5px 0;
        }
        .event-header {
            font-weight: bold;
            color: #4C2C8B;
            margin-bottom: 5px;
        }
        .event-details {
            color: #666;
            font-size: 14px;
        }
        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #f5c6cb;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #c3e6cb;
        }
        .info-box {
            background-color: #e7f3ff;
            border: 1px solid #b3d7ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .stat {
            text-align: center;
        }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
            color: #4C2C8B;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚚 Test FedEx Tracking API</h1>
            <p>Interfaccia di test per verificare il tracking delle spedizioni FedEx</p>
        </div>

        <div class="info-box">
            <strong>ℹ️ Informazioni:</strong>
            <ul>
                <li>Inserisci un numero di tracking FedEx valido</li>
                <li>L'API utilizza le credenziali sandbox configurate nel file .env</li>
                <li>La risposta mostrerà tutti gli eventi di tracking disponibili</li>
            </ul>
        </div>

        <form id="trackingForm">
            <div class="form-group">
                <label for="tracking_number">Numero di Tracking FedEx:</label>
                <input type="text" id="tracking_number" name="tracking_number" 
                       placeholder="Esempio: 123456789012" required>
            </div>
            
            <button type="submit" class="btn" id="submitBtn">
                🔍 Traccia Spedizione
            </button>
        </form>

        <div id="results" class="results" style="display: none;">
            <h3>📋 Risultati Tracking</h3>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        document.getElementById('trackingForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const trackingNumber = document.getElementById('tracking_number').value.trim();
            const submitBtn = document.getElementById('submitBtn');
            const results = document.getElementById('results');
            const resultsContent = document.getElementById('resultsContent');
            
            if (!trackingNumber) {
                alert('Inserisci un numero di tracking');
                return;
            }
            
            // Mostra loading
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Caricamento...';
            results.style.display = 'block';
            resultsContent.innerHTML = '<div class="loading">🔄 Chiamata API FedEx in corso...</div>';
            
            // Chiamata AJAX
            fetch('/track', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tracking_number: trackingNumber
                })
            })
            .then(response => response.json())
            .then(data => {
                submitBtn.disabled = false;
                submitBtn.textContent = '🔍 Traccia Spedizione';
                
                if (data.success) {
                    displayResults(data.events, trackingNumber);
                } else {
                    resultsContent.innerHTML = `
                        <div class="error">
                            ❌ <strong>Errore:</strong> ${data.error || 'Errore durante il tracking'}
                        </div>
                    `;
                }
            })
            .catch(error => {
                submitBtn.disabled = false;
                submitBtn.textContent = '🔍 Traccia Spedizione';
                resultsContent.innerHTML = `
                    <div class="error">
                        ❌ <strong>Errore di connessione:</strong> ${error.message}
                    </div>
                `;
            });
        });
        
        function displayResults(events, trackingNumber) {
            const resultsContent = document.getElementById('resultsContent');
            
            if (!events || events.length === 0) {
                resultsContent.innerHTML = `
                    <div class="error">
                        ⚠️ Nessun evento trovato per il tracking <strong>${trackingNumber}</strong>
                    </div>
                `;
                return;
            }
            
            // Statistiche
            let statsHtml = `
                <div class="stats">
                    <div class="stat">
                        <div class="stat-number">${events.length}</div>
                        <div class="stat-label">Eventi Totali</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${trackingNumber}</div>
                        <div class="stat-label">Numero Tracking</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">FedEx</div>
                        <div class="stat-label">Vettore</div>
                    </div>
                </div>
            `;
            
            // Lista eventi
            let eventsHtml = '';
            events.forEach((event, index) => {
                eventsHtml += `
                    <div class="event">
                        <div class="event-header">
                            📅 ${event.data || 'N/A'} ${event.ora || ''} - ${event.codice || 'N/A'}
                        </div>
                        <div class="event-details">
                            <strong>Descrizione:</strong> ${event.descrizione || 'N/A'}<br>
                            <strong>Luogo:</strong> ${event.luogo || 'N/A'}
                        </div>
                    </div>
                `;
            });
            
            resultsContent.innerHTML = `
                <div class="success">
                    ✅ <strong>Tracking completato!</strong> Trovati ${events.length} eventi per ${trackingNumber}
                </div>
                ${statsHtml}
                <h4>📝 Eventi di Tracking:</h4>
                ${eventsHtml}
            `;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Pagina principale con form di tracking"""
    return render_template_string(TEMPLATE)

@app.route('/track', methods=['POST'])
def track():
    """Endpoint per eseguire il tracking"""
    try:
        data = request.get_json()
        tracking_number = data.get('tracking_number', '').strip()
        
        if not tracking_number:
            return jsonify({
                'success': False,
                'error': 'Numero di tracking richiesto'
            })
        
        # Inizializza tracker FedEx
        tracker = FedExTracking()
        
        # Esegui tracking
        events = tracker.track_shipment(tracking_number)
        
        return jsonify({
            'success': True,
            'events': events,
            'tracking_number': tracking_number,
            'total_events': len(events)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore interno: {str(e)}'
        })

if __name__ == '__main__':
    print("🚀 Avvio server test FedEx Tracking...")
    print("📍 Apri il browser su: http://127.0.0.1:5002")
    print("🔧 Debug mode: ON")
    app.run(debug=True, host='127.0.0.1', port=5002)