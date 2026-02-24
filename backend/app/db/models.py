"""SQLAlchemy models for snapshots, mill config, and trend points."""

import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from .database import Base


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    mill_id = Column(String, default="pine_hill", index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String, default="")
    inputs_json = Column(Text, nullable=False)
    results_json = Column(Text, nullable=False)

    @property
    def inputs(self):
        return json.loads(self.inputs_json)

    @inputs.setter
    def inputs(self, value):
        self.inputs_json = json.dumps(value)

    @property
    def results(self):
        return json.loads(self.results_json)

    @results.setter
    def results(self, value):
        self.results_json = json.dumps(value)


class TrendPoint(Base):
    __tablename__ = "trend_points"

    id = Column(Integer, primary_key=True, index=True)
    mill_id = Column(String, default="pine_hill", index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # Model predictions (auto-captured)
    predicted_sulfidity_pct = Column(Float, nullable=False)
    smelt_sulfidity_pct = Column(Float, default=0)
    nash_dry_lb_hr = Column(Float, default=0)
    naoh_dry_lb_hr = Column(Float, default=0)
    target_sulfidity_pct = Column(Float, default=29.4)
    # Lab measurement (user enters via PATCH)
    lab_sulfidity_pct = Column(Float, nullable=True)
    notes = Column(String, default="")


class MillConfig(Base):
    __tablename__ = "mill_configs"

    id = Column(Integer, primary_key=True, index=True)
    mill_id = Column(String, unique=True, index=True)
    mill_name = Column(String)
    config_json = Column(Text, nullable=False)

    @property
    def config(self):
        return json.loads(self.config_json)

    @config.setter
    def config(self, value):
        self.config_json = json.dumps(value)
