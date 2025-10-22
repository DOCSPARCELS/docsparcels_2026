#!/usr/bin/env python3
"""
Tracking Service - Aggiornamento automatico last_position e final_position

Integra UPS, DHL, SDA, BRT, FedEx e TNT tracking con la tabella spedizioni.
NON salva messaggi di errore in last_position - solo status validi.
Aggiorna automaticamente final_position quando la spedizione è consegnata.
"""

import logging
from typing import Optional, Dict, Any
from db_connector import cursor as db_cursor
from ups_tracking import UPSTrackingClient
from dhl_tracking import DHLTrackingClient
from interface.sda_tracking_interface import SDATrackingInterface
from interface.brt_tracking_interface import BRTTrackingInterface
from fedex_tracking import FedExTracking
from tnt_tracking import TNTTrackingClient

LOG = logging.getLogger(__name__)


class TrackingService:
    """Servizio per aggiornamento tracking spedizioni"""
    
    def __init__(self):
        self.ups_client = UPSTrackingClient()
        self.dhl_client = DHLTrackingClient()
        self.sda_client = SDATrackingInterface(environment='prod')
        self.brt_client = BRTTrackingInterface()
        self.fedex_client = FedExTracking()
        self.tnt_client = TNTTrackingClient()
    
def update_tracking(self, spedizione_id: int) -> Dict[str, Any]:
    """
    Router che chiama il metodo specifico per ogni vettore
    
    Args:
        spedizione_id: ID della spedizione
        
    Returns:
        Dict con risultato operazione
    """
    try:
        # Leggi vettore
        spedizione_data = self._get_spedizione_data(spedizione_id)
        if not spedizione_data:
            return {"success": False, "error": "Spedizione non trovata"}
        
        vettore = spedizione_data.get('vettore', '').upper()
        
        # Router: chiama metodo specifico per vettore
        if vettore == "UPS":
            return self.update_tracking_ups(spedizione_id)
        elif vettore == "DHL":
            return self.update_tracking_dhl(spedizione_id)
        elif vettore == "SDA":
            return self.update_tracking_sda(spedizione_id)
        elif vettore == "BRT":
            return self.update_tracking_brt(spedizione_id)
        elif vettore in ["FEDEX", "FED"]:
            return self.update_tracking_fedex(spedizione_id)
        elif vettore == "TNT":
            return self.update_tracking_tnt(spedizione_id)
        else:
            return {"success": False, "error": f"Vettore {vettore} non supportato"}
            
    except Exception as e:
        LOG.exception("Errore routing tracking spedizione %s", spedizione_id)
        return {"success": False, "error": f"Errore interno: {str(e)}"}

    def _update_tracking_data(self, spedizione_id: int, last_position: str, events: list) -> bool:
        """Aggiorna last_position e final_position nel database"""
        try:
            if not last_position:
                LOG.warning(f"Nessuno status valido per spedizione {spedizione_id}")
                return False
            
            vettore = self._get_vettore_for_spedizione(spedizione_id)
            final_position = self._determine_final_position(last_position, vettore)
            
            with db_cursor() as (conn, cur):
                cur.execute(
                    """UPDATE spedizioni 
                    SET last_position = %s, final_position = %s 
                    WHERE id = %s""",
                    [last_position, final_position, spedizione_id]
                )
                conn.commit()
                
                if cur.rowcount > 0:
                    LOG.info(f"✅ Aggiornato tracking spedizione {spedizione_id}: '{last_position}' (final={final_position})")
                    return True
                else:
                    LOG.warning(f"⚠️ Nessuna riga aggiornata per spedizione {spedizione_id}")
                    return False
                    
        except Exception as e:
            LOG.exception("Errore aggiornamento tracking per spedizione %s", spedizione_id)
            return False
    
    def update_tracking_ups(self, spedizione_id: int) -> Dict[str, Any]:
        """Aggiorna tracking specifico per UPS - dati grezzi"""
        try:
            spedizione_data = self._get_spedizione_data(spedizione_id)
            if not spedizione_data:
                return {"success": False, "error": "Spedizione non trovata"}
            
            awb = spedizione_data.get('awb', '')
            if not awb:
                return {"success": False, "error": "AWB mancante"}
            
            # Tracking UPS
            result = self.ups_client.track_shipment(awb, verbose=False)
            if result.get('error'):
                return {"success": False, "error": result['error'], "vettore": "UPS", "awb": awb}
            
            # Estrai dati grezzi
            tracking_data = self._extract_ups_status(result)
            description, date_str, time_str = tracking_data
            
            if not description:
                return {"success": False, "error": "Nessuno status ricevuto"}
            
            # Aggiorna database - SOLO DATI GREZZI
            with db_cursor() as (conn, cur):
                if date_str and time_str:
                    from datetime import datetime
                    dt_obj = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                    cur.execute(
                        """UPDATE spedizioni 
                        SET last_position = %s, last_position_update = %s 
                        WHERE id = %s""",
                        [description, dt_obj, spedizione_id]
                    )
                else:
                    cur.execute(
                        """UPDATE spedizioni 
                        SET last_position = %s 
                        WHERE id = %s""",
                        [description, spedizione_id]
                    )
                conn.commit()
                
                if cur.rowcount > 0:
                    LOG.info(f"✅ Tracking UPS {spedizione_id} aggiornato: {description}")
                    return {"success": True, "last_position": description, "vettore": "UPS", "awb": awb}
                else:
                    return {"success": False, "error": "Errore aggiornamento database"}
                    
        except Exception as e:
            LOG.exception("Errore tracking UPS spedizione %s", spedizione_id)
            return {"success": False, "error": str(e)}

    def _get_spedizione_data(self, spedizione_id: int) -> Optional[Dict[str, Any]]:
        """Legge vettore e AWB dal database"""
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    "SELECT vettore, awb FROM spedizioni WHERE id = %s",
                    [spedizione_id]
                )
                row = cur.fetchone()
                if row:
                    return {"vettore": row[0], "awb": row[1]}
                return None
        except Exception as e:
            LOG.exception("Errore lettura spedizione %s", spedizione_id)
            return None
    
    def _get_tracking_data(self, vettore: str, awb: str) -> Dict[str, Any]:
        """
        Ottiene i dati completi di tracking dal vettore appropriato
        
        Args:
            vettore: UPS, DHL, SDA, BRT, FedEx o TNT
            awb: Numero tracking
            
        Returns:
            Dict con status (solo se valido), events, error (se presente)
        """
        try:
            if vettore == "UPS":
                result = self.ups_client.track_shipment(awb)
                if result.get('error'):
                    LOG.warning(f"Errore tracking UPS {awb}: {result['error']}")
                    return {'tracking_data': (None, None, None), 'events': [], 'error': result['error']}
                
                tracking_data = self._extract_ups_status(result)
                return {
                    'success': True,
                    'tracking_data': tracking_data,
                    'events': result.get('events', []),
                    'raw_result': result
                }
            
            elif vettore == "DHL":
                result = self.dhl_client.track_shipment(awb)
                if result.get('error'):
                    LOG.warning(f"Errore tracking DHL {awb}: {result['error']}")
                    return {'status': None, 'events': [], 'error': result['error']}
                status = self._extract_dhl_status(result)
                return {
                    'success': True,
                    'status': status,
                    'events': result.get('events', []),
                    'raw_result': result
                }
            
            elif vettore == "SDA":
                result = self.sda_client.track(awb)
                if not result.get('success'):
                    LOG.warning(f"Errore tracking SDA {awb}: {result.get('message', 'Errore sconosciuto')}")
                    return {'status': None, 'events': [], 'error': result.get('message', 'Errore tracking SDA')}
                status = self._extract_sda_status(result)
                return {
                    'success': True,
                    'status': status,
                    'events': result.get('events', []),
                    'raw_result': result
                }
            
            elif vettore == "BRT":
                result = self.brt_client.track(awb)
                if not result.get('success'):
                    LOG.warning(f"Errore tracking BRT {awb}: {result.get('message', 'Errore sconosciuto')}")
                    return {'status': None, 'events': [], 'error': result.get('message', 'Errore tracking BRT')}
                status = self._extract_brt_status(result)
                return {
                    'success': True,
                    'status': status,
                    'events': result.get('events', []),
                    'raw_result': result
                }
            
            elif vettore in ["FEDEX", "FED"]:
                result = self.fedex_client.track_shipment(awb)
                if not result.get('success'):
                    error_msg = result.get('error', 'Errore FedEx sconosciuto')
                    LOG.warning(f"Errore tracking FedEx {awb}: {error_msg}")
                    return {'status': None, 'events': [], 'error': error_msg}
                
                events = result.get('events', [])
                status = self._extract_fedex_status(events)
                return {
                    'success': True,
                    'status': status,
                    'events': events,
                    'raw_result': result
                }
            
            elif vettore == "TNT":
                result = self.tnt_client.track_shipment(awb)
                if result.get('status') != 'success':
                    error_msg = result.get('message', 'Errore TNT sconosciuto')
                    LOG.warning(f"Errore tracking TNT {awb}: {error_msg}")
                    return {'status': None, 'events': [], 'error': error_msg}
                
                events = result.get('events', [])
                status = self._extract_tnt_status(result)
                return {
                    'success': True,
                    'status': status,
                    'events': events,
                    'raw_result': result
                }
            
            else:
                return {
                    'success': False,
                    'status': None,
                    'events': [],
                    'error': f"Vettore {vettore} non supportato"
                }
                
        except Exception as e:
            LOG.exception("Errore tracking %s %s", vettore, awb)
            return {
                'success': False,
                'status': None,
                'events': [],
                'error': f"Errore interno: {str(e)}"
            }
    
    def _extract_ups_status(self, ups_result: Dict[str, Any]) -> tuple:
        """Estrae description, date e time da risultato UPS per aggiornamento DB
        
        Returns:
            tuple: (description, date, time) oppure (None, None, None) se errore
        """
        try:
            if ups_result.get('error'):
                return (None, None, None)
            
            events = ups_result.get('events', [])
            if events:
                latest_event = events[0]  # Primo evento = più recente
                
                # Estrai description
                description = latest_event.get('description', latest_event.get('status_type', ''))
                
                # Estrai date e time
                date = latest_event.get('date', '')
                time = latest_event.get('time', '')
                
                if description and date and time:
                    return (description, date, time)
            
            # Fallback se non ci sono eventi
            status = ups_result.get('status_description', ups_result.get('status', ''))
            return (status, None, None) if status else (None, None, None)
            
        except Exception as e:
            LOG.exception("Errore parsing UPS")
            return (None, None, None)
    
    def _extract_dhl_status(self, dhl_result: Dict[str, Any]) -> str:
        """Estrae il messaggio di status da risultato DHL"""
        try:
            if dhl_result.get('error'):
                return None
            
            events = dhl_result.get('events', [])
            if events:
                latest_event = events[-1]
                status = latest_event.get('description', '')
                if status:
                    return status
            
            status = dhl_result.get('status_description', dhl_result.get('status', ''))
            return status if status else None
            
        except Exception as e:
            LOG.exception("Errore parsing DHL")
            return None
    
    def _extract_sda_status(self, sda_result: Dict[str, Any]) -> str:
        """Estrae il messaggio di status da risultato SDA"""
        try:
            if not sda_result.get('success'):
                return None
            
            status = sda_result.get('last_position', '')
            return status if status and not status.startswith('Errore') else None
            
        except Exception as e:
            LOG.exception("Errore parsing SDA")
            return None
    
    def _extract_brt_status(self, brt_result: Dict[str, Any]) -> str:
        """Estrae il messaggio di status da risultato BRT"""
        try:
            if not brt_result.get('success'):
                return None
            
            status = brt_result.get('last_position', '')
            return status if status and not status.startswith('Errore') else None
            
        except Exception as e:
            LOG.exception("Errore parsing BRT")
            return None
    
    def _extract_fedex_status(self, fedex_events: list) -> str:
        """Estrae il codice evento FedEx"""
        try:
            if not fedex_events or len(fedex_events) == 0:
                return None
            
            latest_event = fedex_events[0]
            codice = latest_event.get('codice', '')
            if codice:
                return codice
            
            descrizione = latest_event.get('descrizione', '')
            if descrizione:
                return descrizione
                
            return None
            
        except Exception as e:
            LOG.exception("Errore parsing FedEx")
            return None
    
    def _extract_tnt_status(self, tnt_result: Dict[str, Any]) -> str:
        """Estrae il codice/status TNT"""
        try:
            current_status = tnt_result.get('current_status', '')
            if current_status:
                return current_status
            
            events = tnt_result.get('events', [])
            if events and len(events) > 0:
                latest_event = events[0]
                description = latest_event.get('description', '')
                if description:
                    return description
            
            return None
            
        except Exception as e:
            LOG.exception("Errore parsing TNT")
            return None
 
    def _get_vettore_for_spedizione(self, spedizione_id: int) -> Optional[str]:
        """Ottiene il vettore per una spedizione specifica"""
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    "SELECT vettore FROM spedizioni WHERE id = %s",
                    [spedizione_id]
                )
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            LOG.exception("Errore lettura vettore per spedizione %s", spedizione_id)
            return None

    def test_tracking_service():
        """Test del servizio tracking"""
        service = TrackingService()
        
        # Test con ID di esempio
        result = service.update_tracking(1)
        print("Risultato test tracking:")
        print(result)


if __name__ == "__main__":
    # Avvia test
    test_tracking_service()