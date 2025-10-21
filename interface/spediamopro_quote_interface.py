#!/usr/bin/env python3
"""
Spediamo Pro Quote Interface

Interfaccia interattiva per preventivi Spediamo Pro con tutti i corrieri.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spediamopro_quote import SpediamoproQuoteClient
import re


def _is_ups_envelope(weight: float, length: float, width: float, height: float) -> bool:
    """
    Determina se un pacco dovrebbe essere trattato come UPS Envelope
    
    Criteri UPS Envelope:
    - Peso ≤ 1.5 kg
    - Spessore (altezza) ≤ 5 cm
    - Dimensioni planari adatte a documenti/lettere
    - Generalmente per documenti o oggetti piatti
    """
    # Trova la dimensione più piccola (dovrebbe essere lo spessore)
    dims = sorted([length, width, height])
    thickness = dims[0]  # La dimensione più piccola
    
    # Criteri envelope UPS
    envelope_criteria = (
        weight <= 1.5 and          # Peso massimo 1.5kg
        thickness <= 5 and         # Spessore massimo 5cm
        dims[1] >= 15 and          # Almeno 15cm una dimensione
        dims[2] >= 20              # Almeno 20cm l'altra dimensione
    )
    
    return envelope_criteria


def validate_postal_code(postal_code: str, country: str) -> bool:
    """Valida formato CAP per paese"""
    postal_code = postal_code.strip()
    
    if country.upper() == "IT":
        return bool(re.match(r'^\d{5}$', postal_code))
    elif country.upper() == "DE":
        return bool(re.match(r'^\d{5}$', postal_code))
    elif country.upper() == "FR":
        return bool(re.match(r'^\d{5}$', postal_code))
    elif country.upper() == "ES":
        return bool(re.match(r'^\d{5}$', postal_code))
    else:
        return len(postal_code) >= 3  # Validazione generica


def get_origin_info():
    """Raccoglie informazioni di partenza"""
    print("\n📤 INFORMAZIONI PARTENZA:")
    print("-" * 40)
    
    origin_country = input("Paese di partenza (IT): ").strip().upper() or "IT"
    origin_city = input("Città di partenza: ").strip()
    if not origin_city:
        raise ValueError("Città di partenza obbligatoria")
    
    origin_postal = input("CAP partenza: ").strip()
    if not validate_postal_code(origin_postal, origin_country):
        raise ValueError(f"CAP non valido per {origin_country}")
    
    return {
        'country': origin_country,
        'city': origin_city,
        'postal': origin_postal
    }


def get_destination_info():
    """Raccoglie informazioni di destinazione"""
    print("\n📥 INFORMAZIONI DESTINAZIONE:")
    print("-" * 40)
    
    dest_country = input("Paese di destinazione (IT): ").strip().upper() or "IT"
    dest_city = input("Città di destinazione: ").strip()
    if not dest_city:
        raise ValueError("Città di destinazione obbligatoria")
    
    dest_postal = input("CAP destinazione: ").strip()
    if not validate_postal_code(dest_postal, dest_country):
        raise ValueError(f"CAP non valido per {dest_country}")
    
    return {
        'country': dest_country,
        'city': dest_city,
        'postal': dest_postal
    }


def get_package_info():
    """Raccoglie informazioni dei colli (supporta multi-collo)"""
    print("\n📦 INFORMAZIONI COLLI:")
    print("-" * 40)
    
    # Numero di colli
    num_packages = input("Numero di colli [1]: ").strip() or "1"
    try:
        num_packages = int(num_packages)
        if num_packages <= 0 or num_packages > 20:
            raise ValueError("Numero colli deve essere tra 1 e 20")
    except ValueError:
        raise ValueError("Numero colli non valido")
    
    packages = []
    total_weight = 0
    total_value = 0
    
    for i in range(num_packages):
        print(f"\n📦 COLLO {i+1}/{num_packages}:")
        print("-" * 30)
        
        # Tipo spedizione per il collo
        package_type_prompt = f"Tipo collo {i+1} - [E]nvelope / [G]enerico [G]: " if num_packages > 1 else "Tipo spedizione - [E]nvelope / [G]enerico [G]: "
        package_type = input(package_type_prompt).strip().lower()
        is_envelope = package_type in ['e', 'envelope', 'env']
        
        if is_envelope:
            print(f"   📧 UPS ENVELOPE selezionato - nessuna dimensione richiesta")
            # Per envelope non serve specificare dimensioni
            length = width = height = None
        else:
            print(f"   📦 Pacco generico selezionato")
        
        # Peso del collo
        if is_envelope:
            weight_prompt = f"Peso collo {i+1} (kg) [0.5]: " if num_packages > 1 else "Peso (kg) [0.5]: "
            weight = input(weight_prompt).strip() or "0.5"
        else:
            weight_prompt = f"Peso collo {i+1} (kg) [1.0]: " if num_packages > 1 else "Peso (kg) [1.0]: "
            weight = input(weight_prompt).strip() or "1.0"
            
        try:
            weight = float(weight)
            if weight <= 0 or weight > 1000:
                raise ValueError("Peso deve essere tra 0.1 e 1000 kg")
            
            # Controllo peso per envelope
            if is_envelope and weight > 1.5:
                print(f"   ⚠️  Avviso: Peso {weight}kg superiore al limite envelope UPS (1.5kg)")
                
        except ValueError:
            raise ValueError(f"Peso collo {i+1} non valido")
        
        # Dimensioni del collo (solo per pacchi generici)
        if not is_envelope:
            dim_prompt = f"Dimensioni collo {i+1} LxWxH cm [30x20x15]: " if num_packages > 1 else "Dimensioni LxWxH cm [30x20x15]: "
            dimensions = input(dim_prompt).strip() or "30x20x15"
            try:
                if 'x' in dimensions:
                    length, width, height = map(float, dimensions.split('x'))
                else:
                    length = width = height = float(dimensions)
                
                if any(d <= 0 or d > 200 for d in [length, width, height]):
                    raise ValueError("Dimensioni devono essere tra 1 e 200 cm")
            except ValueError:
                raise ValueError(f"Dimensioni collo {i+1} non valide (formato: 30x20x15)")
        
        # Valore del collo
        if is_envelope:
            # Per envelope, assicurazione sempre 0
            value = 0.0
            value_message = f"Valore collo {i+1}: EUR 0 (envelope - no assicurazione)" if num_packages > 1 else "Valore assicurato: EUR 0 (envelope - no assicurazione)"
            print(value_message)
        else:
            value_prompt = f"Valore collo {i+1} EUR [0]: " if num_packages > 1 else "Valore EUR [0]: "
            value = input(value_prompt).strip() or "0"
            try:
                value = float(value)
                if value < 0:
                    raise ValueError("Valore non può essere negativo")
            except ValueError:
                raise ValueError(f"Valore collo {i+1} non valido")
        
        packages.append({
            'weight': weight,
            'length': length,
            'width': width,
            'height': height,
            'value': value,
            'is_envelope': is_envelope
        })
        
        total_weight += weight
        total_value += value
        
        if num_packages > 1:
            if is_envelope:
                print(f"   ✅ Collo {i+1}: {weight}kg [ENVELOPE], EUR {value}")
            else:
                print(f"   ✅ Collo {i+1}: {weight}kg, {length}x{width}x{height}cm, EUR {value}")
        elif is_envelope:
            print(f"   📧 UPS ENVELOPE: {weight}kg, EUR {value}")
    
    # Tipo spedizione (automatico per envelope, manuale per pacchi)
    has_envelope = any(pkg.get('is_envelope', False) for pkg in packages)
    
    if has_envelope:
        # Se c'è almeno un envelope, è automaticamente documenti
        is_documents = True
        print(f"\n📄 Tipo contenuto: DOCUMENTI (automatico per envelope)")
    else:
        # Solo per pacchi normali chiede il tipo
        is_documents = input("\nDocumenti? (s/N): ").strip().lower() in ['s', 'si', 'y', 'yes']
    
    if num_packages > 1:
        print(f"\n📊 RIEPILOGO SPEDIZIONE:")
        print(f"   📦 Totale colli: {num_packages}")
        print(f"   ⚖️  Peso totale: {total_weight:.1f} kg")
        print(f"   💰 Valore totale: EUR {total_value:.2f}")
    
    return {
        'packages': packages,
        'num_packages': num_packages,
        'total_weight': total_weight,
        'total_value': total_value,
        'is_documents': is_documents
    }


def display_results(result: dict, origin: dict, destination: dict, package_info: dict):
    """Mostra risultati in formato leggibile"""
    print("\n" + "=" * 80)
    print("📋 RISULTATI SIMULAZIONE SPEDIAMO PRO")
    print("=" * 80)
    
    print(f"📤 Da: {origin['city']} ({origin['postal']}) - {origin['country']}")
    print(f"📥 A:  {destination['city']} ({destination['postal']}) - {destination['country']}")
    
    # Mostra informazioni multi-collo
    if package_info['num_packages'] == 1:
        pkg = package_info['packages'][0]
        if pkg.get('is_envelope', False):
            print(f"📧 Envelope UPS: {pkg['weight']} kg | EUR {pkg['value']}")
        else:
            print(f"📦 Pacco: {pkg['weight']} kg | {pkg['length']}x{pkg['width']}x{pkg['height']} cm | EUR {pkg['value']}")
    else:
        envelopes_count = sum(1 for pkg in package_info['packages'] if pkg.get('is_envelope', False))
        envelope_info = f" ({envelopes_count} envelope)" if envelopes_count > 0 else ""
        print(f"📦 Spedizione: {package_info['num_packages']} colli{envelope_info} | {package_info['total_weight']:.1f} kg totali | EUR {package_info['total_value']:.2f}")
        for i, pkg in enumerate(package_info['packages'], 1):
            if pkg.get('is_envelope', False):
                print(f"   📧 Collo {i}: {pkg['weight']} kg [ENVELOPE] | EUR {pkg['value']}")
            else:
                print(f"   📦 Collo {i}: {pkg['weight']} kg | {pkg['length']}x{pkg['width']}x{pkg['height']} cm | EUR {pkg['value']}")
    
    print(f"📄 Tipo: {'Documenti' if package_info['is_documents'] else 'Merce'}")
    
    if 'error' in result:
        print(f"\n❌ ERRORE: {result['error']}")
        print("\n💡 Suggerimenti:")
        print("   • Verifica le credenziali nel file .env")
        print("   • Controlla che i CAP siano corretti")
        print("   • Verifica la connessione internet")
        return
    
    rates = result.get('rates', [])
    if not rates:
        print("\n❌ Nessuna tariffa disponibile per questa rotta")
        return
    
    print(f"\n💰 Valuta: {result.get('currency', 'EUR')}")
    print(f"🎯 Opzioni trovate: {len(rates)}")
    
    print("\n🚚 TARIFFE DISPONIBILI:")
    print("-" * 80)
    print(f"{'#':<3} {'CORRIERE':<8} {'SERVIZIO':<35} {'PREZZO':<12} {'GIORNI':<8}")
    print("-" * 80)
    
    for i, rate in enumerate(rates[:15], 1):  # Top 15
        carrier = rate.get('carrier', 'N/A')
        service = rate.get('service_name', 'N/A')
        cost = rate.get('total_cost', 0)
        # Prova sia delivery_days che delivery_time per compatibilità
        days = rate.get('delivery_days') or rate.get('delivery_time', 'N/A')
        
        # Tronca il nome del servizio se troppo lungo
        if len(service) > 33:
            service = service[:30] + "..."
        
        print(f"{i:<3} {carrier:<8} {service:<35} EUR {cost:>7.2f} {str(days):<8}")
    
    # Mostra breakdown del migliore
    if rates:
        best_rate = rates[0]
        details = best_rate.get('details', {})
        
        print(f"\n💡 MIGLIORE OPZIONE - {best_rate.get('carrier')} {best_rate.get('service_name')}:")
        print("-" * 50)
        if details.get('prezzo_base'):
            print(f"   📊 Prezzo base:     EUR {details['prezzo_base']:.2f}")
        if details.get('carburante'):
            print(f"   ⛽ Carburante:      EUR {details['carburante']:.2f}")
        if details.get('iva'):
            print(f"   🏛️  IVA:             EUR {details['iva']:.2f}")
        if details.get('altri_costi'):
            print(f"   💳 Altri costi:     EUR {details['altri_costi']:.2f}")
        print(f"   💰 TOTALE:          EUR {best_rate['total_cost']:.2f}")
        print(f"   🆔 ID Simulazione:  {best_rate.get('simulation_id', 'N/A')}")


def main():
    """Interfaccia principale"""
    print("🚚 SPEDIAMO PRO - PREVENTIVI MULTI-CORRIERE")
    print("=" * 60)
    print("Supporta: SDA, BRT, UPS, InPost")
    print("Tariffe: Express, Standard, Fermopoint, Point-to-Point")
    print("Multi-collo: Fino a 20 colli per spedizione")
    print("📧 UPS Envelope: Selezione manuale con dimensioni automatiche")
    
    try:
        # Raccoglie informazioni
        origin = get_origin_info()
        destination = get_destination_info()
        package_info = get_package_info()
        
        print("\n🔄 Elaborazione simulazione...")
        print("⏳ Contattando Spediamo Pro...")
        
        # Esegue simulazione con i nuovi parametri multi-collo
        client = SpediamoproQuoteClient()
        result = client.get_simulation(
            origin_country=origin['country'],
            origin_postal=origin['postal'],
            origin_city=origin['city'],
            destination_country=destination['country'],
            destination_postal=destination['postal'],
            destination_city=destination['city'],
            packages=package_info['packages'],  # Lista di colli
            value_eur=package_info['total_value'],  # Valore totale
            is_documents=package_info['is_documents']
        )
        
        # Mostra risultati
        display_results(result, origin, destination, package_info)
        
    except KeyboardInterrupt:
        print("\n\n👋 Operazione annullata dall'utente")
    except ValueError as e:
        print(f"\n❌ Errore input: {e}")
    except Exception as e:
        print(f"\n💥 Errore inaspettato: {e}")
        print("🔧 Controlla la configurazione nel file .env")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()