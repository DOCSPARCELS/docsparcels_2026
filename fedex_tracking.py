"""
FedEx Tracking API Client
Gestisce le chiamate API per il tracking delle spedizioni FedEx
"""

import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

class FedExTracking:
    def __init__(self):
        """Inizializza il client FedEx con le credenziali dal file .env"""
        self.debug = os.getenv('FEDEX_API_DEBUG', '0') == '1'
        
        # URL base (usa produzione con credenziali valide)
        self.base_url = os.getenv('FEDEX_URL_PROD', 'https://apis.fedex.com/')
        
        # Credenziali per autenticazione OAuth (TRANSIT per tracking)
        self.client_id = os.getenv('FEDEX_AUTH_CLIENT_TRANSIT_ID_PROD')
        self.client_secret = os.getenv('FEDEX_AUTH_SECRET_TRANSIT_ID_PROD')
        self.grant_type = os.getenv('FEDEX_AUTH_GRANT_TYPE', 'client_credentials')
        
        # Token di accesso (verrà ottenuto dinamicamente)
        self.access_token = None
        self.token_expires_at = None
        
        if self.debug:
            print(f"🔧 FedEx API Debug: URL={self.base_url}")
            print(f"🔧 FedEx API Debug: Client ID={self.client_id}")
            print(f"🔧 FedEx API Debug: Grant Type={self.grant_type}")
    
    def get_access_token(self) -> str:
        """Ottiene un token di accesso OAuth per le API FedEx"""
        try:
            # Controlla se abbiamo già un token valido
            if self.access_token and self.token_expires_at:
                if datetime.now() < self.token_expires_at:
                    return self.access_token
            
            # URL per ottenere il token
            token_url = f"{self.base_url}oauth/token"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': self.grant_type,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            if self.debug:
                print(f"🔧 FedEx Token Request: {token_url}")
                print(f"🔧 FedEx Token Data: {data}")
            
            response = requests.post(token_url, headers=headers, data=data)
            
            if self.debug:
                print(f"🔧 FedEx Token Response Status: {response.status_code}")
                print(f"🔧 FedEx Token Response Headers: {dict(response.headers)}")
                print(f"🔧 FedEx Token Response Body: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)  # Default 1 ora
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                if self.debug:
                    print(f"✅ FedEx Token ottenuto: {self.access_token[:20]}...")
                
                return self.access_token
            else:
                if self.debug:
                    print(f"❌ FedEx Token Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"❌ FedEx Token Exception: {str(e)}")
            return None
    
    def track_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """
        Esegue il tracking di una spedizione FedEx
        
        Args:
            tracking_number: Numero di tracking FedEx
            
        Returns:
            Dizionario con risultati tracking in formato standardizzato
        """
        try:
            # Ottieni token di accesso
            token = self.get_access_token()
            if not token:
                if self.debug:
                    print("❌ FedEx: Impossibile ottenere token di accesso")
                return {'success': False, 'error': 'Impossibile ottenere token OAuth'}
            
            # URL per tracking
            tracking_url = f"{self.base_url}track/v1/trackingnumbers"
            
            headers = {
                'Content-Type': 'application/json',
                'X-locale': 'en_US',
                'Authorization': f'Bearer {token}'
            }
            
            # Payload per la richiesta
            payload = {
                "includeDetailedScans": True,
                "trackingInfo": [
                    {
                        "trackingNumberInfo": {
                            "trackingNumber": tracking_number
                        }
                    }
                ]
            }
            
            if self.debug:
                print(f"🔧 FedEx Tracking Request: {tracking_url}")
                print(f"🔧 FedEx Tracking Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(tracking_url, headers=headers, json=payload)
            
            if self.debug:
                print(f"🔧 FedEx Response Status: {response.status_code}")
                print(f"🔧 FedEx Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                events = self._parse_tracking_response(data, tracking_number)
                
                if events:
                    # Determina lo status principale dall'ultimo evento
                    latest_event = events[0] if events else {}
                    status = latest_event.get('descrizione', 'In transito')
                    
                    return {
                        'success': True,
                        'status': status,
                        'description': f"FedEx tracking per {tracking_number}",
                        'events': events
                    }
                else:
                    return {'success': False, 'error': 'Nessun evento trovato'}
            else:
                if self.debug:
                    print(f"❌ FedEx Tracking Error: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'{response.status_code} - {response.text}'}
                
        except Exception as e:
            if self.debug:
                print(f"❌ FedEx Tracking Exception: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_tracking_response(self, data: Dict, tracking_number: str) -> List[Dict[str, Any]]:
        """
        Converte la risposta FedEx in formato standardizzato
        
        Args:
            data: Risposta JSON dell'API FedEx
            tracking_number: Numero di tracking
            
        Returns:
            Lista di eventi in formato standardizzato
        """
        events = []
        
        try:
            # Naviga nella struttura JSON di FedEx
            output = data.get('output', {})
            complete_track_results = output.get('completeTrackResults', [])
            
            for track_result in complete_track_results:
                track_results = track_result.get('trackResults', [])
                
                for result in track_results:
                    # Estrai gli eventi di scan
                    scan_events = result.get('scanEvents', [])
                    
                    for event in scan_events:
                        # Estrai informazioni evento
                        date_str = event.get('date', '')
                        event_type = event.get('eventType', '')
                        event_description = event.get('eventDescription', '')
                        derived_status = event.get('derivedStatus', '')
                        
                        # Estrai location se disponibile
                        scan_location = event.get('scanLocation', {})
                        location = self._format_location(scan_location)
                        
                        # Converti data in formato datetime
                        event_datetime = self._parse_fedex_datetime(date_str)
                        
                        # Crea evento standardizzato
                        standard_event = {
                            'data': event_datetime.strftime('%Y-%m-%d') if event_datetime else '',
                            'ora': event_datetime.strftime('%H:%M') if event_datetime else '',
                            'codice': event_type,
                            'descrizione': event_description or derived_status,
                            'luogo': location,
                            'raw_data': event  # Mantieni dati originali per debug
                        }
                        
                        events.append(standard_event)
                        
                        if self.debug:
                            print(f"🔧 FedEx Event: {standard_event}")
            
            # Ordina eventi per data (più recenti prima)
            events.sort(key=lambda x: x.get('data', '') + x.get('ora', ''), reverse=True)
            
            if self.debug:
                print(f"✅ FedEx: Trovati {len(events)} eventi per {tracking_number}")
            
            return events
            
        except Exception as e:
            if self.debug:
                print(f"❌ FedEx Parse Error: {str(e)}")
            return []
    
    def _format_location(self, location_data: Dict) -> str:
        """Formatta le informazioni di location da FedEx"""
        if not location_data:
            return ""
        
        parts = []
        
        city = location_data.get('city', '')
        state = location_data.get('stateOrProvinceCode', '')
        country = location_data.get('countryCode', '')
        
        if city:
            parts.append(city)
        if state:
            parts.append(state)
        if country:
            parts.append(country)
        
        return ", ".join(parts)
    
    def _parse_fedex_datetime(self, date_str: str) -> datetime:
        """
        Converte le date FedEx in oggetti datetime
        
        Args:
            date_str: Data in formato FedEx (es. "2018-02-02T12:01:00-07:00")
            
        Returns:
            Oggetto datetime o None se parsing fallisce
        """
        if not date_str:
            return None
        
        try:
            # FedEx usa formato ISO 8601 con timezone
            # Es: "2018-02-02T12:01:00-07:00"
            
            # Rimuovi timezone per semplicità (prendi solo data/ora)
            if '+' in date_str:
                date_str = date_str.split('+')[0]
            elif '-' in date_str and 'T' in date_str:
                # Attenzione: il '-' potrebbe essere parte del timezone
                parts = date_str.split('T')
                if len(parts) == 2:
                    time_part = parts[1]
                    if '-' in time_part:
                        time_part = time_part.split('-')[0]
                    date_str = f"{parts[0]}T{time_part}"
            
            # Parsing standard ISO
            return datetime.fromisoformat(date_str.replace('Z', ''))
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ FedEx Date Parse Error: {date_str} - {str(e)}")
            return None


def test_fedex_tracking():
    """Funzione di test per il tracking FedEx"""
    tracker = FedExTracking()
    
    # Numero di test (dovrebbe essere uno valido per il tuo account)
    test_tracking_number = "123456789012"  # Sostituisci con numero reale
    
    print(f"🧪 Test FedEx Tracking per: {test_tracking_number}")
    events = tracker.track_shipment(test_tracking_number)
    
    print(f"\n📋 Risultati: {len(events)} eventi trovati")
    for i, event in enumerate(events, 1):
        print(f"{i}. {event['data']} {event['ora']} - {event['codice']}: {event['descrizione']} ({event['luogo']})")


if __name__ == "__main__":
    test_fedex_tracking()