#!/usr/bin/env python3
"""
UPS Tracking Interface

Interfaccia interattiva per tracking spedizioni UPS.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ups_tracking import UPSTrackingClient


def mostra_menu():
    """Mostra il menu principale"""
    print("\n📦 UPS TRACKING INTERFACE")
    print("=" * 40)
    print("1. 📦 Traccia singola spedizione")
    print("2. 📦📦 Traccia spedizioni multiple")
    print("3. ℹ️  Test con numeri di esempio")
    print("4. 🚪 Esci")
    print("-" * 40)


def traccia_singola():
    """Traccia una singola spedizione"""
    print("\n📦 TRACKING SPEDIZIONE SINGOLA")
    print("=" * 35)
    
    tracking_number = input("Inserisci numero tracking UPS: ").strip()
    
    if not tracking_number:
        print("❌ Numero tracking obbligatorio!")
        return
    
    print(f"\n🔍 Tracking in corso per: {tracking_number}")
    print("⏳ Connessione a UPS...")
    
    client = UPSTrackingClient()
    result = client.track_shipment(tracking_number)
    
    mostra_risultato_tracking(result)


def traccia_multiple():
    """Traccia spedizioni multiple"""
    print("\n📦📦 TRACKING SPEDIZIONI MULTIPLE")
    print("=" * 40)
    
    print("Inserisci i numeri tracking (uno per riga, 'fine' per terminare):")
    tracking_numbers = []
    
    while True:
        tracking = input(f"#{len(tracking_numbers) + 1}: ").strip()
        
        if tracking.lower() == 'fine':
            break
        elif tracking:
            tracking_numbers.append(tracking)
        
        if len(tracking_numbers) >= 10:
            print("⚠️ Limite massimo 10 spedizioni per volta")
            break
    
    if not tracking_numbers:
        print("❌ Nessun numero tracking inserito!")
        return
    
    print(f"\n🔍 Tracking di {len(tracking_numbers)} spedizioni...")
    print("⏳ Connessione a UPS...")
    
    client = UPSTrackingClient()
    
    for i, tracking in enumerate(tracking_numbers, 1):
        print(f"\n--- Spedizione {i}/{len(tracking_numbers)} ---")
        result = client.track_shipment(tracking)
        mostra_risultato_tracking_breve(result)


def test_tracking_esempio():
    """Test con numeri di tracking di esempio"""
    print("\n🧪 TEST CON TRACKING DI ESEMPIO")
    print("=" * 40)
    
    tracking_esempi = [
        ("1Z12345E0193080450", "Numero test UPS (non valido)"),
        ("1Z12345E1234567890", "Numero fake per test formato"),
        ("1Z999AA1234567890", "Altro formato UPS test")
    ]
    
    print("Tracking di esempio disponibili:")
    for i, (tracking, desc) in enumerate(tracking_esempi, 1):
        print(f"{i}. {tracking} - {desc}")
    
    try:
        scelta = int(input("\nSeleziona tracking (1-3): ").strip())
        if 1 <= scelta <= len(tracking_esempi):
            tracking_number, descrizione = tracking_esempi[scelta - 1]
            
            print(f"\n🔍 Test con: {tracking_number}")
            print(f"📝 Descrizione: {descrizione}")
            print("⏳ Tracking in corso...")
            
            client = UPSTrackingClient()
            result = client.track_shipment(tracking_number)
            
            mostra_risultato_tracking(result)
        else:
            print("❌ Selezione non valida!")
    except ValueError:
        print("❌ Inserisci un numero valido!")


def mostra_risultato_tracking(result: dict):
    """Mostra risultato tracking completo"""
    print("\n📋 RISULTATO TRACKING UPS:")
    print("=" * 30)
    
    tracking = result.get('tracking_number', 'N/A')
    print(f"📦 Tracking: {tracking}")
    
    if 'error' in result:
        print(f"❌ Errore: {result['error']}")
        return
    
    # Status
    status = result.get('status_description', 'Sconosciuto')
    print(f"📊 Status: {status}")
    
    # Servizio
    service = result.get('service_type', 'N/A')
    print(f"🚚 Servizio: {service}")
    
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
            status_type = event.get('status_type', '')
            
            print(f"{i}. {date} {time}")
            print(f"   📍 {location}")
            print(f"   📝 {description}")
            if status_type:
                print(f"   📋 Tipo: {status_type}")
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
                    status_type = event.get('status_type', '')
                    
                    print(f"{i}. {date} {time}")
                    print(f"   📍 {location}")
                    print(f"   📝 {description}")
                    if status_type:
                        print(f"   📋 Tipo: {status_type}")
                    if event_code:
                        print(f"   🏷️  Codice: {event_code}")
                    print()
    else:
        print("ℹ️  Nessun evento di tracking disponibile")


def mostra_risultato_tracking_breve(result: dict):
    """Mostra risultato tracking in formato breve"""
    tracking = result.get('tracking_number', 'N/A')
    
    if 'error' in result:
        print(f"❌ {tracking}: {result['error']}")
    else:
        status = result.get('status_description', 'Sconosciuto')
        service = result.get('service_type', 'N/A')
        origin = result.get('origin', {}).get('description', 'N/A')
        destination = result.get('destination', {}).get('description', 'N/A')
        events_count = len(result.get('events', []))
        
        print(f"✅ {tracking}: {status}")
        print(f"   🚚 {service}")
        print(f"   📍 {origin} → {destination}")
        print(f"   📋 {events_count} eventi")


def main():
    """Funzione principale"""
    print("📦 UPS TRACKING INTERFACE")
    print("Inserisci il numero tracking UPS")
    print("=" * 40)
    
    try:
        traccia_singola()
    except KeyboardInterrupt:
        print("\n\n👋 Arrivederci!")
    except Exception as e:
        print(f"\n❌ Errore critico: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    print("📦 UPS TRACKING SYSTEM 2026")
    print("🔑 Ambiente: UPS XML API")
    main()