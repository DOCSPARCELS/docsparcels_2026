#!/usr/bin/env python3
"""
DHL Tracking Interface

Interfaccia interattiva per tracking spedizioni DHL.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dhl_tracking import DHLTrackingClient


def mostra_menu():
    """Mostra il menu principale"""
    print("\n🔍 DHL TRACKING INTERFACE")
    print("=" * 40)
    print("1. 📦 Traccia singola spedizione")
    print("2. 📦📦 Traccia spedizioni multiple")
    print("3. ℹ️  Test con AWB di esempio")
    print("4. 🚪 Esci")
    print("-" * 40)


def traccia_singola():
    """Traccia una singola spedizione"""
    print("\n📦 TRACKING SPEDIZIONE SINGOLA")
    print("=" * 35)
    
    awb_number = input("Inserisci numero AWB: ").strip()
    
    if not awb_number:
        print("❌ Numero AWB obbligatorio!")
        return
    
    print(f"\n🔍 Tracking in corso per AWB: {awb_number}")
    print("⏳ Connessione a DHL...")
    
    client = DHLTrackingClient()
    result = client.track_shipment(awb_number)
    
    mostra_risultato_tracking(result)


def traccia_multiple():
    """Traccia spedizioni multiple"""
    print("\n📦📦 TRACKING SPEDIZIONI MULTIPLE")
    print("=" * 40)
    
    print("Inserisci i numeri AWB (uno per riga, 'fine' per terminare):")
    awb_numbers = []
    
    while True:
        awb = input(f"AWB #{len(awb_numbers) + 1}: ").strip()
        
        if awb.lower() == 'fine':
            break
        elif awb:
            awb_numbers.append(awb)
        
        if len(awb_numbers) >= 5:
            print("⚠️  Massimo 5 AWB per volta")
            break
    
    if not awb_numbers:
        print("❌ Nessun AWB inserito!")
        return
    
    print(f"\n🔍 Tracking di {len(awb_numbers)} spedizioni...")
    
    client = DHLTrackingClient()
    
    for i, awb in enumerate(awb_numbers, 1):
        print(f"\n--- Spedizione {i}/{len(awb_numbers)}: {awb} ---")
        result = client.track_shipment(awb)
        mostra_risultato_tracking_breve(result)


def test_awb_esempio():
    """Test con AWB di esempio"""
    print("\n🧪 TEST CON AWB DI ESEMPIO")
    print("=" * 35)
    
    awb_esempi = [
        ("7343641620", "AWB reale (Roma → Bari)"),
        ("1234567890", "AWB fake per test errore"),
        ("0000000000", "AWB nullo per test")
    ]
    
    print("AWB di esempio disponibili:")
    for i, (awb, desc) in enumerate(awb_esempi, 1):
        print(f"{i}. {awb} - {desc}")
    
    try:
        scelta = int(input("\nSeleziona AWB (1-3): ").strip())
        if 1 <= scelta <= len(awb_esempi):
            awb_number, descrizione = awb_esempi[scelta - 1]
            
            print(f"\n🔍 Test con: {awb_number}")
            print(f"📝 Descrizione: {descrizione}")
            print("⏳ Tracking in corso...")
            
            client = DHLTrackingClient()
            result = client.track_shipment(awb_number)
            
            mostra_risultato_tracking(result)
        else:
            print("❌ Selezione non valida!")
    except ValueError:
        print("❌ Inserisci un numero valido!")


def mostra_risultato_tracking(result: dict):
    """Mostra risultato tracking completo"""
    print("\n📋 RISULTATO TRACKING:")
    print("=" * 25)
    
    awb = result.get('tracking_number', 'N/A')
    print(f"📦 AWB: {awb}")
    
    if 'error' in result:
        print(f"❌ Errore: {result['error']}")
        return
    
    # Status
    status = result.get('status_description', 'Sconosciuto')
    print(f"📊 Status: {status}")
    
    # Origine e destinazione
    origin = result.get('origin', {}).get('description', 'N/A')
    destination = result.get('destination', {}).get('description', 'N/A')
    
    print(f"📤 Origine: {origin}")
    print(f"📥 Destinazione: {destination}")
    
    # Eventi
    events = result.get('events', [])
    print(f"📋 Eventi di tracking: {len(events)}")
    
    if events:
        print("\n📅 CRONOLOGIA EVENTI:")
        print("-" * 30)
        
        # Mostra primi 5 eventi
        for i, event in enumerate(events[:5], 1):
            date = event.get('date', 'N/A')
            time = event.get('time', '')
            location = event.get('location', 'N/A')
            description = event.get('description', 'N/A')
            event_code = event.get('event_code', '')
            
            print(f"{i}. {date} {time}")
            print(f"   📍 {location}")
            print(f"   📝 {description}")
            if event_code:
                print(f"   🏷️  Codice: {event_code}")
            print()
        
        if len(events) > 5:
            print(f"... e altri {len(events) - 5} eventi")
            risposta = input("Vuoi vedere tutti gli eventi? (s/N): ").strip().lower()
            if risposta in ['s', 'si', 'sì', 'y', 'yes']:
                print("\n📅 TUTTI GLI EVENTI:")
                print("-" * 25)
                for i, event in enumerate(events, 1):
                    date = event.get('date', 'N/A')
                    time = event.get('time', '')
                    location = event.get('location', 'N/A')
                    description = event.get('description', 'N/A')
                    event_code = event.get('event_code', '')
                    
                    print(f"{i}. {date} {time}")
                    print(f"   📍 {location}")
                    print(f"   📝 {description}")
                    if event_code:
                        print(f"   🏷️  Codice: {event_code}")
                    print()
    else:
        print("ℹ️  Nessun evento di tracking disponibile")


def mostra_risultato_tracking_breve(result: dict):
    """Mostra risultato tracking in formato breve"""
    awb = result.get('tracking_number', 'N/A')
    
    if 'error' in result:
        print(f"❌ {awb}: {result['error']}")
    else:
        status = result.get('status_description', 'Sconosciuto')
        origin = result.get('origin', {}).get('description', 'N/A')
        destination = result.get('destination', {}).get('description', 'N/A')
        events_count = len(result.get('events', []))
        
        print(f"✅ {awb}: {status}")
        print(f"   📍 {origin} → {destination}")
        print(f"   📋 {events_count} eventi")


def main():
    """Funzione principale"""
    print("🔍 DHL TRACKING INTERFACE")
    print("Inserisci il numero AWB per il tracking")
    print("=" * 40)
    
    try:
        traccia_singola()
    except KeyboardInterrupt:
        print("\n\n👋 Arrivederci!")
    except Exception as e:
        print(f"\n❌ Errore critico: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚚 DHL TRACKING SYSTEM 2026")
    print("🔑 Ambiente: Produzione DHL XML API")
    main()