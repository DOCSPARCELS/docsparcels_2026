#!/usr/bin/env python3
"""
UPS Quote Interface N - Account A65c50

Interfaccia interattiva per preventivi UPS con account A65c50.
Supporta buste, multi-collo e calcolo IVA al 22%.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ups_quote_n import UPSQuoteClientN


def preventivo_singolo():
    """Ottieni un preventivo singolo (supporta multi-collo e buste) - Account A65c50"""
    print("\n💰 PREVENTIVO SPEDIZIONE UPS (Account A65c50)")
    print("=" * 50)
    
    # Raccolta dati origine
    print("\n📤 ORIGINE:")
    origin_country = input("Paese origine (es: IT): ").strip().upper()
    origin_postal = input("CAP origine: ").strip()
    
    # Raccolta dati destinazione
    print("\n📥 DESTINAZIONE:")
    dest_country = input("Paese destinazione (es: US): ").strip().upper()
    dest_postal = input("CAP destinazione: ").strip()
    
    if not all([origin_country, origin_postal, dest_country, dest_postal]):
        print("❌ Tutti i campi origine e destinazione sono obbligatori!")
        return
    
    # Tipo spedizione
    print("\n📋 TIPO SPEDIZIONE:")
    print("1. 📄 Busta/Documenti (dimensioni fisse)")
    print("2. 📦 Pacco generico (dimensioni personalizzate)")
    
    try:
        tipo_choice = input("Seleziona tipo [1]: ").strip() or "1"
        is_envelope = tipo_choice == "1"
    except:
        is_envelope = True
    
    # Raccolta numero colli
    print(f"\n📦 INFORMAZIONI {'BUSTE' if is_envelope else 'COLLI'}:")
    try:
        if is_envelope:
            num_packages = int(input("Numero di buste [1]: ").strip() or "1")
            if num_packages < 1 or num_packages > 10:
                print("❌ Numero buste deve essere tra 1 e 10!")
                return
        else:
            num_packages = int(input("Numero di colli [1]: ").strip() or "1")
            if num_packages < 1 or num_packages > 20:
                print("❌ Numero colli deve essere tra 1 e 20!")
                return
    except ValueError:
        print("❌ Numero non valido!")
        return
    
    packages = []
    total_weight = 0
    
    for i in range(num_packages):
        if is_envelope:
            print(f"\n📄 BUSTA {i+1}/{num_packages}:")
        else:
            print(f"\n📦 COLLO {i+1}/{num_packages}:")
        print("-" * 30)
        
        try:
            if is_envelope:
                weight_prompt = f"Peso busta {i+1} (kg) [0.1]: " if num_packages > 1 else "Peso busta (kg) [0.1]: "
                weight_kg = float(input(weight_prompt).strip() or "0.1")
                
                if weight_kg <= 0 or weight_kg > 2:
                    print(f"❌ Peso busta {i+1} deve essere tra 0.01 e 2 kg!")
                    return
                
                # Dimensioni fisse per buste
                length_cm, width_cm, height_cm = 35, 25, 2
                
                if num_packages > 1:
                    print(f"   ✅ Busta {i+1}: {weight_kg}kg (dimensioni standard: {length_cm}x{width_cm}x{height_cm}cm)")
                
            else:
                weight_prompt = f"Peso collo {i+1} (kg): " if num_packages > 1 else "Peso (kg): "
                weight_kg = float(input(weight_prompt).strip())
                
                if weight_kg <= 0 or weight_kg > 70:
                    print(f"❌ Peso collo {i+1} deve essere tra 0.1 e 70 kg!")
                    return
                    
                dim_prompt = f"Dimensioni collo {i+1} LxWxH cm [30x20x15]: " if num_packages > 1 else "Dimensioni LxWxH cm [30x20x15]: "
                dimensions = input(dim_prompt).strip() or "30x20x15"
                
                # Supporta sia 'x' che 'X' come separatore
                if 'x' in dimensions.lower():
                    if 'X' in dimensions:
                        # Sostituisce X maiuscola con x minuscola
                        dimensions = dimensions.replace('X', 'x')
                    length_cm, width_cm, height_cm = map(int, dimensions.split('x'))
                else:
                    length_cm = width_cm = height_cm = int(dimensions)
                    
                if any(d <= 0 or d > 200 for d in [length_cm, width_cm, height_cm]):
                    print(f"❌ Dimensioni collo {i+1} devono essere tra 1 e 200 cm!")
                    return
                
                if num_packages > 1:
                    print(f"   ✅ Collo {i+1}: {weight_kg}kg, {length_cm}x{width_cm}x{height_cm}cm")
                
        except ValueError:
            package_type = "busta" if is_envelope else "collo"
            print(f"❌ Valori non validi per {package_type} {i+1}!")
            return
        
        packages.append({
            'weight_kg': weight_kg,
            'length_cm': length_cm,
            'width_cm': width_cm,
            'height_cm': height_cm,
            'is_envelope': is_envelope
        })
        
        total_weight += weight_kg
    
    # Riepilogo
    package_type = "buste" if is_envelope else "colli"
    print(f"\n📋 RIEPILOGO SPEDIZIONE (Account A65c50):")
    print(f"   📍 Da: {origin_country} {origin_postal}")
    print(f"   📍 A:  {dest_country} {dest_postal}")
    print(f"   📦 {package_type.title()}: {num_packages}")
    print(f"   ⚖️  Peso totale: {total_weight:.2f} kg")
    if is_envelope:
        print(f"   📄 Tipo: Busta/Documenti (dimensioni standard)")
    print(f"   🏷️ Account: A65c50")
    print()
    
    print("⏳ Connessione a UPS (Account A65c50)...")
    client = UPSQuoteClientN()
    
    # Chiamata con supporto multi-collo
    if num_packages == 1:
        # Singolo pacco (compatibilità)
        result = client.get_quote(
            origin_country, origin_postal,
            dest_country, dest_postal,
            packages[0]['weight_kg'], 
            packages[0]['length_cm'], 
            packages[0]['width_cm'], 
            packages[0]['height_cm']
        )
    else:
        # Multi-collo
        result = client.get_quote(
            origin_country, origin_postal,
            dest_country, dest_postal,
            packages=packages
        )
    
    mostra_risultato_preventivo(result)


def preventivo_multi_destinazione():
    """Confronta prezzi per multiple destinazioni - Account A65c50"""
    print("\n📊 CONFRONTO MULTI-DESTINAZIONE (Account A65c50)")
    print("=" * 55)
    
    # Origine fissa
    print("\n📤 ORIGINE:")
    origin_country = input("Paese origine (es: IT): ").strip().upper()
    origin_postal = input("CAP origine: ").strip()
    
    # Dati pacco fissi
    print("\n📦 DATI PACCO:")
    try:
        weight_kg = float(input("Peso (kg): ").strip())
        length_cm = int(input("Lunghezza (cm, default 30): ").strip() or "30")
        width_cm = int(input("Larghezza (cm, default 20): ").strip() or "20")
        height_cm = int(input("Altezza (cm, default 15): ").strip() or "15")
    except ValueError:
        print("❌ Valori non validi!")
        return
    
    if not all([origin_country, origin_postal]) or weight_kg <= 0:
        print("❌ Tutti i campi sono obbligatori!")
        return
    
    # Raccolta destinazioni
    print("\n📥 DESTINAZIONI:")
    destinazioni = []
    
    while True:
        dest_country = input(f"Paese destinazione {len(destinazioni)+1} (invio per finire): ").strip().upper()
        if not dest_country:
            break
        dest_postal = input(f"CAP destinazione {len(destinazioni)+1}: ").strip()
        if dest_postal:
            destinazioni.append((dest_country, dest_postal))
    
    if not destinazioni:
        print("❌ Inserire almeno una destinazione!")
        return
    
    print(f"\n🔍 Calcolo {len(destinazioni)} preventivi (Account A65c50)...")
    client = UPSQuoteClientN()
    
    for i, (dest_country, dest_postal) in enumerate(destinazioni, 1):
        print(f"\n--- Destinazione {i}/{len(destinazioni)}: {dest_country} {dest_postal} ---")
        result = client.get_quote(
            origin_country, origin_postal,
            dest_country, dest_postal,
            weight_kg, length_cm, width_cm, height_cm
        )
        mostra_risultato_preventivo_breve(result, dest_country, dest_postal)


def preventivo_servizio_specifico():
    """Preventivo per un servizio specifico - Account A65c50"""
    print("\n📋 PREVENTIVO SERVIZIO SPECIFICO (Account A65c50)")
    print("=" * 60)
    
    # Mostra codici servizio comuni
    print("\nCodici servizio UPS comuni:")
    print("• 01 = UPS Next Day Air")
    print("• 02 = UPS 2nd Day Air")  
    print("• 03 = UPS Ground")
    print("• 07 = UPS Worldwide Express")
    print("• 08 = UPS Worldwide Expedited")
    print("• 11 = UPS Standard")
    print("• 12 = UPS 3 Day Select")
    print("• 13 = UPS Next Day Air Saver")
    print("• 14 = UPS Next Day Air Early A.M.")
    print("• 54 = UPS Worldwide Express Plus")
    print("• 59 = UPS 2nd Day Air A.M.")
    print("• 65 = UPS Express Saver")
    
    # Raccolta dati
    print("\n📤 ORIGINE:")
    origin_country = input("Paese origine (es: IT): ").strip().upper()
    origin_postal = input("CAP origine: ").strip()
    
    print("\n📥 DESTINAZIONE:")
    dest_country = input("Paese destinazione (es: US): ").strip().upper()
    dest_postal = input("CAP destinazione: ").strip()
    
    print("\n📋 SERVIZIO:")
    service_code = input("Codice servizio (es: 07): ").strip()
    
    print("\n📦 DATI PACCO:")
    try:
        weight_kg = float(input("Peso (kg): ").strip())
        length_cm = int(input("Lunghezza (cm, default 30): ").strip() or "30")
        width_cm = int(input("Larghezza (cm, default 20): ").strip() or "20")
        height_cm = int(input("Altezza (cm, default 15): ").strip() or "15")
    except ValueError:
        print("❌ Valori non validi!")
        return
    
    if not all([origin_country, origin_postal, dest_country, dest_postal, service_code]) or weight_kg <= 0:
        print("❌ Tutti i campi sono obbligatori!")
        return
    
    print(f"\n🔍 Calcolo preventivo per servizio {service_code} (Account A65c50)...")
    print(f"📍 {origin_country} {origin_postal} → {dest_country} {dest_postal}")
    print(f"📦 {weight_kg} kg ({length_cm}x{width_cm}x{height_cm} cm)")
    print("⏳ Connessione a UPS...")
    
    client = UPSQuoteClientN()
    result = client.get_detailed_quote(
        origin_country, origin_postal,
        dest_country, dest_postal,
        weight_kg, length_cm, width_cm, height_cm,
        service_code
    )
    
    mostra_risultato_preventivo(result)


def test_connessione():
    """Test di connessione UPS A65c50"""
    print("\n🧪 TEST CONNESSIONE UPS (Account A65c50)")
    print("=" * 45)
    
    print("⏳ Testando connessione UPS con account A65c50...")
    
    try:
        client = UPSQuoteClientN()
        # Test con dati fissi: Roma -> Milano, 1kg, 30x20x15cm
        result = client.get_quote("IT", "00100", "IT", "20100", 1.0, 30, 20, 15)
        
        if 'error' in result:
            print(f"❌ Errore di connessione: {result['error']}")
        else:
            print("✅ Connessione UPS riuscita!")
            rates = result.get('rates', [])
            print(f"📋 Servizi trovati: {len(rates)}")
            print(f"🏷️ Account utilizzato: {result.get('account', 'N/A')}")
            print(f"🔧 API utilizzata: {result.get('api_type', 'N/A')}")
            if rates:
                print(f"💰 Primo servizio: {rates[0].get('service_name', 'N/A')}")
                print(f"💵 Prezzo: {result.get('currency', 'EUR')} {rates[0].get('total_cost', 0):.2f}")
    except Exception as e:
        print(f"❌ Errore di test: {str(e)}")


def mostra_risultato_preventivo(result: dict):
    """Mostra risultato preventivo completo per account A65c50"""
    print("\n💰 RISULTATO PREVENTIVO UPS (Account A65c50):")
    print("=" * 50)
    
    if 'error' in result:
        print(f"❌ Errore: {result['error']}")
        return
    
    # Mostra informazioni account
    account = result.get('account', 'N/A')
    api_type = result.get('api_type', 'N/A')
    print(f"🏷️ Account UPS: {account}")
    print(f"🔧 API utilizzata: {api_type}")
    
    # Note specifiche
    if 'note' in result:
        print(f"ℹ️  {result['note']}")
    
    # Mostra informazioni multi-collo se disponibili
    if 'packages_info' in result:
        pkg_info = result['packages_info']
        if pkg_info.get('is_envelope', False):
            print(f"📄 Spedizione busta/documenti")
            print(f"⚖️  Peso: {pkg_info['total_weight_kg']:.2f} kg")
            if 'envelope_note' in result:
                print(f"ℹ️  {result['envelope_note']}")
            print()
        elif pkg_info['is_multi_package']:
            print(f"📦 Spedizione multi-collo: {pkg_info['num_packages']} colli")
            print(f"⚖️  Peso totale: {pkg_info['total_weight_kg']:.2f} kg")
            if 'multi_package_note' in result:
                print(f"ℹ️  {result['multi_package_note']}")
            print()
    
    rates = result.get('rates', [])
    currency = result.get('currency', 'EUR')
    
    if not rates:
        print("ℹ️  Nessun servizio disponibile per questa rotta")
        return
    
    print(f"💰 Valuta: {currency}")
    print(f"📋 Servizi disponibili: {len(rates)}")
    
    print(f"\n📊 TARIFFE UPS (Account A65c50):")
    print("-" * 50)
    
    for i, rate in enumerate(rates, 1):
        service_name = rate.get('service_name', 'N/A')
        service_code = rate.get('service_code', 'N/A')
        total_cost = rate.get('total_cost', 0)
        transport_cost = rate.get('transport_cost', 0)
        service_charges = rate.get('service_charges', 0)
        delivery_days = rate.get('delivery_days', 'N/A')
        billing_weight = rate.get('billing_weight', 'N/A')
        
        print(f"{i}. {service_name} (Codice: {service_code})")
        rate_type = rate.get('rate_type', 'N/A')
        print(f"   📋 Tipo tariffa: {rate_type}")
        
        # Mostra breakdown IVA solo se presente nella risposta UPS
        base_cost = rate.get('base_cost')
        iva_amount = rate.get('iva_amount')
        iva_rate = rate.get('iva_rate')
        
        if base_cost is not None and iva_amount is not None and iva_rate is not None:
            # IVA presente nella risposta UPS
            print(f"   💰 Costo base: {currency} {base_cost:.2f}")
            print(f"   🧾 IVA ({iva_rate}%): {currency} {iva_amount:.2f}")
            print(f"   💵 TOTALE: {currency} {total_cost:.2f}")
        else:
            # Solo totale (IVA non fornita da UPS o già inclusa)
            print(f"   💰 Costo totale: {currency} {total_cost:.2f}")
            print(f"   ℹ️  IVA non specificata da UPS (potrebbe essere inclusa)")
            
        if transport_cost > 0:
            print(f"   🚚 Trasporto: {currency} {transport_cost:.2f}")
        if service_charges > 0:
            print(f"   ⚙️  Servizi aggiuntivi: {currency} {service_charges:.2f}")
        print(f"   📅 Consegna: {delivery_days} giorni")
        if billing_weight != 'N/A':
            weight_unit = rate.get('weight_unit', 'KGS')
            print(f"   ⚖️  Peso fatturato: {billing_weight} {weight_unit}")
        print()


def mostra_risultato_preventivo_breve(result: dict, dest_country: str, dest_postal: str):
    """Mostra risultato preventivo in formato breve per confronti"""
    if 'error' in result:
        print(f"❌ {dest_country} {dest_postal}: {result['error']}")
        return
    
    rates = result.get('rates', [])
    currency = result.get('currency', 'EUR')
    
    if not rates:
        print(f"ℹ️  {dest_country} {dest_postal}: Nessun servizio disponibile")
        return
    
    # Mostra solo i primi 3 servizi più economici
    rates_sorted = sorted(rates, key=lambda x: x.get('total_cost', float('inf')))
    
    print(f"📍 {dest_country} {dest_postal} ({len(rates)} servizi) - Account A65c50:")
    for i, rate in enumerate(rates_sorted[:3], 1):
        service_name = rate.get('service_name', 'N/A')
        total_cost = rate.get('total_cost', 0)
        delivery_days = rate.get('delivery_days', 'N/A')
        print(f"   {i}. {service_name}: {currency} {total_cost:.2f} ({delivery_days} giorni)")


def mostra_menu():
    """Mostra menu principale"""
    print("\n🚚 UPS QUOTE CALCULATOR A65c50 (Buste + Multi-Collo)")
    print("═══════════════════════════════════════════════════")
    print("1. 💰 Preventivo spedizione (Buste/Multi-Collo)")
    print("2. 📊 Confronto multi-destinazione")
    print("3. 📋 Preventivo servizio specifico")
    print("4. 🧪 Test connessione UPS A65c50")
    print("0. ↩️  Torna al menu principale")
    print("═══════════════════════════════════════════════════")


def main():
    """Funzione principale"""
    print("� UPS QUOTE INTERFACE - Account A65c50")
    print("IVA condizionale da risposta UPS")
    print("=" * 50)
    
    try:
        preventivo_singolo()
    except KeyboardInterrupt:
        print("\n\n👋 Arrivederci!")
        return
    except Exception as e:
        print(f"❌ Errore: {str(e)}")


if __name__ == "__main__":
    main()