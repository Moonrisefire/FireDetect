import datetime
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from .database import Base

class MonitoringZone(Base):
    __tablename__ = "monitoring_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    polygon_geojson = Column(JSON, nullable=True)

    cameras = relationship("Camera", back_populates="zone")
    satellite_scans = relationship("SatelliteScan", back_populates="zone")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("monitoring_zones.id"), nullable=True)
    name = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    is_active = Column(Boolean, default=True)
    video_url = Column(String, nullable=True, default="0")

    zone = relationship("MonitoringZone", back_populates="cameras")
    detections = relationship("DetectionLog", back_populates="camera")


class DetectionLog(Base):
    __tablename__ = "detection_logs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    filename = Column(String)
    is_fire = Column(Boolean, default=False, index=True)
    confidence = Column(Float, nullable=True)
    bounding_boxes = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    camera = relationship("Camera", back_populates="detections")


class SatelliteScan(Base):
    __tablename__ = "satellite_scans"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("monitoring_zones.id"), nullable=True)
    mean_ndvi = Column(Float)
    total_risk_zones = Column(Integer)
    problem_areas = Column(JSON)
    weather_snapshot = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    valid_until = Column(DateTime)

    zone = relationship("MonitoringZone", back_populates="satellite_scans")