#!/usr/bin/env python3
"""
DHL Quote Universal Interface

Interactive interface for worldwide DHL quote requests with document/merchandise support.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dhl_quote import DHLQuoteClient, ShipmentQuoteRequest
from datetime import datetime

def get_origin_info():
    """Get origin shipping information"""
    print("\n📤 INFORMAZIONI PARTENZA:")
    print("-" * 30)
    
    origin_city = input("Città di partenza [Roma]: ").strip() or "Roma"
    origin_postal_code = input("CAP partenza [00118]: ").strip() or "00118"
    origin_country = input("Paese partenza [IT]: ").strip().upper() or "IT"
    
    print(f"   ✅ Partenza: {origin_city}, {origin_postal_code} ({origin_country})")
    
    return origin_city, origin_postal_code, origin_country

def get_destination_info():
    """Get destination shipping information"""
    print("\n📥 INFORMAZIONI DESTINAZIONE:")
    print("-" * 35)
    
    dest_city = input("Città di destinazione [Milano]: ").strip() or "Milano"
    dest_postal_code = input("CAP destinazione [20121]: ").strip() or "20121"
    dest_country = input("Paese destinazione [IT]: ").strip().upper() or "IT"
    
    print(f"   ✅ Destinazione: {dest_city}, {dest_postal_code} ({dest_country})")
    
    return dest_city, dest_postal_code, dest_country

def get_package_info():
    """Get package dimensions and weight"""
    print("\n📦 INFORMAZIONI COLLI:")
    print("-" * 25)
    
    # Content type selection
    print("\n🔍 TIPO DI CONTENUTO:")
    print("1. 📄 Documenti")
    print("2. 📦 Merce")
    
    while True:
        content_choice = input("Seleziona tipo [1]: ").strip() or "1"
        if content_choice == "1":
            content_type = "Documenti"
            is_dutiable = False
            break
        elif content_choice == "2":
            content_type = "Merce"
            is_dutiable = True
            break
        else:
            print("⚠️  Seleziona 1 per Documenti o 2 per Merce")
    
    # Number of pieces with better visibility
    print(f"\n📦 NUMERO COLLI:")
    while True:
        try:
            pieces = int(input("Numero di colli [1]: ").strip() or "1")
            if pieces > 0:
                print(f"   ✅ Colli: {pieces}")
                break
            else:
                print("❌ Il numero di colli deve essere maggiore di 0")
        except ValueError:
            print("❌ Inserisci un numero valido")
    
    # Package dimensions
    print(f"\n📏 DIMENSIONI E PESO:")
    try:
        weight = float(input("Peso totale (kg) [1.0]: ").strip() or "1.0")
        length = float(input("Lunghezza (cm) [30]: ").strip() or "30")
        width = float(input("Larghezza (cm) [20]: ").strip() or "20")
        height = float(input("Altezza (cm) [15]: ").strip() or "15")
        
        print(f"   ✅ Peso: {weight} kg")
        print(f"   ✅ Dimensioni: {length}x{width}x{height} cm")
        print(f"   ✅ Contenuto: {content_type}")
        
    except ValueError:
        raise ValueError("Dimensioni devono essere numeriche")
    
    return weight, length, width, height, content_type, is_dutiable, pieces

def main():
    """Main interactive quote interface"""
    print("🚚 DHL PREVENTIVO UNIVERSALE")
    print("=" * 40)
    
    try:
        # Initialize client
        client = DHLQuoteClient()
        
        # Get shipping information
        origin_city, origin_postal_code, origin_country = get_origin_info()
        dest_city, dest_postal_code, dest_country = get_destination_info()
        weight, length, width, height, content_type, is_dutiable, pieces = get_package_info()
        
        # Create quote request
        quote_request = ShipmentQuoteRequest(
            origin_country=origin_country,
            origin_postal_code=origin_postal_code,
            origin_city=origin_city,
            destination_country=dest_country,
            destination_postal_code=dest_postal_code,
            destination_city=dest_city,
            weight_kg=weight,
            length_cm=length,
            width_cm=width,
            height_cm=height,
            is_dutiable=is_dutiable,
            pieces=pieces
        )
        
        # Get shipping date (format: YYYY-MM-DD for DHL)
        date_input = input("Data spedizione (YYYY-MM-DD, lascia vuoto per domani): ").strip()
        if date_input:
            try:
                # Parse user input and validate
                datetime.strptime(date_input, "%Y-%m-%d")
                quote_request.shipment_date = date_input
            except ValueError:
                print("⚠️  Formato data non valido. Uso data di domani.")
        
        # Summary
        print("\n📋 RIEPILOGO PREVENTIVO:")
        print("=" * 30)
        print(f"📤 Da: {origin_city}, {origin_postal_code} ({origin_country})")
        print(f"📥 A: {dest_city}, {dest_postal_code} ({dest_country})")
        print(f"📦 Contenuto: {content_type}")
        print(f"📊 Colli: {pieces}")
        print(f"⚖️  Peso: {weight} kg")
        print(f"📐 Dimensioni: {length}x{width}x{height} cm")
        print(f"📅 Data: {quote_request.shipment_date}")
        
        # Confirm
        confirm = input("\n✅ Procedo con il preventivo? (s/n): ").strip().lower()
        if confirm not in ['s', 'si', 'y', 'yes']:
            print("❌ Preventivo annullato.")
            return
        
        # Get quote
        print("\n🔍 Richiesta preventivo DHL in corso...")
        services = client.get_quote(quote_request)
        
        if services:
            print(f"\n✅ Trovati {len(services)} servizi disponibili:")
            print("=" * 60)
            
            for i, service in enumerate(services, 1):
                print(f"\n{i}. {service['service_name']}")
                print(f"   💰 Prezzo: €{service['price']}")
                print(f"   ⏰ Tempo di consegna: {service['delivery_time']}")
                if service.get('delivery_date'):
                    print(f"   📅 Data consegna: {service['delivery_date']}")
        else:
            print("❌ Nessun servizio disponibile per questa destinazione.")
            
    except KeyboardInterrupt:
        print("\n\n👋 Arrivederci!")
    except Exception as e:
        print(f"\n❌ Errore: {str(e)}")
        print("Riprova con dati corretti.")

if __name__ == "__main__":
    main()