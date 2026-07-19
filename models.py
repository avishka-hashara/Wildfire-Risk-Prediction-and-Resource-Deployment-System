from sqlalchemy import Column, Integer, Float, Boolean, DateTime
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
