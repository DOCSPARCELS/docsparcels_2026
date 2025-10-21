"""
SDA (Poste Italiane) Tracking API Module
========================================

Modulo per il tracking delle spedizioni SDA tramite API Poste Italiane.
Supporta autenticazione OAuth2 e recupero eventi di tracking.

Author: Sistema Spedizioni 2026
Date: 11 ottobre 2025
"""

import os
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Carica variabili ambiente
load_dotenv()

class SDATracking:
    """
    Classe per gestire il tracking SDA tramite API Poste Italiane.
    
    Funzionalità:
    - Autenticazione OAuth2 con client_credentials
    - Recupero eventi tracking spedizioni SDA
    - Gestione cache token di accesso
    - Parsing strutturato degli eventi
    """
    
    def __init__(self, environment='dev'):
        """
        Inizializza il client SDA tracking.
        
        Args:
            environment (str): 'dev' per sviluppo, 'prod' per produzione
        """
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        
        # Cache per il token di accesso
        self.access_token = None
        self.token_expires_at = None
        
        # Configurazione environment
        if environment == 'prod':
            self.auth_url = os.getenv('SDA_AUTH_URL_PROD')
            self.base_url = os.getenv('SDA_BASE_URL_PROD')
            self.client_id = os.getenv('SDA_AUTH_CLIENT_ID_PROD')
            self.client_secret = os.getenv('SDA_AUTH_SECRET_ID_PROD')
            self.scope = os.getenv('SDA_AUTH_SCOPE_PROD')
            self.cost_center = os.getenv('SDA_COST_CENTER_CODE_PROD')
        else:
            self.auth_url = os.getenv('SDA_AUTH_URL_DEV')
            self.base_url = os.getenv('SDA_BASE_URL_DEV')
            self.client_id = os.getenv('SDA_AUTH_CLIENT_ID_DEV')
            self.client_secret = os.getenv('SDA_AUTH_SECRET_ID_DEV')
            self.scope = os.getenv('SDA_AUTH_SCOPE_DEV')
            self.cost_center = os.getenv('SDA_COST_CENTER_CODE_DEV')
        
        self.grant_type = os.getenv('SDA_AUTH_GRANT_TYPE', 'client_credentials')
        self.debug = bool(int(os.getenv('SDA_API_DEBUG', '0')))
        
        # Validazione configurazione
        if not all([self.auth_url, self.base_url, self.client_id, self.client_secret]):
            raise ValueError(f"Configurazione SDA incompleta per environment '{environment}'")
    
    def _get_access_token(self) -> str:
        """
        Ottiene un token di accesso OAuth2 valido.
        Gestisce la cache del token per evitare richieste eccessive.
        
        Returns:
            str: Token di accesso valido
            
        Raises:
            Exception: Se l'autenticazione fallisce
        """
        # Controlla se il token è ancora valido
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at - timedelta(minutes=5)):
            return self.access_token
        
        # Richiedi nuovo token - API Poste Italiane ha formato specifico
        auth_data = {
            'grant_type': self.grant_type,
            'clientId': self.client_id,      # Nota: clientId (non client_id)
            'secretId': self.client_secret,  # Nota: secretId (non client_secret)
            'scope': self.scope
        }
        
        headers = {
            'Content-Type': 'application/json',
            'POSTE_clientID': self.client_id  # Header richiesto da Poste Italiane
        }
        
        if self.debug:
            self.logger.info(f"🔑 Richiesta token SDA: {self.auth_url}")
            self.logger.debug(f"Auth data: {auth_data}")
        
        try:
            response = requests.post(
                self.auth_url,
                json=auth_data,  # Usa json= invece di data= per inviare JSON
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                if self.debug:
                    self.logger.info(f"📋 Risposta token completa: {token_data}")
                
                # Poste Italiane potrebbe usare nomi diversi per il token
                self.access_token = (
                    token_data.get('access_token') or 
                    token_data.get('accessToken') or
                    token_data.get('token') or
                    token_data.get('access')
                )
                
                # Calcola scadenza token (default 1 ora se non specificato)
                expires_in = token_data.get('expires_in', token_data.get('expiresIn', 3600))
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                if self.debug:
                    self.logger.info(f"✅ Token SDA ottenuto: {self.access_token[:20] if self.access_token else 'NONE'}...")
                    self.logger.info(f"✅ Scade: {self.token_expires_at}")
                
                return self.access_token
            else:
                error_msg = f"Errore autenticazione SDA: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.RequestException as e:
            error_msg = f"Errore connessione autenticazione SDA: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def track_shipment(self, waybill_number: str, full_tracking: bool = True) -> Dict[str, Any]:
        """
        Esegue il tracking di una spedizione SDA.
        
        Args:
            waybill_number (str): Numero lettera di vettura SDA
            full_tracking (bool): True per tutti gli eventi, False solo ultimo stato
            
        Returns:
            Dict[str, Any]: Dati strutturati del tracking
            
        Raises:
            Exception: Se il tracking fallisce
        """
        # Ottieni token di accesso
        access_token = self._get_access_token()
        
        # Parametri richiesta
        params = {
            'waybillNumber': waybill_number,
            'lastTracingState': 'N' if full_tracking else 'S',
            'statusDescription': 'E',
            'customerType': 'DQ'
        }
        
        # Headers richiesta
        headers = {
            'Authorization': f'Bearer {access_token}',
            'POSTE_clientID': self.client_id,
            'Content-Type': 'application/json'
        }
        
        # URL endpoint tracking
        tracking_url = f"{self.base_url}tracking"
        
        if self.debug:
            self.logger.info(f"🔍 Tracking SDA: {waybill_number}")
            self.logger.debug(f"URL: {tracking_url}")
            self.logger.debug(f"Params: {params}")
        
        try:
            response = requests.get(
                tracking_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            if self.debug:
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_tracking_response(data, waybill_number)
            else:
                error_msg = f"Errore tracking SDA {waybill_number}: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.RequestException as e:
            error_msg = f"Errore connessione tracking SDA {waybill_number}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _parse_tracking_response(self, data: Dict[str, Any], waybill_number: str) -> Dict[str, Any]:
        """
        Parsa la risposta dell'API tracking SDA.
        
        Args:
            data (Dict[str, Any]): Risposta API grezza
            waybill_number (str): Numero lettera di vettura
            
        Returns:
            Dict[str, Any]: Dati tracking strutturati
        """
        result = {
            'waybill_number': waybill_number,
            'success': False,
            'message': '',
            'events': [],
            'last_event': None,
            'delivery_status': 'Unknown',
            'last_position': '',
            'status': 'Unknown'
        }
        
        try:
            return_data = data.get('return', {})
            outcome = return_data.get('outcome', 'KO')
            code = return_data.get('code', 999)
            
            if outcome == 'OK' and code == 0:
                result['success'] = True
                result['message'] = 'Tracking recuperato con successo'
                
                # Trova la spedizione
                shipments = return_data.get('shipment', [])
                for shipment in shipments:
                    if shipment.get('waybillNumber') == waybill_number:
                        result['product'] = shipment.get('product', '')
                        result['notification_flag'] = shipment.get('NotificationFlag', 'N')
                        result['return_flag'] = shipment.get('returnFlag', 'N')
                        
                        # Parsa eventi tracking
                        tracking_events = shipment.get('tracking', [])
                        result['events'] = self._parse_tracking_events(tracking_events)
                        
                        # Determina ultimo evento e stato consegna
                        if result['events']:
                            result['last_event'] = result['events'][0]  # Il primo è il più recente
                            result['delivery_status'] = self._determine_delivery_status(result['events'])
                            
                            # Aggiorna last_position e status con l'ultimo evento
                            last_event = result['events'][0]
                            result['last_position'] = last_event.get('status_description', '')  # Usa StatusDescription
                            result['status'] = last_event.get('phase', 'Unknown')
                        
                        break
                else:
                    result['message'] = f'Spedizione {waybill_number} non trovata nella risposta'
            else:
                result['message'] = f'Errore API SDA: {outcome} - codice {code}'
                
                # Estrai messaggi di errore se disponibili
                messages = return_data.get('messages', [])
                if messages:
                    for msg_group in messages:
                        if 'messages' in msg_group:
                            for msg in msg_group['messages']:
                                if msg:
                                    result['message'] += f' - {msg}'
        
        except Exception as e:
            result['message'] = f'Errore parsing risposta SDA: {str(e)}'
            self.logger.error(result['message'])
        
        return result
    
    def _parse_tracking_events(self, tracking_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parsa gli eventi di tracking SDA.
        
        Args:
            tracking_events (List[Dict[str, Any]]): Eventi raw dall'API
            
        Returns:
            List[Dict[str, Any]]: Eventi strutturati
        """
        events = []
        
        for event in tracking_events:
            try:
                # Parsing data evento
                event_datetime = None
                if event.get('data'):
                    try:
                        event_datetime = datetime.strptime(event['data'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        self.logger.warning(f"Formato data non valido: {event['data']}")
                
                parsed_event = {
                    'datetime': event_datetime,
                    'date': event_datetime.strftime('%Y-%m-%d') if event_datetime else '',
                    'time': event_datetime.strftime('%H:%M:%S') if event_datetime else '',
                    'status_code': event.get('status', ''),
                    'status_description': event.get('StatusDescription', ''),
                    'app_status_description': event.get('appStatusDescription', ''),
                    'synthesis_description': event.get('synthesisStatusDescription', ''),
                    'office_description': event.get('officeDescription', ''),
                    'office_id': event.get('officeId', ''),
                    'phase': event.get('phase', ''),
                    'location': event.get('officeDescription', '')
                }
                
                events.append(parsed_event)
                
            except Exception as e:
                self.logger.warning(f"Errore parsing evento SDA: {str(e)}")
                continue
        
        # Ordina eventi per data (più recente prima)
        events.sort(key=lambda x: x['datetime'] or datetime.min, reverse=True)
        
        return events
    
    def _determine_delivery_status(self, events: List[Dict[str, Any]]) -> str:
        """
        Determina lo stato di consegna basato sugli eventi.
        
        Args:
            events (List[Dict[str, Any]]): Lista eventi di tracking
            
        Returns:
            str: Stato consegna ('Delivered', 'In Transit', 'Exception', etc.)
        """
        if not events:
            return 'Unknown'
        
        last_event = events[0]
        status_code = last_event.get('status_code', '').upper()
        phase = last_event.get('phase', '').upper()
        description = last_event.get('status_description', '').upper()
        
        # Mapping stati consegna SDA
        if 'CONSEGNAT' in description or 'DELIVERED' in description:
            return 'Delivered'
        elif 'GIACENZA' in description or 'DEPOSITO' in description:
            return 'Available for Pickup'
        elif 'TENTATIV' in description or 'ATTEMPT' in description:
            return 'Delivery Attempted'
        elif 'TRANSITO' in phase or 'IN TRANSITO' in phase:
            return 'In Transit'
        elif 'RITORNO' in description or 'RETURN' in description:
            return 'Returned'
        elif 'ECCEZIONE' in description or 'EXCEPTION' in description:
            return 'Exception'
        else:
            return 'In Transit'
    
    def get_formatted_last_position(self, waybill_number: str) -> str:
        """
        Ottiene l'ultima posizione formattata per una spedizione.
        
        Args:
            waybill_number (str): Numero lettera di vettura
            
        Returns:
            str: Descrizione ultima posizione formattata
        """
        try:
            tracking_data = self.track_shipment(waybill_number, full_tracking=False)
            
            if tracking_data['success'] and tracking_data['last_event']:
                last_event = tracking_data['last_event']
                return last_event.get('synthesis_description', 
                                    last_event.get('status_description', 'Stato non disponibile'))
            else:
                return f"Errore tracking: {tracking_data['message']}"
                
        except Exception as e:
            self.logger.error(f"Errore get_formatted_last_position SDA {waybill_number}: {str(e)}")
            return f"Errore: {str(e)}"

# Test rapido se eseguito direttamente
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Test con numero di tracking di esempio
    sda = SDATracking(environment='dev')
    
    # Sostituisci con un numero di tracking reale per il test
    test_waybill = "ZA123456789IT"
    
    try:
        result = sda.track_shipment(test_waybill)
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(f"Errore test: {e}")