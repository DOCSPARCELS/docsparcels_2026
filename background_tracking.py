#!/usr/bin/env python3
"""
Background Tracking Service - Aggiornamento automatico di tutte le spedizioni

Servizio opzionale che gira in background e aggiorna tutti i tracking
delle spedizioni con vettore UPS/DHL e AWB validi.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any
from db_connector import cursor as db_cursor
from tracking_service import TrackingService

LOG = logging.getLogger(__name__)


class BackgroundTrackingService:
    """Servizio di background per aggiornamento tracking automatico"""
    
    def __init__(self, interval_minutes: int = 20):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.tracking_service = TrackingService()
        self.running = False
        self.thread = None
    
    def start(self):
        """Avvia il servizio di background"""
        if self.running:
            LOG.warning("Servizio già in esecuzione")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        LOG.info("🚀 Servizio tracking background avviato (ogni %d minuti)", self.interval_minutes)
    
    def stop(self):
        """Ferma il servizio di background"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        LOG.info("🛑 Servizio tracking background fermato")
    
    def _run_loop(self):
        """Loop principale del servizio"""
        while self.running:
            try:
                start_time = datetime.now()
                LOG.info("🔄 Avvio aggiornamento tracking automatico alle %s", start_time.strftime("%H:%M:%S"))
                
                # Aggiorna tutte le spedizioni attive
                updated_count = self._update_all_active_shipments()
                
                duration = (datetime.now() - start_time).total_seconds()
                LOG.info("✅ Aggiornamento completato: %d spedizioni in %.1fs", updated_count, duration)
                
                # Attendi il prossimo ciclo
                time.sleep(self.interval_seconds)
                
            except Exception as e:
                LOG.exception("❌ Errore nel loop tracking background")
                time.sleep(60)  # Attendi 1 minuto prima di riprovare
    
    def _update_all_active_shipments(self) -> int:
        """
        Aggiorna tutte le spedizioni con vettore supportato e AWB
        
        Returns:
            Numero di spedizioni aggiornate
        """
        try:
            # Trova spedizioni da aggiornare
            shipments = self._get_active_shipments()
            LOG.info("📦 Trovate %d spedizioni da aggiornare", len(shipments))
            
            updated_count = 0
            for shipment in shipments:
                try:
                    result = self.tracking_service.update_tracking(shipment['id'])
                    if result['success']:
                        updated_count += 1
                        LOG.debug("✅ Aggiornato ID %d: %s", shipment['id'], result['last_position'])
                    else:
                        LOG.debug("⚠️ Errore ID %d: %s", shipment['id'], result['error'])
                        
                except Exception as e:
                    LOG.warning("❌ Errore aggiornamento spedizione ID %d: %s", shipment['id'], str(e))
                
                # Pausa breve tra le chiamate per non sovraccaricare le API
                time.sleep(1)
            
            return updated_count
            
        except Exception as e:
            LOG.exception("Errore aggiornamento spedizioni")
            return 0
    
    def _get_active_shipments(self) -> List[Dict[str, Any]]:
        """
        Ottiene lista spedizioni attive da aggiornare
        
        Criteri:
        - Vettore UPS, DHL, SDA o BRT
        - AWB non vuoto
        - Non consegnate (final_position != 1)
        - Aggiornate nelle ultime 2 settimane
        """
        try:
            with db_cursor() as (conn, cur):
                query = """
                SELECT id, vettore, awb, last_position
                FROM spedizioni 
                WHERE 
                    vettore IN ('UPS', 'DHL', 'SDA', 'BRT')
                    AND awb IS NOT NULL 
                    AND awb != ''
                    AND (final_position IS NULL OR final_position != 1)
                    AND data_spedizione >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                ORDER BY data_spedizione DESC
                LIMIT 100
                """
                
                cur.execute(query)
                rows = cur.fetchall()
                
                shipments = []
                for row in rows:
                    shipments.append({
                        'id': row[0],
                        'vettore': row[1],
                        'awb': row[2],
                        'last_position': row[3]
                    })
                
                return shipments
                
        except Exception as e:
            LOG.exception("Errore query spedizioni attive")
            return []


def main():
    """Avvia il servizio di background"""
    import signal
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('tracking_background.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Crea e avvia il servizio
    service = BackgroundTrackingService(interval_minutes=30)
    
    def signal_handler(sig, frame):
        LOG.info("Ricevuto segnale di stop")
        service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        service.start()
        LOG.info("✅ Servizio tracking background attivo. Premi Ctrl+C per fermare.")
        
        # Mantieni il processo attivo
        while service.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        LOG.info("Fermato da utente")
    finally:
        service.stop()


if __name__ == "__main__":
    main()