"""
DHL Tracking API Client - SOLO per tracking AWB
"""

import ssl
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import DHLConfig


class _TLS12HttpAdapter(HTTPAdapter):
    """HTTPAdapter che forza l'uso di TLS 1.2 e accetta cipher legacy DHL."""

    def __init__(self, *args, **kwargs):
        self._ssl_context = self._build_ssl_context()
        super().__init__(*args, **kwargs)

    @staticmethod
    def _build_ssl_context() -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        # Assicura TLS >= 1.2 (alcuni endpoint DHL rifiutano negoziazioni diverse)
        if hasattr(ctx, "minimum_version"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        else:  # fallback per vecchie versioni Python
            ctx.options |= getattr(ssl, "OP_NO_TLSv1", 0)
            ctx.options |= getattr(ssl, "OP_NO_TLSv1_1", 0)
        # Alcuni cluster DHL richiedono cipher legacy -> abbassiamo SECLEVEL
        try:
            ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        except ssl.SSLError:
            # se l'installazione OpenSSL non supporta la direttiva, ignoriamo
            pass
        return ctx

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["ssl_context"] = self._ssl_context
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs["ssl_context"] = self._ssl_context
        return super().proxy_manager_for(proxy, **proxy_kwargs)


class DHLTrackingClient:
    """Client DHL per tracking spedizioni"""
    
    def __init__(self, config=None):
        """Inizializza client tracking"""
        if config is None:
            config = DHLConfig.from_env()
        self.site_id = config.site_id
        self.password = config.password
        self.base_url = config.effective_url
        self.debug = getattr(config, 'debug', False)
        self.timeout = getattr(config, 'timeout', 30)
        self.max_retries = getattr(config, 'max_retries', 3)

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.7,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        self.session = requests.Session()
        adapter = _TLS12HttpAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "User-Agent": "DHLTrackingClient/2026 (+https://example.local)",
            "Connection": "close",
        })
    
    def track_shipment(self, awb_number: str) -> Dict:
        """
        Traccia una spedizione DHL
        
        Args:
            awb_number: Numero AWB da tracciare
            
        Returns:
            Dict con informazioni tracking o errore
        """
        try:
            # Create XML request
            xml_request = self._create_tracking_xml(awb_number)
            
            # Debug: mostra richiesta XML se abilitato
            if self.debug:
                print("DEBUG - RICHIESTA XML TRACKING:")
                print("=" * 50)
                print(xml_request)
                print("=" * 50)
            
            # Set headers
            headers = {
                'Content-Type': 'application/xml',
                'Accept': 'application/xml',
                'Connection': 'close',
            }
            
            # Make API request
            response = self.session.post(
                self.base_url,
                data=xml_request.encode('utf-8'),
                headers=headers,
                timeout=self.timeout
            )
            
            # Debug: mostra risposta XML se abilitato
            if self.debug:
                print("DEBUG - RISPOSTA XML TRACKING:")
                print("=" * 50)
                print(response.text)
                print("=" * 50)
            
            if response.status_code == 200:
                return self._parse_tracking_response(response.text, awb_number)
            else:
                return {
                    'error': f'HTTP {response.status_code}',
                    'tracking_number': awb_number
                }
                
        except requests.exceptions.RequestException as exc:
            return {
                'error': f'Connessione DHL fallita: {exc}',
                'tracking_number': awb_number
            }
        except Exception as e:
            return {
                'error': str(e),
                'tracking_number': awb_number
            }
    
    def _create_tracking_xml(self, awb_number: str) -> str:
        """Crea XML per richiesta tracking"""
        message_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+01:00'
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<req:KnownTrackingRequest xmlns:req="http://www.dhl.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.dhl.com track-req.xsd">
    <Request>
        <ServiceHeader>
            <MessageTime>{message_time}</MessageTime>
            <MessageReference>1234567890123456789012345678901</MessageReference>
            <SiteID>{self.site_id}</SiteID>
            <Password>{self.password}</Password>
        </ServiceHeader>
    </Request>
    <LanguageCode>en</LanguageCode>
    <AWBNumber>{awb_number}</AWBNumber>
    <LevelOfDetails>ALL_CHECK_POINTS</LevelOfDetails>
