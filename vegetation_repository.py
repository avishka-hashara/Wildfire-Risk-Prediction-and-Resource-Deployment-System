from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models import VegetationData, Location
from datetime import datetime

class VegetationRepository:
    """
    Repository layer for managing Vegetation Data (NDVI) and Locations independently
    from the high-frequency Telemetry Logs.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_location(self, latitude: float, longitude: float) -> Location:
        """Retrieves an existing location by coordinates, or creates a new one."""
        stmt = select(Location).where(
            Location.latitude == latitude, 
            Location.longitude == longitude
        )
        result = await self.session.execute(stmt)
        location = result.scalar_one_or_none()
        
        if not location:
            location = Location(latitude=latitude, longitude=longitude)
            self.session.add(location)
            await self.session.flush()
            
        return location

    async def add_vegetation_data(self, location_id: int, ndvi: float, source: str, captured_at: datetime) -> VegetationData:
        """Adds a new vegetation data record for a given location."""
        veg_data = VegetationData(
            location_id=location_id,
            ndvi=ndvi,
            source=source,
            captured_at=captured_at
        )
        self.session.add(veg_data)
        await self.session.flush()
        return veg_data
        
    async def get_latest_ndvi(self, latitude: float, longitude: float) -> VegetationData:
        """Gets the most recently captured vegetation data for specific coordinates."""
        stmt = (
            select(VegetationData)
            .join(Location)
            .where(
                Location.latitude == latitude, 
                Location.longitude == longitude
            )
            .order_by(desc(VegetationData.captured_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
