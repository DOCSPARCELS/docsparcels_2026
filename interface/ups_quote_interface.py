#!/usr/bin/env python3
"""
UPS Quote Interface - Account X8899X

Interfaccia interattiva per preventivi UPS con account X8899X.
IVA 22% automatica su tutte le tariffe.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ups_quote import UPSQuoteClient


def preventivo_singolo():
    """Ottieni un preventivo singolo (supporta multi-collo e buste) - Account X8899X"""
    print("\n💰 PREVENTIVO SPEDIZIONE UPS (Account X8899X)")
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
                
                # Supporta sia "x" che "X"
                if 'x' in dimensions.lower():
                    separator = 'x' if 'x' in dimensions else 'X'
                    length_cm, width_cm, height_cm = map(int, dimensions.split(separator))
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
    print(f"\n📋 RIEPILOGO SPEDIZIONE:")
    print(f"   📍 Da: {origin_country} {origin_postal}")
    print(f"   📍 A:  {dest_country} {dest_postal}")
    print(f"   📦 {package_type.title()}: {num_packages}")
    print(f"   ⚖️  Peso totale: {total_weight:.2f} kg")
    if is_envelope:
        print(f"   📄 Tipo: Busta/Documenti (dimensioni standard)")
    print()
    
    print("⏳ Connessione a UPS...")
    client = UPSQuoteClient()
    
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


def mostra_risultato_preventivo(result):
    """Mostra i risultati del preventivo in formato leggibile"""
    if 'error' in result:
        print(f"❌ Errore: {result['error']}")
        if 'details' in result:
            print(f"💡 Dettagli: {result['details']}")
            if 'multi_package_note' in result:
                print(f"ℹ️  {result['multi_package_note']}")
        print()
        return
    
    # Messaggio se è simulazione
    if result.get('is_simulation', False):
        print("🔄 MODALITÀ SIMULAZIONE")
        if result.get('api_error'):
            print(f"⚠️  Errore API: {result['api_error']}")
            if 'multi_package_note' in result:
                print(f"ℹ️  {result['multi_package_note']}")
            print()
    
    rates = result.get('rates', [])
    currency = result.get('currency', 'USD')
    
    if not rates:
        print("ℹ️  Nessun servizio disponibile per questa rotta")
        return
    
    print(f"💰 Valuta: {currency}")
    print(f"📋 Servizi disponibili: {len(rates)}")
    
    print(f"\n📊 TARIFFE UPS:")
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
        
        # Mostra breakdown IVA
        if 'iva_details' in rate:
            iva_info = rate['iva_details']
            subtotal = iva_info.get('subtotal', 0)
            iva_amount = iva_info.get('iva_amount', 0)
            print(f"   💰 Subtotale: {currency} {subtotal:.2f}")
            print(f"   📊 IVA (22%): {currency} {iva_amount:.2f}")
            print(f"   💯 TOTALE: {currency} {total_cost:.2f}")
        else:
            print(f"   💯 Costo totale: {currency} {total_cost:.2f}")
        
        print(f"   🚚 Trasporto: {currency} {transport_cost:.2f}")
        if service_charges > 0:
            print(f"   📋 Servizi aggiuntivi: {currency} {service_charges:.2f}")
        print(f"   📅 Tempi di consegna: {delivery_days}")
        
        if billing_weight != 'N/A':
            print(f"   ⚖️  Peso tariffabile: {billing_weight} kg")
        
        print()


def main():
    """Funzione principale"""
    print("🚀 UPS QUOTE INTERFACE - Account X8899X")
    print("IVA 22% automatica su tutte le tariffe")
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