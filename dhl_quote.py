"""
DHL Quote API Client
Gestisce esclusivamente i preventivi DHL separatamente dal tracking
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from config import DHLConfig


@dataclass
class ShipmentQuoteRequest:
    """Data class per richiesta preventivo di spedizione"""
    origin_country: str
    origin_city: str
    origin_postal_code: str
    destination_country: str
    destination_city: str
    destination_postal_code: str
    weight_kg: float
    length_cm: float = 0
    width_cm: float = 0
    height_cm: float = 0
    declared_value: float = 0
    currency: str = "EUR"
    shipment_date: str = None  # Format: DD-MM-YYYY
    is_dutiable: bool = False  # True per merce, False per documenti
    pieces: int = 1  # Numero di colli
    
    def __post_init__(self):
        if self.shipment_date is None:
            # Default to tomorrow in YYYY-MM-DD format (DHL standard)
            tomorrow = datetime.now() + timedelta(days=1)
            self.shipment_date = tomorrow.strftime("%Y-%m-%d")


class DHLQuoteClient:
    """Client dedicato per i preventivi DHL"""
    
    def __init__(self, config: DHLConfig = None):
        """
        Initialize DHL Quote client
        
        Args:
            config: DHLConfig object, if None loads from environment
        """
        self.config = config or DHLConfig.from_env()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/xml',
            'SOAPAction': ''
        })
    
    def get_quote(self, quote_request: ShipmentQuoteRequest) -> Dict:
        """
        Ottieni preventivo di spedizione da DHL
        
        Args:
            quote_request: ShipmentQuoteRequest con dettagli spedizione
            
        Returns:
            Dict con preventivo o errore
        """
        try:
            # Create XML request with customer code
            xml_request = self._create_quote_xml(quote_request)
            
            # Debug output if enabled
            if self.config.debug:
                print("📤 DEBUG - RICHIESTA XML PREVENTIVO DHL:")
                print("=" * 80)
                print(xml_request)
                print("=" * 80)
            
            # Make API request
            response = self.session.post(
                self.config.effective_url,
                data=xml_request,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            
            # Debug output if enabled
            if self.config.debug:
                print("📥 DEBUG - RISPOSTA XML PREVENTIVO DHL:")
                print("=" * 80)
                print(response.text)
                print("=" * 80)
            
            # Parse response
            return self._parse_quote_response(response.text)
            
        except requests.exceptions.RequestException as e:
            return {
                'error': f"Errore richiesta API: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': f"Errore imprevisto: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_quote_xml(self, quote_request: ShipmentQuoteRequest) -> str:
        """
        Crea richiesta XML per API preventivi DHL con codice cliente
        
        Args:
            quote_request: ShipmentQuoteRequest con dettagli spedizione
            
        Returns:
            String XML per la richiesta preventivo
        """
        # Generate pieces XML based on number of pieces
        pieces_xml = ""
        for i in range(quote_request.pieces):
            pieces_xml += f"""
                <Piece>
                    <PieceID>{i + 1}</PieceID>
                    <Height>{quote_request.height_cm}</Height>
                    <Depth>{quote_request.length_cm}</Depth>
                    <Width>{quote_request.width_cm}</Width>
                    <Weight>{quote_request.weight_kg / quote_request.pieces:.2f}</Weight>
                </Piece>"""

        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:DCTRequest xmlns:p="http://www.dhl.com" xmlns:p1="http://www.dhl.com/datatypes" xmlns:p2="http://www.dhl.com/DCTRequestdatatypes" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.dhl.com DCT-req.xsd ">
    <GetQuote>
        <Request>
            <ServiceHeader>
                <MessageTime>{datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+01:00</MessageTime>
                <MessageReference>1234567890123456789012345678901</MessageReference>
                <SiteID>{self.config.site_id}</SiteID>
                <Password>{self.config.password}</Password>
            </ServiceHeader>
        </Request>
        <From>
            <CountryCode>{quote_request.origin_country}</CountryCode>
            <Postalcode>{quote_request.origin_postal_code}</Postalcode>
            <City>{quote_request.origin_city}</City>
        </From>
        <BkgDetails>
            <PaymentCountryCode>IT</PaymentCountryCode>
            <Date>{quote_request.shipment_date}</Date>
            <ReadyTime>PT9H</ReadyTime>
            <ReadyTimeGMTOffset>+01:00</ReadyTimeGMTOffset>
            <DimensionUnit>CM</DimensionUnit>
            <WeightUnit>KG</WeightUnit>
            <Pieces>{pieces_xml}
            </Pieces>
            <PaymentAccountNumber>{self.config.customer_code}</PaymentAccountNumber>
            <IsDutiable>{'Y' if quote_request.is_dutiable else 'N'}</IsDutiable>
            <NetworkTypeCode>AL</NetworkTypeCode>
            <InsuredValue>0</InsuredValue>
            <InsuredCurrency>EUR</InsuredCurrency>
        </BkgDetails>
        <To>
            <CountryCode>{quote_request.destination_country}</CountryCode>
            <Postalcode>{quote_request.destination_postal_code}</Postalcode>
            <City>{quote_request.destination_city}</City>
        </To>
    </GetQuote>
</p:DCTRequest>"""
        
        return xml_template
    
    def _parse_quote_response(self, xml_response: str) -> Dict:
        """
        Parse XML response from DHL quote API
        
        Args:
            xml_response: XML response string from DHL
            
        Returns:
            Dict with parsed quote information
        """
        try:
            root = ET.fromstring(xml_response)
            
            # Check for errors first
            error_elements = root.findall(".//Condition/ConditionCode")
            if error_elements:
                errors = []
                for error_elem in error_elements:
                    error_code = error_elem.text
                    error_data_elem = error_elem.find("../ConditionData")
                    error_data = error_data_elem.text if error_data_elem is not None else "No details"
                    errors.append(f"{error_code}: {error_data}")
                
                return {
                    'error': "DHL API Error: " + "; ".join(errors),
                    'timestamp': datetime.now().isoformat()
                }
            
            # Parse successful response
            services = []
            quote_elements = root.findall(".//QtdShp")
            
            for quote in quote_elements:
                service_name = self._get_text_safe(quote, "ProductShortName", "Unknown Service")
                service_code = self._get_text_safe(quote, "GlobalProductCode", "")
                
                # Escludi EXPRESS EASY dai risultati
                if "EXPRESS EASY" in service_name.upper():
                    continue
                
                currency = self._get_text_safe(quote, "CurrencyCode", "EUR")
                
                # Try to get shipping charge
                shipping_charge = self._get_text_safe(quote, "ShippingCharge", "0")
                weight_charge = self._get_text_safe(quote, "WeightCharge", "0")
                weight_charge_tax = self._get_text_safe(quote, "WeightChargeTax", "0")
                
                # Calculate total price
                total_price = float(shipping_charge) if shipping_charge else 0.0
                if total_price == 0:
                    total_price = float(weight_charge) + float(weight_charge_tax)
                
                # Get delivery info
                delivery_date = self._get_text_safe(quote, "DeliveryDate", "")
                delivery_time = self._get_text_safe(quote, "DeliveryTime", "")
                transit_days = self._get_text_safe(quote, "TotalTransitDays", "")
                
                # Format delivery info
                delivery_info = ""
                if delivery_date:
                    delivery_info = f"Consegna: {delivery_date}"
                    if delivery_time:
                        # Convert PT format (e.g., PT12H) to readable format
                        time_str = delivery_time.replace("PT", "").replace("H", ":00")
                        if time_str != "23:59:00":  # Don't show end of day
                            delivery_info += f" entro le {time_str}"
                    if transit_days:
                        delivery_info += f" ({transit_days} giorni lavorativi)"
                
                services.append({
                    'service_name': service_name,
                    'service_code': service_code,
                    'total_price': f"{total_price:.2f}€",
                    'currency': currency,
                    'delivery_info': delivery_info,
                    'raw_price': total_price
                })
            
            # Sort by price
            services.sort(key=lambda x: x['raw_price'])
            
            return {
                'success': True,
                'services': services,
                'timestamp': datetime.now().isoformat(),
                'customer_code_used': self.config.customer_code or "Tariffe pubbliche"
            }
            
        except ET.ParseError as e:
            return {
                'error': f"Errore parsing XML: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': f"Errore processing response: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_text_safe(self, element, tag_name: str, default: str = "") -> str:
        """Safely get text from XML element"""
        found = element.find(f".//{tag_name}")
        return found.text if found is not None and found.text else default


def test_quote_with_customer_code():
    """Test preventivo con codice cliente"""
    print("🧪 Test preventivo DHL con codice cliente...")
    
    client = DHLQuoteClient()
    
    quote_request = ShipmentQuoteRequest(
        origin_country="IT",
        origin_city="Roma", 
        origin_postal_code="00100",
        destination_country="IT",
        destination_city="Bari",
        destination_postal_code="70100",
        weight_kg=1.0,
        length_cm=20,
        width_cm=15,
        height_cm=10
    )
    
    result = client.get_quote(quote_request)
    
    if 'error' in result:
        print(f"❌ Errore: {result['error']}")
    else:
        print(f"✅ Preventivo ottenuto con: {result['customer_code_used']}")
        print(f"📦 Trovati {len(result['services'])} servizi:\n")
        
        for service in result['services']:
            print(f"  🚚 {service['service_name']}")
            print(f"     💰 Prezzo: {service['total_price']}")
            print(f"     📅 {service['delivery_info']}")
            print()


if __name__ == "__main__":
    test_quote_with_customer_code()