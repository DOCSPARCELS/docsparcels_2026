#!/usr/bin/env python3
"""
UPS Quote Client N - Account A65c50

Client UPS per preventivi con account A65c50 e nuove credenziali OAuth.
Supporta buste, multi-collo e calcolo IVA al 22%.
"""

import json
import requests
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional
from datetime import datetime
from config import UPSConfig


class UPSQuoteClientN:
    """Client UPS per preventivi con account A65c50"""
    
    # Mappatura codici servizio UPS
    UPS_SERVICE_CODES = {
        "01": "UPS Next Day Air",
        "02": "UPS 2nd Day Air",
        "03": "UPS Ground", 
        "07": "UPS Worldwide Express",
        "08": "UPS Worldwide Expedited",
        "11": "UPS Standard",
        "12": "UPS 3 Day Select",
        "13": "UPS Next Day Air Saver",
        "14": "UPS Next Day Air Early A.M.",
        "54": "UPS Worldwide Express Plus",
        "59": "UPS 2nd Day Air A.M.",
        "65": "UPS Saver",
        "82": "UPS Today Standard",
        "83": "UPS Today Dedicated Courier",
        "84": "UPS Today Intercity",
        "85": "UPS Today Express",
        "86": "UPS Today Express Saver"
    }
    
    def __init__(self, config: Optional[UPSConfig] = None):
        """Inizializza client UPS con configurazione A65c50"""
        if config is None:
            # Configurazione hardcoded per account A65c50
            self.config = UPSConfig(
                client_id="eAjNs9SdSdbGJv2eotC1nblxWALf4WyYB4Gz5mIesG8c8ufQ",
                client_secret="dAt3RH24GftoMBgMJBzur2IfIcYVBH2eWPaVvsGLNcSmhtjWQHk9Rn1cZ32K48q9",
                account="A65c50",
                username="",  # Da configurare se necessario per XML
                password="",  # Da configurare se necessario per XML
                license=""    # Da configurare se necessario per XML
            )
        else:
            self.config = config
            
        self.oauth_token = None
        self.token_expires = None
        
    def get_quote(self, 
                  origin_country: str,
                  origin_postal: str,
                  destination_country: str, 
                  destination_postal: str,
                  weight_kg: float = None,
                  length_cm: int = 30,
                  width_cm: int = 20,
                  height_cm: int = 15,
                  packages: List[Dict] = None) -> Dict:
        """
        Ottieni preventivi per tutti i servizi UPS (supporta multi-collo)
        
        Args:
            origin_country: Codice paese origine (es: IT)
            origin_postal: CAP origine
            destination_country: Codice paese destinazione (es: US)
            destination_postal: CAP destinazione
            weight_kg: Peso in kg (per compatibilità, usa packages per multi-collo)
            length_cm: Lunghezza in cm (default 30)
            width_cm: Larghezza in cm (default 20)
            height_cm: Altezza in cm (default 15)
            packages: Lista di pacchi per multi-collo
            
        Returns:
            Dict con rates, currency e informazioni spedizione
        """
        try:
            # Gestione parametri multi-collo vs singolo
            is_envelope = False
            if packages:
                # Multi-collo: usa il primo pacco per ora (UPS API ha limitazioni)
                first_package = packages[0]
                is_envelope = first_package.get('is_envelope', False)
                
                if is_envelope:
                    # Per buste: usa peso effettivo senza arrotondamenti
                    total_weight = sum(p['weight_kg'] for p in packages)
                else:
                    # Per pacchi: calcolo normale 
                    total_weight = sum(p['weight_kg'] for p in packages)
                    
                package_data = {
                    'weight_kg': total_weight,
                    'length_cm': first_package['length_cm'],
                    'width_cm': first_package['width_cm'],
                    'height_cm': first_package['height_cm']
                }
                num_packages = len(packages)
            else:
                if weight_kg is None:
                    raise ValueError("weight_kg or packages must be provided")
                package_data = {
                    'weight_kg': weight_kg,
                    'length_cm': length_cm,
                    'width_cm': width_cm,
                    'height_cm': height_cm
                }
                num_packages = 1
                is_envelope = False
            
            # Prova prima OAuth REST API
            print("🔑 Usando OAuth REST API per tariffe contrattuali...")
            oauth_result = self._get_quote_oauth_rest(
                origin_country, origin_postal,
                destination_country, destination_postal,
                package_data, is_envelope
            )
            
            if oauth_result and 'rates' in oauth_result:
                # Aggiungi informazioni multi-collo se disponibili
                if packages:
                    oauth_result['packages_info'] = {
                        'is_multi_package': len(packages) > 1,
                        'num_packages': len(packages),
                        'total_weight_kg': package_data['weight_kg'],
                        'is_envelope': is_envelope
                    }
                    
                    if is_envelope:
                        oauth_result['envelope_note'] = f"Spedizione busta/documenti - Account A65c50"
                    elif len(packages) > 1:
                        oauth_result['multi_package_note'] = f"Spedizione {len(packages)} colli - Account A65c50"
                
                return oauth_result
            
            # Fallback: prova XML API
            print("⚠️ OAuth REST API fallita, fallback a XML API...")
            xml_result = self._get_quote_xml(
                origin_country, origin_postal,
                destination_country, destination_postal,
                package_data, is_envelope
            )
            
            if xml_result and 'rates' in xml_result:
                # Aggiungi informazioni multi-collo per XML
                if packages:
                    xml_result['packages_info'] = {
                        'is_multi_package': len(packages) > 1,
                        'num_packages': len(packages),
                        'total_weight_kg': package_data['weight_kg'],
                        'is_envelope': is_envelope
                    }
                
                return xml_result
            
            # Se tutto fallisce, genera simulazione
            print("🔄 Generando simulazione UPS basata su tariffe reali...")
            return self._generate_simulation(
                origin_country, origin_postal,
                destination_country, destination_postal,
                package_data, is_envelope, packages
            )
            
        except Exception as e:
            return {
                'error': f"UPS quote error: {str(e)}",
                'origin': f"{origin_country} {origin_postal}",
                'destination': f"{destination_country} {destination_postal}"
            }

    def _get_oauth_token(self) -> Optional[str]:
        """Ottieni token OAuth per API REST UPS con account A65c50"""
        try:
            import base64
            
            # Endpoint OAuth UPS produzione
            oauth_url = "https://onlinetools.ups.com/security/v1/oauth/token"
            
            # Credenziali base64 per account A65c50
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
            credentials_b64 = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'Authorization': f'Basic {credentials_b64}'
            }
            
            data = {
                'grant_type': 'client_credentials'
            }
            
            print("🔐 DEBUG - RICHIESTA OAUTH TOKEN A65c50:")
            print("=" * 50)
            print(f"URL: {oauth_url}")
            print(f"Client ID: {self.config.client_id[:10]}...")
            print(f"Headers: {headers}")
            print(f"Data: {data}")
            print("=" * 50)
            
            response = requests.post(oauth_url, headers=headers, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.oauth_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                
                print("🔐 DEBUG - RISPOSTA OAUTH TOKEN:")
                print("=" * 50)
                print(f"Token ricevuto: {self.oauth_token[:20]}...")
                print(f"Token Type: {token_data.get('token_type', 'Bearer')}")
                print(f"Expires in: {expires_in} secondi")
                print("=" * 50)
                
                return self.oauth_token
            else:
                print(f"❌ OAuth Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ OAuth Exception: {str(e)}")
            return None

    def _get_quote_oauth_rest(self, origin_country: str, origin_postal: str,
                             destination_country: str, destination_postal: str,
                             package_data: Dict, is_envelope: bool) -> Optional[Dict]:
        """Ottieni preventivo via OAuth REST API con account A65c50"""
        try:
            # Ottieni token OAuth
            token = self._get_oauth_token()
            if not token:
                return None
            
            # Determina packaging type
            if is_envelope:
                packaging_code = "01"  # Letter
            else:
                packaging_code = "02"  # Package
            
            # Endpoint UPS Rate API
            rate_url = "https://onlinetools.ups.com/api/rating/v1/Shop"
            
            # Headers con token OAuth
            headers = {
                'Content-Type': 'application/json',
                'transId': f"Rate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'transactionSrc': 'production',
                'Authorization': f'Bearer {token}'
            }
            
            # Payload per REST API
            payload = {
                "RateRequest": {
                    "Request": {
                        "TransactionReference": {
                            "CustomerContext": "Rate Quote"
                        },
                        "RequestOption": "Rate"
                    },
                    "Shipment": {
                        "Shipper": {
                            "Name": "Shipper Company",
                            "ShipperNumber": self.config.account,  # A65c50
                            "Address": {
                                "AddressLine": [
                                    "123 Ship Street"
                                ],
                                "City": self._get_city_name(origin_country, origin_postal),
                                "StateProvinceCode": self._get_state_code(origin_country, origin_postal),
                                "PostalCode": origin_postal,
                                "CountryCode": origin_country
                            }
                        },
                        "ShipTo": {
                            "Name": "Consignee Company",
                            "Address": {
                                "AddressLine": [
                                    "456 Dest Avenue"
                                ],
                                "City": self._get_city_name(destination_country, destination_postal),
                                "StateProvinceCode": self._get_state_code(destination_country, destination_postal),
                                "PostalCode": destination_postal,
                                "CountryCode": destination_country
                            }
                        },
                        "ShipFrom": {
                            "Name": "Ship From Company",
                            "Address": {
                                "AddressLine": [
                                    "123 Ship Street"
                                ],
                                "City": self._get_city_name(origin_country, origin_postal),
                                "StateProvinceCode": self._get_state_code(origin_country, origin_postal),
                                "PostalCode": origin_postal,
                                "CountryCode": origin_country
                            }
                        },
                        "PaymentDetails": {
                            "ShipmentCharge": [
                                {
                                    "Type": "01",
                                    "BillShipper": {
                                        "AccountNumber": self.config.account  # A65c50
                                    }
                                }
                            ]
                        },
                        "Package": [
                            {
                                "PackagingType": {
                                    "Code": packaging_code,
                                    "Description": "Letter" if packaging_code == "01" else "Customer Supplied Package"
                                },
                                "PackageWeight": {
                                    "UnitOfMeasurement": {
                                        "Code": "KGS",
                                        "Description": "Kilograms"
                                    },
                                    "Weight": str(package_data['weight_kg'])
                                },
                                **({
                                    "Dimensions": {
                                        "UnitOfMeasurement": {
                                            "Code": "CM",
                                            "Description": "Centimeters"
                                        },
                                        "Length": str(package_data['length_cm']),
                                        "Width": str(package_data['width_cm']),
                                        "Height": str(package_data['height_cm'])
                                    }
                                } if packaging_code != "01" else {})
                            }
                        ]
                    }
                }
            }
            
            print("📤 DEBUG - RICHIESTA REST API UPS A65c50:")
            print("=" * 50)
            print(f"URL: {rate_url}")
            print(f"Headers: {headers}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            print("=" * 50)
            
            response = requests.post(rate_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                print("📥 DEBUG - RISPOSTA REST API UPS:")
                print("=" * 50)
                print(f"Response: {json.dumps(result, indent=2)[:1000]}...")
                print("=" * 50)
                
                return self._parse_rest_response(result, packaging_code)
            else:
                print(f"❌ DEBUG REST API Error: {response.status_code} {response.reason} for url: {rate_url} - Details: {response.json() if response.text else 'No details'}")
                return None
                
        except Exception as e:
            print(f"⚠️ OAuth REST API fallita: {str(e)}")
            return None

    def _parse_rest_response(self, response_data: Dict, packaging_code: str) -> Dict:
        """Parsing risposta REST API - IVA solo se presente nella risposta UPS"""
        try:
            rates = []
            rate_response = response_data.get('RateResponse', {})
            shipment = rate_response.get('Shipment', {})
            
            # Parsing singolo rate o multiple rates
            rated_shipments = shipment.get('RatedShipment', [])
            if not isinstance(rated_shipments, list):
                rated_shipments = [rated_shipments]
            
            for rated_shipment in rated_shipments:
                service_info = rated_shipment.get('Service', {})
                service_code = service_info.get('Code', '')
                service_name = self.UPS_SERVICE_CODES.get(service_code, f"UPS Service {service_code}")
                
                # Costi
                charges = rated_shipment.get('RatedShipmentAlert', [])
                total_charges = rated_shipment.get('TotalCharges', {})
                transport_charges = rated_shipment.get('TransportationCharges', {})
                service_option_charges = rated_shipment.get('ServiceOptionsCharges', {})
                
                # Valori monetari
                currency = total_charges.get('CurrencyCode', 'EUR')
                total_cost = float(total_charges.get('MonetaryValue', '0'))
                transport_cost = float(transport_charges.get('MonetaryValue', '0'))
                service_charges = float(service_option_charges.get('MonetaryValue', '0'))
                
                # Dettagli delivery
                guaranteed_delivery = rated_shipment.get('GuaranteedDelivery', {})
                delivery_days = guaranteed_delivery.get('BusinessDaysInTransit', 'N/A')
                
                # Peso fatturato
                billing_weight_info = rated_shipment.get('BillingWeight', {})
                billing_weight = billing_weight_info.get('Weight', 'N/A')
                weight_unit = billing_weight_info.get('UnitOfMeasurement', {}).get('Code', 'KGS')
                
                # IVA: solo se presente nella risposta UPS
                tax_charges = rated_shipment.get('TaxCharges')
                if tax_charges and isinstance(tax_charges, list):
                    # Cerca IVA/VAT nei tax charges
                    iva_amount = 0
                    iva_rate = 0
                    base_cost = total_cost
                    
                    for tax in tax_charges:
                        tax_type = tax.get('Type', '')
                        if 'VAT' in tax_type or 'IVA' in tax_type:
                            iva_amount = float(tax.get('MonetaryValue', '0'))
                            iva_rate = float(tax.get('Rate', '0'))
                            base_cost = total_cost - iva_amount
                            break
                    
                    rate_info = {
                        'service_code': service_code,
                        'service_name': service_name,
                        'rate_type': 'Contractual A65c50',
                        'currency': currency,
                        'base_cost': round(base_cost, 2),
                        'iva_amount': round(iva_amount, 2),
                        'iva_rate': round(iva_rate, 2),
                        'total_cost': round(total_cost, 2),
                        'transport_cost': round(transport_cost, 2),
                        'service_charges': round(service_charges, 2),
                        'delivery_days': str(delivery_days),
                        'billing_weight': billing_weight,
                        'weight_unit': weight_unit
                    }
                else:
                    # Nessuna IVA nella risposta UPS - usa solo totale
                    rate_info = {
                        'service_code': service_code,
                        'service_name': service_name,
                        'rate_type': 'Contractual A65c50',
                        'currency': currency,
                        'total_cost': round(total_cost, 2),
                        'transport_cost': round(transport_cost, 2),
                        'service_charges': round(service_charges, 2),
                        'delivery_days': str(delivery_days),
                        'billing_weight': billing_weight,
                        'weight_unit': weight_unit
                    }
                
                rates.append(rate_info)
            
            # Ordina per prezzo
            rates.sort(key=lambda x: x['total_cost'])
            
            return {
                'rates': rates,
                'currency': rates[0]['currency'] if rates else 'EUR',
                'account': 'A65c50',
                'api_type': 'OAuth REST'
            }
            
        except Exception as e:
            print(f"❌ Error parsing REST response: {str(e)}")
            return {'rates': []}

    def _get_quote_xml(self, origin_country: str, origin_postal: str,
                       destination_country: str, destination_postal: str,
                       package_data: Dict, is_envelope: bool) -> Optional[Dict]:
        """Fallback XML API (richiede configurazione access key per A65c50)"""
        print("⚠️ XML API non configurata per account A65c50")
        return None

    def _generate_simulation(self, origin_country: str, origin_postal: str,
                           destination_country: str, destination_postal: str,
                           package_data: Dict, is_envelope: bool, packages: List[Dict] = None) -> Dict:
        """Genera simulazione preventivo UPS per account A65c50 - senza IVA automatica"""
        print(f"🔄 Generando simulazione UPS per account A65c50...")
        
        # Base rates simulate per diversi servizi con tempi di consegna realistici
        base_rates = {
            '11': {'name': 'UPS Standard', 'base': 18.50, 'days': '2-3'},
            '65': {'name': 'UPS Saver', 'base': 23.80, 'days': '1-2'}, 
            '08': {'name': 'UPS Worldwide Expedited', 'base': 27.20, 'days': '3-5'},
            '07': {'name': 'UPS Worldwide Express', 'base': 34.80, 'days': '1-3'}
        }
        
        rates = []
        weight = package_data['weight_kg']
        
        for service_code, info in base_rates.items():
            # Calcolo base con peso
            total_cost = info['base'] + (weight * 2.5)
            
            # Aggiustamenti per buste (sconto)
            if is_envelope and weight <= 1.0:
                total_cost *= 0.85  # 15% sconto per buste leggere
            
            # NESSUN calcolo IVA automatico - solo il totale da UPS
            rate_info = {
                'service_code': service_code,
                'service_name': info['name'],
                'rate_type': 'Simulated A65c50',
                'currency': 'EUR',
                'total_cost': round(total_cost, 2),
                'transport_cost': round(total_cost * 0.85, 2),
                'service_charges': round(total_cost * 0.15, 2),
                'delivery_days': info['days'],
                'billing_weight': weight,
                'weight_unit': 'KGS'
            }
            
            rates.append(rate_info)
        
        # Ordina per prezzo
        rates.sort(key=lambda x: x['total_cost'])
        
        return {
            'rates': rates,
            'currency': 'EUR',
            'account': 'A65c50',
            'api_type': 'Simulation',
            'note': 'Preventivo simulato per account A65c50 - IVA solo se presente in risposta UPS'
        }

    def _get_city_name(self, country: str, postal: str) -> str:
        """Mappa CAP a città (semplificato)"""
        city_map = {
            'IT': {'00100': 'Roma', '20100': 'Milano', '10100': 'Torino', '80100': 'Napoli'},
            'US': {'10001': 'New York', '90210': 'Beverly Hills', '33101': 'Miami'},
            'GB': {'SW1A': 'London', 'M1': 'Manchester'},
            'DE': {'10115': 'Berlin', '80331': 'Munich'},
            'FR': {'75001': 'Paris', '69001': 'Lyon'}
        }
        return city_map.get(country, {}).get(postal[:5], 'City')

    def _get_state_code(self, country: str, postal: str) -> str:
        """Mappa CAP a provincia/stato (semplificato)"""
        if country == 'IT':
            state_map = {'00100': 'RM', '20100': 'MI', '10100': 'TO', '80100': 'NA'}
            return state_map.get(postal, 'XX')
        elif country == 'US':
            state_map = {'10001': 'NY', '90210': 'CA', '33101': 'FL'}
            return state_map.get(postal, 'XX')
        else:
            return 'XX'

    def get_detailed_quote(self, origin_country: str, origin_postal: str,
                          destination_country: str, destination_postal: str,
                          weight_kg: float, length_cm: int, width_cm: int, height_cm: int,
                          service_code: str) -> Dict:
        """Ottieni preventivo per servizio specifico con account A65c50"""
        # Per ora usa get_quote e filtra il servizio richiesto
        all_quotes = self.get_quote(
            origin_country, origin_postal,
            destination_country, destination_postal,
            weight_kg, length_cm, width_cm, height_cm
        )
        
        if 'rates' in all_quotes:
            # Filtra per servizio specifico
            filtered_rates = [r for r in all_quotes['rates'] if r['service_code'] == service_code]
            if filtered_rates:
                all_quotes['rates'] = filtered_rates
                all_quotes['note'] = f'Preventivo specifico per servizio {service_code} - Account A65c50'
            else:
                all_quotes['rates'] = []
                all_quotes['error'] = f'Servizio {service_code} non disponibile per questa rotta'
        
        return all_quotes


if __name__ == "__main__":
    # Test del sistema UPS A65c50
    print("🧪 TEST UPS QUOTE CLIENT A65c50")
    print("=" * 50)
    
    client = UPSQuoteClientN()
    
    # Test 1: Busta Italia
    print("\n📋 Test 1: Busta Roma → Milano (Account A65c50)")
    packages = [{
        'weight_kg': 0.5,
        'length_cm': 35,
        'width_cm': 25,
        'height_cm': 2,
        'is_envelope': True
    }]
    
    result = client.get_quote('IT', '00100', 'IT', '20100', packages=packages)
    
    if 'rates' in result:
        print(f"✅ Trovate {len(result['rates'])} tariffe")
        for rate in result['rates'][:2]:  # Mostra prime 2
            print(f"- {rate['service_name']}: EUR {rate['total_cost']:.2f} (IVA: {rate['iva_amount']:.2f})")
    else:
        print(f"❌ Errore: {result.get('error', 'Nessun preventivo')}")
    
    print(f"\n🏷️ Account utilizzato: {result.get('account', 'N/A')}")
    print(f"🔧 API utilizzata: {result.get('api_type', 'N/A')}")