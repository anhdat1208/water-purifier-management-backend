from __future__ import annotations

from pydantic import BaseModel


class DashboardStatsOut(BaseModel):
    total_devices: int
    active_devices: int
    maintenance_devices: int
    filters_due_soon: int


class FilterLifeTrendPoint(BaseModel):
    label: str
    value: int


class StatusDistribution(BaseModel):
    active: int
    maintenance: int
    inactive: int


class DeviceAttentionItem(BaseModel):
    id: int
    name: str
    location: str
    filter_life_percent: int
    status: str
    reason: str


class RecentActivityItem(BaseModel):
    id: str
    title: str
    description: str
    created_at: str
    type: str


class DashboardOverviewOut(BaseModel):
    stats: DashboardStatsOut
    filter_life_trend: list[FilterLifeTrendPoint]
    status_distribution: StatusDistribution
    devices_needing_attention: list[DeviceAttentionItem]
    recent_activities: list[RecentActivityItem]
