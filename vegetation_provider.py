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
import os
import asyncio
import httpx

class SentinelHubVegetationProvider(VegetationProvider):
    """
    A real implementation connecting to the Sentinel Hub Statistical API.
    Provides NDVI values from Sentinel-2 L2A satellite imagery.
    Handles OAuth authentication, retries, rate limiting (429), and cloudy pixels.
    """
    
    def __init__(self):
        self.client_id = os.getenv("SENTINEL_HUB_CLIENT_ID")
        self.client_secret = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ValueError("Sentinel Hub credentials missing. Set SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET.")
            
        self._access_token = None
        self._token_expires_at = 0.0

    async def _get_token(self) -> str:
        """Fetches and caches the OAuth2 token for Sentinel Hub API."""
        now = datetime.now(timezone.utc).timestamp()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://services.sentinel-hub.com/oauth/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            # Buffer of 60 seconds before actual expiration
            self._token_expires_at = now + data["expires_in"] - 60
            return self._access_token

    async def get_ndvi(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Public interface with built-in retry mechanism for rate limits (429) and temporary 5xx errors.
        """
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                return await self._fetch_ndvi(latitude, longitude)
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429 or status >= 500:
                    if attempt == max_retries - 1:
                        raise e
                    
                    delay = base_delay * (2 ** attempt)
                    if status == 429:
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            delay = float(retry_after)
                            
                    await asyncio.sleep(delay)
                else:
                    raise e
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(base_delay * (2 ** attempt))

    async def _fetch_ndvi(self, latitude: float, longitude: float) -> Dict[str, Any]:
        token = await self._get_token()
        
        # Bounding box of ~200m x 200m around the point
        # 1 degree latitude is approx 111km, so 0.001 deg is ~111m
        offset = 0.001
        bbox = [
            longitude - offset,
            latitude - offset,
            longitude + offset,
            latitude + offset
        ]
        
        # Look back 30 days to find cloud-free imagery
        time_to = datetime.now(timezone.utc)
        time_from = time_to - timedelta(days=30)
        
        # Evalscript calculates NDVI and ignores cloudy/invalid pixels using the Scene Classification Layer (SCL)
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{
                    bands: ["B04", "B08", "SCL", "dataMask"]
                }],
                output: [
                    { id: "ndvi", bands: 1 },
                    { id: "dataMask", bands: 1 }
                ]
            };
        }

        function evaluatePixel(sample) {
            // SCL: 3 (cloud shadows), 7, 8, 9, 10 (clouds)
            let isCloudOrShadow = [3, 7, 8, 9, 10].includes(sample.SCL);
            let valid = sample.dataMask === 1 && !isCloudOrShadow;
            
            let ndvi = 0;
            if (valid) {
                ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
            }
            
            return {
                ndvi: [ndvi],
                dataMask: [valid ? 1 : 0]
            };
        }
        """

        payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": time_from.isoformat().replace("+00:00", "Z"),
                                "to": time_to.isoformat().replace("+00:00", "Z")
                            }
                        }
                    }
                ]
            },
            "aggregation": {
                "timeRange": {
                    "from": time_from.isoformat().replace("+00:00", "Z"),
                    "to": time_to.isoformat().replace("+00:00", "Z")
                },
                "aggregationInterval": {
                    "of": "P30D"
                },
                "evalscript": evalscript,
                "resx": 10,
                "resy": 10
            }
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://services.sentinel-hub.com/api/v1/statistics",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=20.0
            )
            resp.raise_for_status()
            data = resp.json()
            
        try:
            stats = data["data"][0]["outputs"]["ndvi"]["bands"]["B0"]["stats"]
            ndvi_mean = stats.get("mean")
            if ndvi_mean is None:
                raise ValueError("No valid, cloud-free imagery found in the past 30 days.")
                
            interval_to_str = data["data"][0]["interval"]["to"]
            captured_at = datetime.fromisoformat(interval_to_str.replace("Z", "+00:00"))
        except (KeyError, IndexError) as e:
            raise ValueError(f"Failed to parse NDVI from Sentinel Hub response: {e}")
            
        return {
            "ndvi": float(ndvi_mean),
            "source": "Sentinel-2 L2A (Sentinel Hub)",
            "captured_at": captured_at
        }
