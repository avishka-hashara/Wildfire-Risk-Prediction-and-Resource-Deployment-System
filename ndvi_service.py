from datetime import datetime
from typing import Optional, Dict, Tuple
from vegetation_provider import VegetationProvider
from vegetation_repository import VegetationRepository

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
        # Simple in-memory cache to quickly serve latest values without hitting DB/API
        self._cache: Dict[Tuple[float, float], float] = {}

    def _validate_ndvi(self, ndvi: float) -> None:
        """
        Validates the NDVI value. Valid NDVI ranges from -1.0 to 1.0.
        Throws InvalidNdviException if out of bounds.
        """
        if not (-1.0 <= ndvi <= 1.0):
            raise InvalidNdviException(f"Invalid NDVI value: {ndvi}. Must be between -1.0 and 1.0.")

    async def fetch_and_store_ndvi(self, latitude: float, longitude: float) -> float:
        """
        Retrieves fresh NDVI from the provider, validates it, saves it to PostgreSQL, 
        updates the cache, and returns the value.
        """
        # 1. Retrieve NDVI from the provider
        resp = await self.provider.get_ndvi(latitude, longitude)
        ndvi_value = resp["ndvi"]
        
        # 2. Validate and reject invalid values
        self._validate_ndvi(ndvi_value)
        
        # 3. Save values to PostgreSQL
        location = await self.repository.get_or_create_location(latitude, longitude)
        await self.repository.add_vegetation_data(
            location_id=location.id,
            ndvi=ndvi_value,
            source=resp["source"],
            captured_at=resp["captured_at"].replace(tzinfo=None)
        )
        
        # 4. Cache recent value
        self._cache[(latitude, longitude)] = ndvi_value
        
        return ndvi_value

    async def get_latest_ndvi(self, latitude: float, longitude: float) -> Optional[float]:
        """
        Returns the latest NDVI for a given location.
        Checks the local cache first, then falls back to the database.
        """
        # Check cache
        coord_key = (latitude, longitude)
        if coord_key in self._cache:
            return self._cache[coord_key]
            
        # Fallback to Database
        veg_data = await self.repository.get_latest_ndvi(latitude, longitude)
        if veg_data:
            self._cache[coord_key] = veg_data.ndvi
            return veg_data.ndvi
            
        return None
