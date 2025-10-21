"""
Interfaccia standardizzata per il tracking BRT
Integra BRTTracking con il sistema unificato di tracking
"""

import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Dict, List, Optional
from brt_tracking import BRTTracking


class BRTTrackingInterface:
    """Interfaccia standardizzata per il tracking BRT"""
    
    def __init__(self):
        """Inizializza l'interfaccia BRT con configurazione da variabili d'ambiente"""
        
        # Credenziali da .env
        self.username = os.getenv('BRT_USER', '')
        self.password = os.getenv('BRT_PASSWORD', '')
        self.debug = os.getenv('BRT_API_DEBUG', '0') == '1'
        
        # URL base tracking
        self.base_url = "https://api.brt.it/rest/v1/tracking"
        
        # Valida configurazione
        if not self.username or not self.password:
            raise ValueError("Credenziali BRT mancanti. Verifica BRT_USER e BRT_PASSWORD in .env")
        
        # Inizializza client
        self.client = BRTTracking(
            username=self.username,
            password=self.password,
            base_url=self.base_url,
            debug=self.debug
        )
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
    
    def track(self, waybill_number: str) -> Dict:
        """
        Traccia una spedizione BRT
        
        Args:
            waybill_number: Numero spedizione BRT (segnacollo)
            
        Returns:
            Dict standardizzato con informazioni di tracking
        """
        try:
            # Valida input
            if not waybill_number or not waybill_number.strip():
                return {
                    'success': False,
                    'error': 'Numero spedizione richiesto',
                    'message': 'Il numero di spedizione BRT non può essere vuoto'
                }
            
            waybill_number = waybill_number.strip()
            
            if self.debug:
                self.logger.info(f"🔍 Tracking BRT: {waybill_number}")
            
            # Esegui tracking
            result = self.client.track(waybill_number)
            
            if result.get('success'):
                # Standardizza formato risposta
                tracking_data = self._standardize_response(result)
                
                if self.debug:
                    self.logger.info(f"✅ Tracking BRT {waybill_number} completato")
                
                return tracking_data
            else:
                self.logger.warning(f"❌ Tracking BRT {waybill_number} fallito: {result.get('message', 'Errore sconosciuto')}")
                return result
                
        except Exception as e:
            self.logger.error(f"Errore tracking BRT {waybill_number}: {str(e)}")
            return {
                'success': False,
                'error': 'Errore interno',
                'message': str(e)
            }
    
    def _standardize_response(self, brt_data: Dict) -> Dict:
        """
        Standardizza la risposta BRT nel formato comune del sistema
        
        Args:
            brt_data: Dati grezzi da BRT
            
        Returns:
            Dict nel formato standardizzato
        """
        try:
            # Estrai eventi e standardizzali
            events = self._standardize_events(brt_data.get('events', []))
            
            # Ultimo stato
            last_position = brt_data.get('last_position', 'Stato non disponibile')
            
            # Info consegna
            delivered = bool(brt_data.get('delivery_date'))
            delivery_info = None
            if delivered:
                delivery_info = {
                    'date': brt_data.get('delivery_date', ''),
                    'time': brt_data.get('delivery_time', ''),
                    'recipient': brt_data.get('recipient', '')
                }
            
            return {
                'success': True,
                'carrier': 'BRT',
                'waybill_number': brt_data.get('shipment_id', ''),
                'status': brt_data.get('status', ''),
                'status_description': brt_data.get('status_description', ''),
                'last_position': last_position,
                'delivered': delivered,
                'delivery_info': delivery_info,
                'events': events,
                'raw_data': brt_data.get('raw_data', {})
            }
            
        except Exception as e:
            self.logger.error(f"Errore standardizzazione risposta BRT: {str(e)}")
            return {
                'success': False,
                'error': 'Errore standardizzazione',
                'message': str(e),
                'raw_data': brt_data
            }
    
    def _standardize_events(self, brt_events: List[Dict]) -> List[Dict]:
        """
        Converte gli eventi BRT nel formato standard
        
        Args:
            brt_events: Lista eventi da BRT
            
        Returns:
            Lista eventi nel formato standardizzato
        """
        standardized_events = []
        
        try:
            for event in brt_events:
                # Formato standard evento
                std_event = {
                    'date': event.get('date', ''),
                    'time': event.get('time', ''),
                    'timestamp': event.get('timestamp', ''),
                    'code': event.get('code', ''),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'carrier': 'BRT'
                }
                standardized_events.append(std_event)
                
        except Exception as e:
            self.logger.error(f"Errore standardizzazione eventi BRT: {str(e)}")
        
        return standardized_events
    
    def validate_waybill_number(self, waybill_number: str) -> bool:
        """
        Valida il formato del numero spedizione BRT
        
        Args:
            waybill_number: Numero da validare
            
        Returns:
            True se valido, False altrimenti
        """
        if not waybill_number:
            return False
        
        waybill_number = waybill_number.strip()
        
        # BRT usa vari formati, controllo base
        if len(waybill_number) < 8 or len(waybill_number) > 35:
            return False
        
        # Deve essere alfanumerico
        return waybill_number.replace('-', '').replace('/', '').isalnum()
    
    def get_supported_formats(self) -> List[str]:
        """
        Restituisce i formati supportati per i numeri BRT
        
        Returns:
            Lista dei formati accettati
        """
        return [
            "Segnacollo BRT (8-35 caratteri alfanumerici)",
            "Formato: XXXXXXXXX",
            "Può contenere trattini o slash"
        ]