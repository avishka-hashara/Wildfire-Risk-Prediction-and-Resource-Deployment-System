import abc
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

class VegetationProvider(abc.ABC):
    """
    Abstract base class defining the contract for all vegetation data providers.
    This abstraction allows the system to switch between Sentinel Hub, Google Earth Engine, 
    NASA, Copernicus, etc. without altering the core wildfire prediction logic.
    """
    
    @abc.abstractmethod
    async def get_ndvi(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetches the NDVI (Normalized Difference Vegetation Index) for a given location.
        
        Args:
            latitude (float): Latitude of the target sector.
            longitude (float): Longitude of the target sector.
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'ndvi' (float): The index value, typically -1.0 to 1.0.
                - 'source' (str): The name of the satellite/provider.
                - 'captured_at' (datetime): The timestamp when the imagery was captured.
        """
        pass


class MockVegetationProvider(VegetationProvider):
    """
    A mock implementation of the VegetationProvider for local development and testing.
    It generates realistic sample NDVI values without hitting real APIs or incurring costs.
    """
    
    async def get_ndvi(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Returns a mock NDVI reading. 
        Uses the coordinates to seed the generator, ensuring the same coordinates 
        return consistent vegetation values during a single test run.
        """
        # Realistic NDVI for vegetated land generally falls between 0.1 and 0.85
        # (Lower values indicate barren rock/sand, higher values indicate dense canopy)
        
        # Seed based on coordinates for pseudo-deterministic behavior
        seed_val = hash(f"{latitude:.4f},{longitude:.4f}")
        random.seed(seed_val)
        
        mock_ndvi = round(random.uniform(0.15, 0.85), 3)
        
        # Simulate the satellite having captured this image sometime in the last 5 days
        days_ago = random.randint(0, 5)
        captured_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        
        # Reset the seed to not affect global random state
        random.seed()
        
        return {
            "ndvi": mock_ndvi,
            "source": "MockSatellite-1A",
            "captured_at": captured_at
        }
