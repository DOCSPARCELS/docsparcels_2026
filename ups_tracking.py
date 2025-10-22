#!/usr/bin/env python3
"""
UPS Tracking Client - Versione Produzione

Client per tracking spedizioni UPS utilizzando XML API.
Ottimizzato per ambiente di produzione con gestione rate limiting avanzata.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
import time
from config import UPSConfig


class UPSTrackingClient:
    """Client per il tracking UPS con gestione rate limiting per produzione"""
    
    def __init__(self, config: Optional[UPSConfig] = None):
        """
        Inizializza il client UPS
        
        Args:
            config: Configurazione UPS (se None, carica da variabili d'ambiente)
        """
        self.config = config or UPSConfig.from_env()
        self.config.debug = True  # MODIFICATO: Attiva debug
        
        # Rate limiting ottimizzato per produzione
        self.min_delay_between_requests = 5.0  # 5 secondi tra richieste
        self.last_request_time = 0
        
        # Retry logic per gestire errori 429
        self.max_retries = 5
        self.retry_base_delay = 30  # 30 secondi base per retry
        
        # Statistiche
        self.request_count = 0
        self.error_count = 0
        
    def track_shipment(self, tracking_number: str, verbose: bool = True) -> Dict:
        """
        Traccia una spedizione UPS
        
        Args:
            tracking_number: Numero di tracking UPS
            verbose: Se True, mostra messaggi di progresso
            
        Returns:
            Dict con informazioni di tracking o errore
        """
        try:
            if verbose:
                print(f"Tracciamento in corso: {tracking_number}...")
            
            # Crea richiesta XML
            xml_request = self._create_tracking_xml(tracking_number)
            
            # Invia richiesta con retry
            xml_response = self._send_request_with_retry(xml_request, verbose)
            
            # Parse risposta
            result = self._parse_tracking_response(xml_response, tracking_number)
            
            self.request_count += 1
            
            if verbose and 'error' not in result:
                print(f"✓ Tracking completato: {result['status_description']}")
            
            return result
            
        except Exception as e:
            self.error_count += 1
            error_result = {
                'error': f'UPS tracking error: {str(e)}',
                'tracking_number': tracking_number
            }
            
            if verbose:
                print(f"✗ Errore nel tracking: {str(e)}")
            
            return error_result
    
    def track_multiple_shipments(self, tracking_numbers: List[str], verbose: bool = True) -> List[Dict]:
        """
        Traccia multiple spedizioni UPS con rate limiting automatico
        
        Args:
            tracking_numbers: Lista di numeri di tracking
            verbose: Se True, mostra progresso
            
        Returns:
            Lista di Dict con informazioni di tracking
        """
        results = []
        total = len(tracking_numbers)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Tracking di {total} spedizioni in corso...")
            print(f"Delay tra richieste: {self.min_delay_between_requests}s")
            print(f"{'='*60}\n")
        
        for i, tracking_number in enumerate(tracking_numbers, 1):
            if verbose:
                print(f"[{i}/{total}] ", end="")
            
            result = self.track_shipment(tracking_number, verbose)
            results.append(result)
            
            # Attesa tra richieste (tranne l'ultima)
            if i < total:
                if verbose:
                    print(f"    Attesa {self.min_delay_between_requests}s prima della prossima richiesta...\n")
                time.sleep(self.min_delay_between_requests)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Completato! Richieste: {self.request_count}, Errori: {self.error_count}")
            print(f"{'='*60}\n")
        
        return results
    
    def _create_tracking_xml(self, tracking_number: str) -> str:
        """
        Crea XML per richiesta tracking UPS
        
        Args:
            tracking_number: Numero di tracking
            
        Returns:
            Stringa XML formattata per UPS API
        """
        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<AccessRequest xml:lang="en-US">
    <AccessLicenseNumber>{self.config.license}</AccessLicenseNumber>
    <UserId>{self.config.username}</UserId>
    <Password>{self.config.password}</Password>
</AccessRequest>
<?xml version="1.0" encoding="UTF-8"?>
<TrackRequest xml:lang="en-US">
    <Request>
        <TransactionReference>
            <CustomerContext>Track Package</CustomerContext>
            <XpciVersion>1.0</XpciVersion>
        </TransactionReference>
        <RequestAction>Track</RequestAction>
        <RequestOption>1</RequestOption>
    </Request>
    <TrackingNumber>{tracking_number}</TrackingNumber>
</TrackRequest>"""
        
        return xml_template
    
    def _wait_for_rate_limit(self, verbose: bool = False):
        """
        Attende il tempo necessario per rispettare il rate limiting
        
        Args:
            verbose: Se True, mostra messaggi di debug
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_delay_between_requests:
            wait_time = self.min_delay_between_requests - time_since_last_request
            
            if verbose:
                print(f"    Rate limiting: attesa di {wait_time:.1f}s...")
            
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _send_request_with_retry(self, xml_data: str, verbose: bool = False) -> str:
        """
        Invia richiesta XML a UPS con retry logic per gestire errore 429
        
        Args:
            xml_data: XML della richiesta
            verbose: Se True, mostra messaggi di progresso
            
        Returns:
            Risposta XML da UPS
            
        Raises:
            Exception: Se tutti i retry falliscono
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Rispetta rate limiting
                if attempt == 0:
                    self._wait_for_rate_limit(verbose)
                
                # Invia richiesta
                response_text = self._send_request(xml_data)
                
                # Se arriva qui, la richiesta è andata a buon fine
                return response_text
                
            except requests.exceptions.HTTPError as e:
                last_error = e
                
                # Se è 429 (Too Many Requests), attendi e riprova
                if e.response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # Backoff esponenziale: 30s, 60s, 90s, 120s, 150s
                        wait_time = self.retry_base_delay * (attempt + 1)
                        
                        if verbose:
                            print(f"    ⚠ Rate limit raggiunto (tentativo {attempt + 1}/{self.max_retries})")
                            print(f"    Attesa di {wait_time}s prima di riprovare...")
                        
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            f"Rate limit superato dopo {self.max_retries} tentativi. "
                            f"Attendi alcuni minuti prima di riprovare."
                        )
                else:
                    # Per altri errori HTTP, solleva subito
                    raise Exception(f"HTTP Error {e.response.status_code}: {str(e)}")
                    
            except Exception as e:
                # Per altri errori, solleva subito
                raise Exception(f"Request error: {str(e)}")
        
        # Se arriviamo qui, tutti i retry sono falliti
        if last_error:
            raise last_error
        else:
            raise Exception("Richiesta fallita dopo tutti i retry")
    
    def _send_request(self, xml_data: str) -> str:
        """
        Invia richiesta XML a UPS
        
        Args:
            xml_data: XML della richiesta
            
        Returns:
            Risposta XML
            
        Raises:
            requests.exceptions.RequestException: Se la richiesta fallisce
        """
        # Endpoint UPS per tracking
        url = f"{self.config.effective_url}ups.app/xml/Track"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UPS-Python-Client/1.0'
        }
        
        try:
            # Debug output richiesta
            if self.config.debug:
                print(f"\nDEBUG - URL: {url}")
                print(f"DEBUG - RICHIESTA XML UPS:")
                print("=" * 50)
                print(xml_data)
                print("=" * 50)
            
            # Invia richiesta
            response = requests.post(
                url,
                data=xml_data,
                headers=headers,
                timeout=self.config.timeout
            )
            
            # Solleva eccezione per status code 4xx/5xx
            response.raise_for_status()
            
            # Debug output risposta - FORMATTATO
            if self.config.debug:
                print(f"DEBUG - RISPOSTA XML UPS:")
                print("=" * 50)
                try:
                    import xml.dom.minidom
                    dom = xml.dom.minidom.parseString(response.text)
                    print(dom.toprettyxml())
                except:
                    # Fallback se il parsing fallisce
                    print(response.text)
                print("=" * 50)
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            raise
    
    def _parse_tracking_response(self, xml_response: str, tracking_number: str) -> Dict:
        """
        Parse risposta XML tracking UPS
        
        Args:
            xml_response: XML di risposta da UPS
            tracking_number: Numero di tracking originale
            
        Returns:
            Dict con dati di tracking strutturati
        """
        try:
            root = ET.fromstring(xml_response)
            
            # Controlla errori nella risposta
            error_elem = root.find('.//Error')
            if error_elem is not None:
                error_code = error_elem.find('.//ErrorCode')
                error_desc = error_elem.find('.//ErrorDescription')
                
                error_code_text = error_code.text if error_code is not None else 'Unknown'
                error_desc_text = error_desc.text if error_desc is not None else 'No description'
                
                return {
                    'error': f'UPS Error {error_code_text}: {error_desc_text}',
                    'tracking_number': tracking_number
                }
            
            # Inizializza risultato
            result = {
                'tracking_number': tracking_number,
                'status_description': 'Unknown',
                'status_code': None,
                'events': [],
                'origin': {},
                'destination': {},
                'service_type': '',
                'estimated_delivery': None,
                'weight': None
            }
            
            # Trova Shipment element
            shipment = root.find('.//Shipment')
            if shipment is not None:
                
                # Service Type
                service_elem = shipment.find('.//Service/Description')
                if service_elem is not None:
                    result['service_type'] = service_elem.text
                
                # Weight
                weight_elem = shipment.find('.//ShipmentWeight')
                if weight_elem is not None:
                    weight_value = weight_elem.find('.//Weight')
                    weight_unit = weight_elem.find('.//UnitOfMeasurement/Code')
                    if weight_value is not None and weight_unit is not None:
                        result['weight'] = f"{weight_value.text} {weight_unit.text}"
                
                # Shipper (origine)
                shipper = shipment.find('.//Shipper')
                if shipper is not None:
                    address = shipper.find('.//Address')
                    if address is not None:
                        city = address.find('.//City')
                        state = address.find('.//StateProvinceCode')
                        country = address.find('.//CountryCode')
                        
                        origin_parts = []
                        if city is not None:
                            origin_parts.append(city.text)
                        if state is not None:
                            origin_parts.append(state.text)
                        if country is not None:
                            origin_parts.append(country.text)
                        
                        result['origin']['description'] = ', '.join(origin_parts)
                
                # ShipTo (destinazione)
                ship_to = shipment.find('.//ShipTo')
                if ship_to is not None:
                    address = ship_to.find('.//Address')
                    if address is not None:
                        city = address.find('.//City')
                        state = address.find('.//StateProvinceCode')
                        country = address.find('.//CountryCode')
                        
                        dest_parts = []
                        if city is not None:
                            dest_parts.append(city.text)
                        if state is not None:
                            dest_parts.append(state.text)
                        if country is not None:
                            dest_parts.append(country.text)
                        
                        result['destination']['description'] = ', '.join(dest_parts)
            
            # Package tracking info
            package = root.find('.//Package')
            if package is not None:
                
                # Activity (eventi)
                activities = package.findall('.//Activity')
                events = []
                
                for activity in activities:
                    event_data = {}
                    
                    # Status
                    status = activity.find('.//Status')
                    if status is not None:
                        status_type = status.find('.//StatusType/Description')
                        status_desc = status.find('.//StatusCode/Description')
                        status_code = status.find('.//StatusCode/Code')
                        
                        if status_type is not None:
                            event_data['status_type'] = status_type.text
                        
                        if status_desc is not None:
                            event_data['description'] = status_desc.text
                        elif status_type is not None:
                            event_data['description'] = status_type.text
                        
                        if status_code is not None:
                            event_data['event_code'] = status_code.text
                    
                    # Date and Time
                    date_elem = activity.find('.//Date')
                    time_elem = activity.find('.//Time')
                    
                    if date_elem is not None:
                        date_str = date_elem.text
                        # Formato UPS: YYYYMMDD
                        if len(date_str) == 8:
                            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            event_data['date'] = formatted_date
                    
                    if time_elem is not None:
                        time_str = time_elem.text
                        # Formato UPS: HHMMSS
                        if len(time_str) == 6:
                            formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                            event_data['time'] = formatted_time
                    
                    # Location
                    location = activity.find('.//ActivityLocation')
                    if location is not None:
                        address = location.find('.//Address')
                        if address is not None:
                            city = address.find('.//City')
                            state = address.find('.//StateProvinceCode')
                            country = address.find('.//CountryCode')
                            
                            location_parts = []
                            if city is not None:
                                location_parts.append(city.text)
                            if state is not None:
                                location_parts.append(state.text)
                            if country is not None:
                                location_parts.append(country.text)
                            
                            event_data['location'] = ', '.join(location_parts)
                    
                    events.append(event_data)
                
                result['events'] = events
                
                # Ultimo status come status principale
                if events:
                    last_event = events[0]  # UPS events sono in ordine cronologico inverso
                    if last_event.get('description'):
                        result['status_description'] = last_event['description']
                    if last_event.get('event_code'):
                        result['status_code'] = last_event['event_code']
            
            return result
            
        except Exception as e:
            return {
                'error': f'Parse error: {str(e)}',
                'tracking_number': tracking_number
            }
    
    def get_statistics(self) -> Dict:
        """
        Restituisce statistiche sull'utilizzo del client
        
        Returns:
            Dict con statistiche
        """
        return {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'success_rate': f"{((self.request_count - self.error_count) / self.request_count * 100):.1f}%" if self.request_count > 0 else "N/A"
        }


