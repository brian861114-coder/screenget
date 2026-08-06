"""
exporter.py - 使用資料匯出（CSV / JSON）
"""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.analyzer import UsageAnalyzer


class UsageExporter:
    """將使用統計匯出為檔案"""

    def __init__(self, analyzer: UsageAnalyzer):
        self.analyzer = analyzer

    def build_export_payload(self, start: datetime, end: datetime) -> Dict[str, Any]:
        sessions = self.analyzer.db.get_sessions_in_range(start, end, include_active=False)
        rankings = self.analyzer.get_app_rankings(start, end)
        websites = self.analyzer.get_website_rankings(start, end)
        categories = self.analyzer.get_category_rankings(start, end)

        session_rows = []
        for s in sessions:
            name = s["app_name"]
            session_rows.append({
                "app_name": name,
                "category": self.analyzer.get_category_for(name, s.get("app_type")),
                "app_type": s.get("app_type", "app"),
                "window_title": s.get("window_title", ""),
                "url": s.get("url", ""),
                "start_time": s.get("clipped_start").isoformat() if s.get("clipped_start") else s.get("start_time"),
                "end_time": s.get("clipped_end").isoformat() if s.get("clipped_end") else s.get("end_time"),
                "duration_seconds": round(s.get("duration_seconds", 0) or 0, 3),
                "formatted_time": self.analyzer.format_duration(s.get("duration_seconds", 0) or 0),
            })

        return {
            "exported_at": datetime.now().isoformat(),
            "range": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "summary": {
                "total_seconds": sum(r["total_seconds"] for r in rankings),
                "app_count": len(rankings),
                "website_count": len(websites),
            },
            "rankings": rankings,
            "websites": websites,
            "categories": categories,
            "sessions": session_rows,
        }

    def export_json(self, path: str, start: datetime, end: datetime) -> str:
        payload = self.build_export_payload(start, end)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        return path

    def export_csv(self, path: str, start: datetime, end: datetime) -> str:
        payload = self.build_export_payload(start, end)
        fieldnames = [
            "app_name", "category", "app_type", "window_title", "url",
            "start_time", "end_time", "duration_seconds", "formatted_time",
        ]
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in payload["sessions"]:
                writer.writerow(row)
        return path