</req:KnownTrackingRequest>'''
    
    def _parse_tracking_response(self, xml_response: str, awb_number: str) -> Dict:
        """Parse risposta XML tracking"""
        try:
            root = ET.fromstring(xml_response)
            
            # Rimuovi i namespace per semplificare il parsing
            # Trova tutti gli elementi senza namespace specifico
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}')[1]
            
            # Controlla errori
            error_elements = root.findall('.//Condition')
            if error_elements:
                error_code = error_elements[0].find('.//ConditionCode')
                error_data = error_elements[0].find('.//ConditionData')
                
                error_code_text = error_code.text if error_code is not None else 'Unknown'
                error_data_text = error_data.text if error_data is not None else 'No details'
                
                return {
                    'error': f'DHL Error: {error_code_text}: {error_data_text}',
                    'tracking_number': awb_number
                }
            
            # Estrai informazioni tracking
            result = {
                'tracking_number': awb_number,
                'status_description': 'Unknown',
                'events': [],
                'origin': {},
                'destination': {}
            }
            
            # Trova AWBInfo
            awb_info = root.find('.//AWBInfo')
            if awb_info is not None:
                
                # Status
                status_elem = awb_info.find('.//ActionStatus')
                if status_elem is not None:
                    result['status_description'] = status_elem.text
                
                # Shipment info
                shipment_info = awb_info.find('.//ShipmentInfo')
                if shipment_info is not None:
                    
                    # Origin
                    origin_elem = shipment_info.find('.//OriginServiceArea')
                    if origin_elem is not None:
                        origin_desc = origin_elem.find('.//Description')
                        if origin_desc is not None:
                            result['origin']['description'] = origin_desc.text
                    
                    # Destination
                    dest_elem = shipment_info.find('.//DestinationServiceArea')
                    if dest_elem is not None:
                        dest_desc = dest_elem.find('.//Description')
                        if dest_desc is not None:
                            result['destination']['description'] = dest_desc.text
                
                    # Eventi
                    events = []
                    shipment_events = shipment_info.findall('.//ShipmentEvent')
                    
                    for event in shipment_events:
                        event_data = {}
                        
                        date_elem = event.find('.//Date')
                        time_elem = event.find('.//Time')
                        
                        if date_elem is not None:
                            event_data['date'] = date_elem.text
                        if time_elem is not None:
                            event_data['time'] = time_elem.text
                        
                        # Location
                        location_elem = event.find('.//ServiceArea')
                        if location_elem is not None:
                            desc_elem = location_elem.find('.//Description')
                            if desc_elem is not None:
                                event_data['location'] = desc_elem.text
                        
                        # Description (dal ServiceEvent)
                        service_event = event.find('.//ServiceEvent')
                        if service_event is not None:
                            desc_elem = service_event.find('.//Description')
                            if desc_elem is not None:
                                event_data['description'] = desc_elem.text
                            
                            # Event code
                            code_elem = service_event.find('.//EventCode')
                            if code_elem is not None:
                                event_data['event_code'] = code_elem.text
                        
                        events.append(event_data)
                    
                    result['events'] = events
                    
                    # Trova l'ultimo evento per lo status attuale
                    if events:
                        last_event = events[-1]
                        if last_event.get('description'):
                            result['status_description'] = last_event['description']
            
            return result
            
        except Exception as e:
            return {
                'error': f'Parse error: {str(e)}',
                'tracking_number': awb_number
            }


def test_tracking():
    """Test tracking"""
    import sys
    print("Test DHL Tracking")
    print("=" * 30)
    client = DHLTrackingClient()
    if len(sys.argv) > 1:
        test_awb = sys.argv[1]
    else:
        test_awb = "7343641620"  # default se non passato
    print(f"Tracking: {test_awb}")
    result = client.track_shipment(test_awb)
    if 'error' in result:
        print(f"Errore: {result['error']}")
    else:
        print(f"Status: {result.get('status_description', 'N/A')}")
        print(f"Origin: {result.get('origin', {}).get('description', 'N/A')}")
        print(f"Destination: {result.get('destination', {}).get('description', 'N/A')}")
        print(f"Events: {len(result.get('events', []))}")


if __name__ == "__main__":
    from db_connector import get_awb_in_transit, update_last_position
    print("Test tracking DHL per tutte le spedizioni in transito (final_position=0)")
    awb_list = get_awb_in_transit()
    print(f"Trovati {len(awb_list)} AWB in transito.")
    client = DHLTrackingClient()
    for i, awb in enumerate(awb_list, 1):
        print(f"\n--- {i}/{len(awb_list)} AWB: {awb} ---")
        result = client.track_shipment(awb)
        if 'error' in result:
            status = f"ERRORE: {result['error']}"
            print(f"❌ Errore: {result['error']}")
        else:
            status = result.get('status_description', 'N/A')
            print(f"✅ Status: {status}")
            print(f"   Origine: {result.get('origin', {}).get('description', 'N/A')}")
            print(f"   Destinazione: {result.get('destination', {}).get('description', 'N/A')}")
            print(f"   Eventi: {len(result.get('events', []))}")
        update_last_position(awb, status)
        print(f"   Aggiornato last_position nel DB: {status}")