if __name__ == "__main__":
    import sys
    from tracking_service import TrackingService
    from db_connector import cursor as db_cursor
    
    if len(sys.argv) > 1:
        # Test singolo tracking con AWB passato come parametro
        awb = sys.argv[1]
        client = UPSTrackingClient()
        result = client.track_shipment(awb, verbose=True)
        
        print("\n" + "="*60)
        print("RISULTATO")
        print("="*60)
        
        if 'error' in result:
            print(f"❌ Errore: {result['error']}")
        else:
            print(f"✓ Tracking completato")
            
        # Cerca nel database e aggiorna
        print("\nAggiornamento database...")
        with db_cursor() as (conn, cur):
            cur.execute("SELECT id FROM spedizioni WHERE awb = %s AND vettore = 'UPS'", [awb])
            row = cur.fetchone()
            if row:
                spedizione_id = row[0]
                service = TrackingService()
                update_result = service.update_tracking_ups(spedizione_id)
                if update_result.get("success"):
                    print(f"✓ Database aggiornato per spedizione ID {spedizione_id}")
                else:
                    print(f"⚠ Errore aggiornamento DB: {update_result.get('error')}")
            else:
                print(f"⚠ Nessuna spedizione UPS trovata con AWB {awb}")
                
    else:
        # Processa TUTTE le spedizioni UPS in transito (final_position = 0)
        print("\n" + "="*60)
        print("TRACKING AUTOMATICO SPEDIZIONI UPS IN TRANSITO")
        print("="*60 + "\n")
        
        from tracking_service import TrackingService
        service = TrackingService()
        
        with db_cursor() as (conn, cur):
            cur.execute("""
                SELECT id, awb 
                FROM spedizioni 
                WHERE vettore = 'UPS' 
                AND final_position = 0 
                AND awb IS NOT NULL 
                AND awb != ''
                ORDER BY data_spedizione DESC
            """)
            spedizioni = cur.fetchall()
            
            if not spedizioni:
                print("Nessuna spedizione UPS in transito trovata.\n")
            else:
                print(f"Trovate {len(spedizioni)} spedizioni UPS in transito.\n")
                
                for i, (spedizione_id, awb) in enumerate(spedizioni, 1):
                    print(f"[{i}/{len(spedizioni)}] Tracking AWB: {awb} (ID: {spedizione_id})")
                    
                    result = service.update_tracking_ups(spedizione_id)
                    
                    if result.get("success"):
                        print(f"  ✓ {result['last_position']}\n")
                    else:
                        print(f"  ✗ {result.get('error')}\n")
                    
                    # Delay tra richieste (tranne l'ultima)
                    if i < len(spedizioni):
                        import time
                        print(f"  Attesa 5s...\n")
                        time.sleep(5)
                
                print("="*60)
                print(f"Completato! Processate {len(spedizioni)} spedizioni UPS")
                print("="*60)
    print("DEBUG: Script ups_tracking.py avviato!")
    # Se viene passato un AWB, aggiorna anche il database
    import sys
    from tracking_service import TrackingService

    if len(sys.argv) > 1:
        awb = sys.argv[1]
        client = UPSTrackingClient()
        result = client.track_shipment(awb, verbose=True)

        print("\nAggiornamento database...")
        # Cerca la spedizione con quell'AWB
        from db_connector import cursor as db_cursor
        print(f"DEBUG: Cerco AWB {awb} nel database...")
        with db_cursor() as (conn, cur):
            cur.execute("SELECT id FROM spedizioni WHERE awb = %s", [awb])
            row = cur.fetchone()
            if row:
                spedizione_id = row[0]
            if len(sys.argv) > 1:
                awb = sys.argv[1]
                client = UPSTrackingClient()
                result = client.track_shipment(awb, verbose=True)

                print("\nAggiornamento database...")
                print(f"DEBUG: Cerco AWB {awb} nel database...")
                from db_connector import cursor as db_cursor
                with db_cursor() as (conn, cur):
                    cur.execute("SELECT id FROM spedizioni WHERE awb = %s", [awb])
                    row = cur.fetchone()
                    if row:
                        spedizione_id = row[0]
                        print(f"DEBUG: Trovato id={spedizione_id} per AWB={awb}")
                        service = TrackingService()
                        update_result = service.update_tracking(spedizione_id)
                        print(f"DEBUG: Risultato update_tracking: {update_result}")
                        if update_result.get("success"):
                            print(f"✓ Database aggiornato per spedizione ID {spedizione_id}")
                        else:
                            print(f"⚠ Errore aggiornamento DB: {update_result.get('error')}")
                    else:
                        print(f"⚠ Nessuna spedizione trovata con questo AWB ({awb}) nel database.")
            else:
                print("Nessun AWB passato: processiamo tutte le spedizioni UPS in transito (final_position=0)...")
                from db_connector import cursor as db_cursor
                from tracking_service import TrackingService
                client = UPSTrackingClient()
                with db_cursor() as (conn, cur):
                    cur.execute("SELECT id, awb FROM spedizioni WHERE vettore = 'UPS' AND final_position = 0 AND awb IS NOT NULL AND awb != ''")
                    rows = cur.fetchall()
                    print(f"DEBUG: Query trovate {len(rows)} spedizioni UPS in transito.")
                    if not rows:
                        print("DEBUG: Nessuna spedizione UPS in transito trovata nel database!")
                    else:
                        print("DEBUG: AWB trovati:")
                        for r in rows:
                            print(f"  - ID: {r[0]}, AWB: {r[1]}")
                    for row in rows:
                        spedizione_id, awb = row
                        print(f"\nDEBUG: Tracking AWB: {awb} (ID: {spedizione_id})")
                        result = client.track_shipment(awb, verbose=True)
                        service = TrackingService()
                        update_result = service.update_tracking(spedizione_id)
                        print(f"DEBUG: Risultato update_tracking: {update_result}")
                        if update_result.get("success"):
                            print(f"✓ Database aggiornato per spedizione ID {spedizione_id}")
                        else:
                            print(f"⚠ Errore aggiornamento DB: {update_result.get('error')}")