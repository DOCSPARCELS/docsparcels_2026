#!/usr/bin/env python3
"""
TNT Tracking Interface
Interfaccia interattiva per test tracking spedizioni TNT Express

Aggiornato: 13 ottobre 2025
"""

import sys
import os

# Aggiungi il path parent per import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tnt_tracking import TNTTrackingClient

def display_header():
    """Mostra header dell'interfaccia TNT"""
    print("\n" + "=" * 60)
    print("🚚 TNT EXPRESS TRACKING INTERFACE")
    print("Sistema tracking unificato per spedizioni TNT")
    print("=" * 60)

def display_tracking_result(result):
    """Mostra risultato tracking in formato user-friendly"""
    
    if result['status'] == 'success':
        # Controlla se è simulazione
        if result.get('simulation'):
            print(f"\n🧪 SIMULAZIONE TNT (API non disponibile)")
            print(f"⚠️ NOTA: Dati simulati per test - non reali")
            print("-" * 50)
            
        print(f"\n✅ SPEDIZIONE TNT TROVATA")
        print(f"📦 AWB: {result['awb']}")
        print(f"🚚 Servizio: {result['service']}")
        print(f"📍 Origine: {result['origin']}")
        print(f"🎯 Destinazione: {result['destination']}")
        print(f"📊 Status: {result['current_status']}")
        print(f"📍 Località: {result['current_location']}")
        print(f"⏰ Aggiornamento: {result['last_update']}")
        print(f"🔗 URL: {result['tracking_url']}")
        
        if result.get('simulation'):
            print(f"\n⚠️ MODALITÀ SIMULAZIONE ATTIVA")
            print(f"Per produzione servono:")
            print(f"   - Credenziali TNT valide") 
            print(f"   - Endpoint API corretto")
            print(f"   - Possibile certificato SSL")
        
        # Eventi di tracking
        events = result.get('events', [])
        if events:
            print(f"\n📋 TIMELINE SPEDIZIONE ({len(events)} eventi):")
            print("-" * 50)
            
            for i, event in enumerate(events, 1):
                # Icona per tipo evento
                icon = "🚚"
                desc_lower = event['description'].lower()
                if 'delivered' in desc_lower or 'consegnato' in desc_lower:
                    icon = "✅"
                elif 'out for delivery' in desc_lower or 'consegna' in desc_lower:
                    icon = "🚛"
                elif 'transit' in desc_lower or 'transito' in desc_lower:
                    icon = "🚚"
                elif 'exception' in desc_lower or 'problem' in desc_lower:
                    icon = "⚠️"
                
                print(f"{i:2d}. {icon} {event['date']} {event['time']}")
                print(f"    {event['description']}")
                if event['location']:
                    print(f"    📍 {event['location']}")
                if event.get('code'):
                    print(f"    🏷️ Codice: {event['code']}")
                print()
        else:
            print("\n📋 Nessun evento di tracking disponibile")
            
    elif result['status'] == 'not_found':
        print(f"\n❌ SPEDIZIONE NON TROVATA")
        print(f"📦 AWB: {result['awb']}")
        print(f"💡 Il numero inserito potrebbe essere:")
        print(f"   - Non valido o inesistente")
        print(f"   - Non ancora nel sistema TNT")
        print(f"   - Appartenente ad un altro vettore")
        
    elif result['status'] == 'error':
        print(f"\n🚨 ERRORE TNT API")
        print(f"📦 AWB: {result['awb']}")
        print(f"💥 Errore: {result['message']}")
        print(f"💡 Possibili cause:")
        print(f"   - Problemi di connessione")
        print(f"   - Servizio TNT temporaneamente non disponibile")
        print(f"   - Credenziali API non valide")
        
    else:
        print(f"\n⚠️ STATUS SCONOSCIUTO")
        print(f"📦 AWB: {result['awb']}")
        print(f"📊 Status: {result['status']}")
        print(f"💬 Messaggio: {result.get('message', 'Nessun messaggio')}")

def get_awb_input():
    """Input del numero AWB con validazione"""
    while True:
        print(f"\n📦 INSERISCI NUMERO AWB TNT:")
        awb = input("AWB TNT (o 'exit' per uscire): ").strip()
        
        if awb.lower() == 'exit':
            return None
            
        if not awb:
            print("⚠️ Inserisci un numero AWB valido")
            continue
            
        # Validazione base formato AWB TNT
        if len(awb) < 8:
            print("⚠️ Il numero AWB TNT deve essere di almeno 8 caratteri")
            continue
            
        return awb.upper()

def main():
    """Funzione principale dell'interfaccia"""
    display_header()
    
    # Inizializza client TNT
    try:
        client = TNTTrackingClient()
        print("✅ Client TNT inizializzato correttamente")
    except Exception as e:
        print(f"❌ Errore inizializzazione client TNT: {str(e)}")
        return
    
    # Menu principale
    while True:
        print(f"\n" + "=" * 50)
        print("🎯 OPZIONI DISPONIBILI:")
        print("1. 🔍 Tracking singolo AWB")
        print("2. 🧪 Test con AWB esempio (WS82879660)")
        print("3. ❌ Esci")
        
        choice = input("\nScegli opzione [1-3]: ").strip()
        
        if choice == '1':
            # Tracking singolo
            awb = get_awb_input()
            if awb is None:
                break
                
            print(f"\n🔍 Tracking TNT AWB: {awb}")
            print("⏳ Connessione al sistema TNT...")
            
            result = client.track_shipment(awb)
            display_tracking_result(result)
            
        elif choice == '2':
            # Test con AWB esempio
            test_awb = "WS82879660"
            print(f"\n🧪 Test con AWB esempio: {test_awb}")
            print("⏳ Connessione al sistema TNT...")
            
            result = client.track_shipment(test_awb)
            display_tracking_result(result)
            
        elif choice == '3':
            print("\n👋 Uscita da TNT Tracking Interface")
            break
            
        else:
            print("\n⚠️ Opzione non valida. Riprova.")
            
        # Pausa prima del prossimo comando
        input("\n📱 Premi INVIO per continuare...")

if __name__ == "__main__":
    main()