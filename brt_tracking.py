"""
Modulo per il tracking BRT
Implementa le chiamate API REST per il tracking delle spedizioni BRT
"""

import json
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime


class BRTTracking:
    """Client per le API di tracking BRT"""
    
    def __init__(self, username: str, password: str, base_url: str = "https://api.brt.it/rest/v1/tracking", debug: bool = False):
        """
        Inizializza il client BRT tracking
        
        Args:
            username: Username BRT
            password: Password BRT  
            base_url: URL base dell'API BRT
            debug: Flag per logging dettagliato
        """
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip('/')
        self.debug = debug
        
        # Setup logging
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)
        
    def track(self, parcel_id: str) -> Dict:
        """
        Esegue il tracking di una spedizione BRT
        
        Args:
            parcel_id: Numero spedizione BRT (segnacollo)
            
        Returns:
            Dict con le informazioni di tracking
        """
        try:
            # Costruisci URL endpoint
            url = f"{self.base_url}/parcelID/{parcel_id}"
            
            # Headers con autenticazione
            headers = {
                'userID': self.username,
                'password': self.password,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            if self.debug:
                self.logger.debug(f"BRT Tracking URL: {url}")
                self.logger.debug(f"BRT Headers: {headers}")
            
            # Chiamata API
            response = requests.get(url, headers=headers, timeout=30)
            
            if self.debug:
                self.logger.debug(f"BRT Response Status: {response.status_code}")
                self.logger.debug(f"BRT Response: {response.text}")
            
            # Gestisci risposta
            if response.status_code == 200:
                data = response.json()
                return self._parse_tracking_response(data)
            else:
                self.logger.error(f"Errore BRT API: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'message': response.text
                }
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Errore connessione BRT: {str(e)}")
            return {
                'success': False,
                'error': 'Errore connessione',
                'message': str(e)
            }
        except Exception as e:
            self.logger.error(f"Errore generico BRT tracking: {str(e)}")
            return {
                'success': False,
                'error': 'Errore generico',
                'message': str(e)
            }
    
    def _parse_tracking_response(self, data: Dict) -> Dict:
        """
        Elabora la risposta JSON dell'API BRT
        
        Args:
            data: Risposta JSON dell'API
            
        Returns:
            Dict con dati parsing standardizzati
        """
        try:
            # Struttura risposta BRT
            if 'ttParcelIdResponse' not in data:
                return {
                    'success': False,
                    'error': 'Formato risposta non valido',
                    'message': 'Chiave ttParcelIdResponse mancante'
                }
            
            response_data = data['ttParcelIdResponse']
            
            # Verifica esito
            esito = response_data.get('esito', -1)
            execution_message = response_data.get('executionMessage', {})
            
            if esito != 0:  # 0 = successo in BRT
                error_code = execution_message.get('code', esito)
                error_message = execution_message.get('message', 'Errore sconosciuto')
                return {
                    'success': False,
                    'error': f'Errore BRT {error_code}',
                    'message': error_message
                }
            
            # Estrai dati spedizione
            bolla = response_data.get('bolla', {})
            dati_spedizione = bolla.get('dati_spedizione', {})
            dati_consegna = bolla.get('dati_consegna', {})
            
            # Estrai eventi
            eventi = self._extract_events(response_data)
            
            # Determina ultimo stato
            last_event = eventi[0] if eventi else None
            last_position = self._get_last_position(last_event, dati_spedizione, dati_consegna)
            
            return {
                'success': True,
                'shipment_id': dati_spedizione.get('spedizione_id', ''),
                'status': dati_spedizione.get('stato_sped_parte1', ''),
                'status_description': dati_spedizione.get('descrizione_stato_sped_parte1', ''),
                'last_position': last_position,
                'delivery_date': dati_consegna.get('data_consegna_merce', ''),
                'delivery_time': dati_consegna.get('ora_consegna_merce', ''),
                'recipient': dati_consegna.get('firmatario_consegna', ''),
                'events': eventi,
                'raw_data': data
            }
            
        except Exception as e:
            self.logger.error(f"Errore parsing risposta BRT: {str(e)}")
            return {
                'success': False,
                'error': 'Errore parsing',
                'message': str(e),
                'raw_data': data
            }
    
    def _extract_events(self, response_data: Dict) -> List[Dict]:
        """
        Estrae gli eventi di tracking dalla risposta
        
        Args:
            response_data: Dati della risposta
            
        Returns:
            Lista di eventi ordinati per data/ora decrescente
        """
        eventi = []
        
        try:
            lista_eventi = response_data.get('lista_eventi', [])
            
            for item in lista_eventi:
                evento_data = item.get('evento', {})
                
                if evento_data:
                    # Formatta data e ora
                    data_str = evento_data.get('data', '')
                    ora_str = evento_data.get('ora', '')
                    
                    # Crea timestamp
                    timestamp = self._create_timestamp(data_str, ora_str)
                    
                    evento = {
                        'date': data_str,
                        'time': ora_str,
                        'timestamp': timestamp,
                        'code': evento_data.get('id', ''),
                        'description': evento_data.get('descrizione', ''),
                        'location': evento_data.get('filiale', ''),
                        'raw_event': evento_data
                    }
                    eventi.append(evento)
            
            # Ordina per timestamp decrescente (più recente primo)
            eventi.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Errore estrazione eventi BRT: {str(e)}")
        
        return eventi
    
    def _create_timestamp(self, data_str: str, ora_str: str) -> str:
        """
        Crea timestamp da data e ora BRT
        
        Args:
            data_str: Data formato DD/MM/YYYY o YYYY-MM-DD
            ora_str: Ora formato HH:MM
            
        Returns:
            Timestamp formato ISO
        """
        try:
            # Parse data - BRT può usare DD/MM/YYYY o YYYY-MM-DD
            if '/' in data_str:
                # Formato DD/MM/YYYY
                date_obj = datetime.strptime(data_str, '%d/%m/%Y')
            elif '-' in data_str:
                # Formato YYYY-MM-DD
                date_obj = datetime.strptime(data_str, '%Y-%m-%d')
            else:
                return f"{data_str} {ora_str}"
            
            # Parse ora
            if ora_str and ':' in ora_str:
                time_parts = ora_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                # Combina data e ora
                datetime_obj = date_obj.replace(hour=hour, minute=minute)
                return datetime_obj.isoformat()
            else:
                return date_obj.isoformat()
                
        except Exception as e:
            self.logger.warning(f"Errore parsing timestamp BRT: {str(e)}")
            return f"{data_str} {ora_str}"
    
    def _get_last_position(self, last_event: Optional[Dict], dati_spedizione: Dict, dati_consegna: Dict) -> str:
        """
        Determina l'ultima posizione/stato della spedizione
        
        Args:
            last_event: Ultimo evento disponibile
            dati_spedizione: Dati della spedizione
            dati_consegna: Dati di consegna
            
        Returns:
            Descrizione dell'ultimo stato
        """
        # Se consegnata, mostra info consegna
        if dati_consegna.get('data_consegna_merce'):
            recipient = dati_consegna.get('firmatario_consegna', '')
            if recipient:
                return f"Consegnata a {recipient}"
            else:
                return "Consegnata"
        
        # Altrimenti usa ultimo evento o stato spedizione
        if last_event and last_event.get('description'):
            location = last_event.get('location', '')
            if location:
                return f"{last_event['description']} - {location}"
            else:
                return last_event['description']
        
        # Fallback su stato spedizione
        status = dati_spedizione.get('stato_sped_parte1', '')
        if status:
            return status
        
        return "Stato non disponibile"