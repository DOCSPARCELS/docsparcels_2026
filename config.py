"""
Configuration file for DHL and UPS API
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class DHLConfig:
    """Configuration class for DHL API settings"""
    
    # API Configuration
    site_id: str
    password: str
    customer_code: str = ""  # Codice cliente DHL per tariffe contrattuali
    base_url: str = "https://xmlpi-ea.dhl.com/XMLShippingServlet"
    tracking_url: str = "https://xmlpi-ea.dhl.com/XMLShippingServlet"  # Same endpoint for tracking
    testing_url: str = "http://xmlpitest-ea.dhl.com/XMLShippingServlet"
    locator_url: str = "https://locator.dhl.com/ServicePointLocator/rest/servicepoints?address="
    
    # Environment settings
    use_testing: bool = False
    debug: bool = False
    timeout: int = 30
    max_retries: int = 3
    
    @property
    def effective_url(self) -> str:
        """Get the effective API URL based on environment"""
        return self.testing_url if self.use_testing else self.base_url
    
    @classmethod
    def from_env(cls) -> 'DHLConfig':
        """Create configuration from environment variables"""
        site_id = os.getenv('DHL_SITE_ID')
        password = os.getenv('DHL_PASSWORD')
        
        if not site_id or not password:
            raise ValueError("DHL_SITE_ID and DHL_PASSWORD environment variables are required")
        
        return cls(
            site_id=site_id.strip("'\""),  # Remove quotes if present
            password=password.strip("'\""),  # Remove quotes if present
            customer_code=os.getenv('DHL_CUSTOMER_CODE', '').strip("'\""),  # Codice cliente DHL
            base_url=os.getenv('DHL_BASE_URL', 'https://xmlpi-ea.dhl.com/XMLShippingServlet').strip("'\""),
            testing_url=os.getenv('DHL_BASE_URL_TESTING', 'http://xmlpitest-ea.dhl.com/XMLShippingServlet').strip("'\""),
            locator_url=os.getenv('DHL_BASE_URL_LOCATOR', 'https://locator.dhl.com/ServicePointLocator/rest/servicepoints?address=').strip("'\""),
            debug=os.getenv('DHL_API_DEBUG', '0') == '1',
            use_testing=os.getenv('DHL_USE_TESTING', 'false').lower() == 'true',
            timeout=int(os.getenv('DHL_TIMEOUT', '30')),
            max_retries=int(os.getenv('DHL_MAX_RETRIES', '3'))
        )


# Default configuration for development
DEFAULT_CONFIG = DHLConfig(
    site_id="xmlDEPDILUCA",  # Your actual site ID from .env
    password="2YLDco7pv0",   # Your actual password from .env
    customer_code="106288496",  # Your real DHL customer code
    use_testing=True  # Use testing environment for development
)


@dataclass
@dataclass
class UPSConfig:
    """Configuration class for UPS API settings"""
    
    # API Configuration
    username: str
    password: str
    license: str
    account: str
    client_id: str = ""  # OAuth Client ID per REST API
    client_secret: str = ""  # OAuth Client Secret per REST API
    base_url: str = "https://onlinetools.ups.com/"
    testing_url: str = "https://wwwcie.ups.com/"
    
    # Environment settings
    use_testing: bool = False
    debug: bool = False
    timeout: int = 30
    max_retries: int = 3
    
    @property
    def effective_url(self) -> str:
        """Get the effective API URL based on environment"""
        return self.testing_url if self.use_testing else self.base_url
    
    @classmethod
    def from_env(cls) -> 'UPSConfig':
        """Create configuration from environment variables"""
        username = os.getenv('UPS_USERNAME')
        password = os.getenv('UPS_PASSWORD')
        license = os.getenv('UPS_LICENSE')
        account = os.getenv('UPS_ACCOUNT')
        
        if not all([username, password, license, account]):
            raise ValueError("UPS_USERNAME, UPS_PASSWORD, UPS_LICENSE, and UPS_ACCOUNT environment variables are required")
        
        return cls(
            username=username.strip("'\""),
            password=password.strip("'\""),
            license=license.strip("'\""),
            account=account.strip("'\""),
            client_id=os.getenv('UPS_CLIENT_ID', '').strip("'\""),
            client_secret=os.getenv('UPS_CLIENT_SECRET', '').strip("'\""),
            base_url=os.getenv('UPS_BASE_URL', 'https://onlinetools.ups.com/').strip("'\""),
            testing_url=os.getenv('UPS_BASE_URL_TESTING', 'https://wwwcie.ups.com/').strip("'\""),
            debug=os.getenv('UPS_API_DEBUG', '0') == '1',
            use_testing=os.getenv('UPS_USE_TESTING', 'false').lower() == 'true',
            timeout=int(os.getenv('UPS_TIMEOUT', '30')),
            max_retries=int(os.getenv('UPS_MAX_RETRIES', '3'))
        )


# Default UPS configuration for development
DEFAULT_UPS_CONFIG = UPSConfig(
    username="Dep33",
    password="Parcels1", 
    license="ED3661DFFEF82EDD",
    account="X8899X",
    client_id="",  # Inserire Client ID da MyUPS Developer
    client_secret="",  # Inserire Client Secret da MyUPS Developer
    use_testing=True  # Use testing environment for development
)


@dataclass
class SpediamoproConfig:
    """Configuration class for Spediamo Pro API settings"""
    
    # API Configuration
    username: str
    password: str
    authcode: str  # AuthCode richiesto per l'autenticazione
    base_url: str = "https://core.spediamopro.com/api/v1/"
    testing_url: str = "https://test.spediamopro.com/api/v1/"  # Se disponibile
    
    # Environment settings
    use_testing: bool = False
    debug: bool = False
    timeout: int = 30
    max_retries: int = 3
    
    # JWT Token settings
    token: Optional[str] = None
    token_expires_at: Optional[float] = None
    
    @property
    def effective_url(self) -> str:
        """Get the effective API URL based on environment"""
        return self.testing_url if self.use_testing else self.base_url
    
    @classmethod
    def from_env(cls) -> 'SpediamoproConfig':
        """Create configuration from environment variables"""
        username = os.getenv('SPEDIAMOPRO_USERNAME')
        password = os.getenv('SPEDIAMOPRO_PASSWORD')
        authcode = os.getenv('SPEDIAMOPRO_AUTHCODE')
        
        if not username or not password or not authcode:
            raise ValueError("SPEDIAMOPRO_USERNAME, SPEDIAMOPRO_PASSWORD, and SPEDIAMOPRO_AUTHCODE environment variables are required")
        
        return cls(
            username=username.strip("'\""),
            password=password.strip("'\""),
            authcode=authcode.strip("'\""),
            base_url=os.getenv('SPEDIAMOPRO_BASE_URL', 'https://core.spediamopro.com/api/v1/').strip("'\""),
            testing_url=os.getenv('SPEDIAMOPRO_BASE_URL_TESTING', 'https://test.spediamopro.com/api/v1/').strip("'\""),
            debug=os.getenv('SPEDIAMOPRO_API_DEBUG', '0') == '1',
            use_testing=os.getenv('SPEDIAMOPRO_USE_TESTING', 'false').lower() == 'true',
            timeout=int(os.getenv('SPEDIAMOPRO_TIMEOUT', '30')),
            max_retries=int(os.getenv('SPEDIAMOPRO_MAX_RETRIES', '3'))
        )


# Default Spediamo Pro configuration for development
DEFAULT_SPEDIAMOPRO_CONFIG = SpediamoproConfig(
    username="",  # Inserire username Spediamo Pro
    password="",  # Inserire password Spediamo Pro
    authcode="",  # Inserire authCode Spediamo Pro
    use_testing=True  # Use testing environment for development
)