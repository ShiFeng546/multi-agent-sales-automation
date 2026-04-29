from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .sales_agents import (
    CampaignBrief,
    LeadScoutAgent,
    OpsManagerAgent,
    OutreachAgent,
    ResearchAgent,
    SegmentAgent,
    SequenceAgent,
)


class MultiAgentSalesAutomationEngine:
    def __init__(self, leads_path: Path) -> None:
        self._leads_path = leads_path
        self._agents = [
            LeadScoutAgent(),
            ResearchAgent(),
            SegmentAgent(),
            OutreachAgent(),
            SequenceAgent(),
            OpsManagerAgent(),
        ]

    def load_sample_leads(self) -> list[dict[str, Any]]:
        with self._leads_path.open("r", encoding="utf-8") as handle:
            leads = json.load(handle)
        return leads

    def run_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        brief = CampaignBrief.from_payload(payload)
        leads = self.load_sample_leads()
        timeline: list[dict[str, Any]] = []
        state: dict[str, Any] = {
            "brief": brief,
            "raw_leads": leads,
            "qualified_leads": [],
            "result_leads": [],
        }

        for agent in self._agents:
            output = agent.run(state)
            timeline.append(output["timeline"])
            state.update(output.get("state_updates", {}))

        result_leads = state["result_leads"]
        channel_mix = Counter()
        priority_mix = Counter()
        segment_mix = Counter()
        fit_scores: list[int] = []

        for lead in result_leads:
            fit_scores.append(lead["fit_score"])
            segment_mix.update([lead["segment"]])
            priority_mix.update([lead["priority"]])
            channel_mix.update(lead["recommended_channels"])

        run_id = uuid.uuid4().hex[:10]
        created_at = datetime.now().isoformat(timespec="seconds")
        summary = {
            "campaign_name": brief.campaign_name,
            "created_at": created_at,
            "qualified_leads": len(result_leads),
            "average_fit_score": round(sum(fit_scores) / len(fit_scores), 1) if fit_scores else 0,
            "high_priority_count": priority_mix.get("P1", 0),
            "top_segment": segment_mix.most_common(1)[0][0] if segment_mix else "暂无",
            "channel_mix": dict(channel_mix.most_common()),
            "priority_mix": dict(priority_mix.most_common()),
        }

        return {
            "run_id": run_id,
            "summary": summary,
            "timeline": timeline,
            "brief": brief.to_dict(),
            "playbook": state["playbook"],
            "result_leads": result_leads,
            "sample_count": len(leads),
        }
