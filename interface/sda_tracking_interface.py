"""
SDA Tracking Interface
=====================

Interfaccia semplificata per il tracking SDA compatibile con tracking_service.py.
Fornisce metodi standardizzati per l'integrazione nel sistema di tracking unificato.

Author: Sistema Spedizioni 2026
Date: 11 ottobre 2025
"""

import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Dict, Any, Optional
from sda_tracking import SDATracking

class SDATrackingInterface:
    """
    Interfaccia standardizzata per il tracking SDA.
    
    Fornisce metodi compatibili con il TrackingService per l'integrazione
    nel sistema di tracking unificato delle spedizioni.
    """
    
    def __init__(self, environment='dev'):
        """
        Inizializza l'interfaccia SDA tracking.
        
        Args:
            environment (str): 'dev' per sviluppo, 'prod' per produzione
        """
        self.sda_client = SDATracking(environment=environment)
        self.logger = logging.getLogger(__name__)
    
    def track(self, waybill_number: str) -> Dict[str, Any]:
        """
        Esegue il tracking di una spedizione SDA.
        
        Args:
            waybill_number (str): Numero lettera di vettura SDA
            
        Returns:
            Dict[str, Any]: Risultato tracking standardizzato
        """
        try:
            self.logger.info(f"🔍 Tracking SDA: {waybill_number}")
            
            # Chiama l'API SDA
            result = self.sda_client.track_shipment(waybill_number, full_tracking=True)
            
            if result['success']:
                # Standardizza la risposta per compatibilità con TrackingService
                standardized_result = {
                    'success': True,
                    'awb': waybill_number,
                    'vettore': 'SDA',
                    'last_position': self._get_last_position_description(result),
                    'delivery_status': result['delivery_status'],
                    'events': result['events'],
                    'raw_response': result,
                    'message': result['message']
                }
                
                self.logger.info(f"✅ Tracking SDA {waybill_number} completato")
                return standardized_result
            else:
                # Errore nel tracking
                error_result = {
                    'success': False,
                    'awb': waybill_number,
                    'vettore': 'SDA',
                    'last_position': f"Errore tracking: {result['message']}",
                    'delivery_status': 'Error',
                    'events': [],
                    'raw_response': result,
                    'message': result['message']
                }
                
                self.logger.warning(f"⚠️ Errore tracking SDA {waybill_number}: {result['message']}")
                return error_result
                
        except Exception as e:
            error_msg = f"Errore tracking SDA {waybill_number}: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'awb': waybill_number,
                'vettore': 'SDA',
                'last_position': f"Errore: {str(e)}",
                'delivery_status': 'Error',
                'events': [],
                'raw_response': None,
                'message': error_msg
            }
    
    def get_last_position(self, waybill_number: str) -> str:
        """
        Ottiene solo l'ultima posizione di una spedizione SDA.
        
        Args:
            waybill_number (str): Numero lettera di vettura SDA
            
        Returns:
            str: Descrizione ultima posizione
        """
        try:
            return self.sda_client.get_formatted_last_position(waybill_number)
        except Exception as e:
            self.logger.error(f"Errore get_last_position SDA {waybill_number}: {str(e)}")
            return f"Errore: {str(e)}"
    
    def _get_last_position_description(self, tracking_result: Dict[str, Any]) -> str:
        """
        Estrae la descrizione dell'ultima posizione dal risultato tracking.
        
        Args:
            tracking_result (Dict[str, Any]): Risultato del tracking SDA
            
        Returns:
            str: Descrizione ultima posizione
        """
        if not tracking_result.get('last_event'):
            return "Nessun evento disponibile"
        
        last_event = tracking_result['last_event']
        
        # Priorità descrizioni: synthesis > status > app
        description = (
            last_event.get('synthesis_description') or
            last_event.get('status_description') or  
            last_event.get('app_status_description') or
            "Stato non disponibile"
        )
        
        return description.strip()
    
    def validate_waybill_number(self, waybill_number: str) -> bool:
        """
        Valida il formato del numero lettera di vettura SDA.
        
        Args:
            waybill_number (str): Numero da validare
            
        Returns:
            bool: True se valido, False altrimenti
        """
        if not waybill_number or not isinstance(waybill_number, str):
            return False
        
        # Rimuovi spazi e converti a maiuscolo
        waybill = waybill_number.strip().upper()
        
        # Formati supportati da SDA secondo documentazione:
        # - 7 digit: solo numeri
        # - 9 digit: LdV Sticker  
        # - 13 digit: codice barcode
        # - 18 digit: codice esteso
        # - 16 digit: formato aggiuntivo (osservato in pratica)
        
        # Controllo lunghezza
        if len(waybill) not in [7, 9, 13, 16, 18]:
            return False
        
        # Controllo pattern base (può iniziare con lettere per formati internazionali)
        if len(waybill) >= 13:
            # Formato internazionale, può contenere lettere e numeri
            return waybill.isalnum()
        else:
            # Formato nazionale, solo numeri
            return waybill.isdigit()
    
    def get_tracking_events(self, waybill_number: str) -> list:
        """
        Ottiene tutti gli eventi di tracking per una spedizione.
        
        Args:
            waybill_number (str): Numero lettera di vettura
            
        Returns:
            list: Lista eventi di tracking
        """
        try:
            result = self.track(waybill_number)
            return result.get('events', [])
        except Exception as e:
            self.logger.error(f"Errore get_tracking_events SDA {waybill_number}: {str(e)}")
            return []
    
    def is_delivered(self, waybill_number: str) -> bool:
        """
        Verifica se una spedizione è stata consegnata.
        
        Args:
            waybill_number (str): Numero lettera di vettura
            
        Returns:
            bool: True se consegnata, False altrimenti
        """
        try:
            result = self.track(waybill_number)
            return result.get('delivery_status') == 'Delivered'
        except Exception as e:
            self.logger.error(f"Errore is_delivered SDA {waybill_number}: {str(e)}")
            return False

# Test rapido se eseguito direttamente
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test interfaccia SDA
    interface = SDATrackingInterface(environment='dev')
    
    # Test validazione numeri
    test_numbers = [
        "1234567",           # 7 digit valido
        "123456789",         # 9 digit valido  
        "ZA123456789IT",     # 13 digit valido internazionale
        "123456",            # Troppo corto
        "12345678901234567890",  # Troppo lungo
        "ABC123DEF456GHI",   # 16 digit con lettere
    ]
    
    print("Test validazione numeri lettera di vettura:")
    for num in test_numbers:
        is_valid = interface.validate_waybill_number(num)
        print(f"  {num}: {'✅ Valido' if is_valid else '❌ Non valido'}")
    
    # Test tracking (sostituisci con numero reale)
    test_waybill = "ZA123456789IT"
    print(f"\nTest tracking: {test_waybill}")
    
    try:
        result = interface.track(test_waybill)
        print(f"Successo: {result['success']}")
        print(f"Ultima posizione: {result['last_position']}")
        print(f"Stato consegna: {result['delivery_status']}")
        print(f"Eventi: {len(result['events'])}")
    except Exception as e:
        print(f"Errore test: {e}")