from sqlalchemy import Column, Integer, Float, Boolean, DateTime, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now())
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, nullable=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    wind_speed = Column(Float, nullable=False)
    rain = Column(Float, nullable=False)
    ffmc = Column(Float, nullable=True)
    dmc = Column(Float, nullable=True)
    dc = Column(Float, nullable=True)
    isi = Column(Float, nullable=True)
    bui = Column(Float, nullable=True)
    fwi = Column(Float, nullable=True)
    risk_probability = Column(Float, nullable=False)
    evacuation_authorized = Column(Boolean, nullable=False)

class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('latitude', 'longitude', name='uq_location_lat_lng'),
        Index('ix_location_lat_lng', 'latitude', 'longitude'),
    )
    
    vegetation_data = relationship("VegetationData", back_populates="location")

class VegetationData(Base):
    __tablename__ = "vegetation_data"
    
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    ndvi = Column(Float, nullable=False)
    source = Column(String(50), nullable=True)
    captured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    location = relationship("Location", back_populates="vegetation_data")
    
    __table_args__ = (
        Index('ix_vegetation_data_location_id_captured_at', 'location_id', 'captured_at'),
    )
