from datetime import datetime, timedelta
import logging
from typing import Optional
from vegetation_provider import VegetationProvider
from vegetation_repository import VegetationRepository

logger = logging.getLogger(__name__)

class InvalidNdviException(Exception):
    """Exception raised when an NDVI value is outside the valid [-1.0, 1.0] range."""
    pass

class NdviService:
    """
    Service layer for managing vegetation health data.
    Encapsulates business logic for retrieving, validating, caching, and storing NDVI.
    """
    
    def __init__(self, provider: VegetationProvider, repository: VegetationRepository):
        self.provider = provider
        self.repository = repository

    def _validate_ndvi(self, ndvi: float) -> None:
        """
        Validates the NDVI value. Valid NDVI ranges from -1.0 to 1.0.
        Throws InvalidNdviException if out of bounds.
        """
        if not (-1.0 <= ndvi <= 1.0):
            raise InvalidNdviException(f"Invalid NDVI value: {ndvi}. Must be between -1.0 and 1.0.")

    async def get_ndvi(self, latitude: float, longitude: float) -> Optional[float]:
        """
        Retrieves the NDVI value according to the caching rules:
        - Cache NDVI in PostgreSQL for 24 hours.
        - If cache exists and is < 24 hours old: return cached value.
        - If cache expired or doesn't exist: request a new value.
        - If provider fails: use latest cached value (even if expired).
        - If no cached value exists at all: return None.
        """
        # 1. Check PostgreSQL for the latest cached value
        veg_data = await self.repository.get_latest_ndvi(latitude, longitude)
        
        now = datetime.now()
        cache_valid = False
        
        if veg_data and veg_data.created_at:
            # Check if the cache was created within the last 24 hours
            if (now - veg_data.created_at) <= timedelta(hours=24):
                cache_valid = True

        if cache_valid:
            # 2. Cache exists and is valid: return cached value
            return veg_data.ndvi

        # 3. Cache expired or doesn't exist: request a new value.
        try:
            resp = await self.provider.get_ndvi(latitude, longitude)
            ndvi_value = resp["ndvi"]
            
            # Validate and reject invalid values
            self._validate_ndvi(ndvi_value)
            
            # Save values to PostgreSQL (this essentially refreshes the cache)
            location = await self.repository.get_or_create_location(latitude, longitude)
            await self.repository.add_vegetation_data(
                location_id=location.id,
                ndvi=ndvi_value,
                source=resp["source"],
                captured_at=resp["captured_at"].replace(tzinfo=None)
            )
            return ndvi_value
            
        except Exception as e:
            logger.warning(f"Failed to fetch new NDVI for {latitude},{longitude}: {e}")
            # 4. Provider fails: use latest cached value if it exists
            if veg_data:
                return veg_data.ndvi
            
            # 5. If no cached value exists at all: return None
            return None
