from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,，/\n]", value) if item.strip()]
    return [str(value).strip()]


def contains_any(text: str, needles: list[str]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(needle) in normalized for needle in needles if needle)


def overlap_score(texts: list[str], keywords: list[str]) -> int:
    searchable = normalize_text(" ".join(texts))
    return sum(1 for keyword in keywords if keyword and normalize_text(keyword) in searchable)


def first_non_empty(options: list[str], fallback: str) -> str:
    for option in options:
        if option:
            return option
    return fallback


@dataclass(slots=True)
class CampaignBrief:
    campaign_name: str
    product_name: str
    product_value: str
    target_industries: list[str] = field(default_factory=list)
    target_sizes: list[str] = field(default_factory=list)
    target_personas: list[str] = field(default_factory=list)
    target_markets: list[str] = field(default_factory=list)
    business_goal: str = ""
    offer: str = ""
    tone: str = "专业、直接"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CampaignBrief":
        return cls(
            campaign_name=payload.get("campaign_name", "增长自动化行动"),
            product_name=payload.get("product_name", "GrowthPilot"),
            product_value=payload.get(
                "product_value",
                "帮助销售团队自动筛选高意向客户、生成个性化触达文案并安排自动跟进",
            ),
            target_industries=normalize_list(payload.get("target_industries", ["SaaS", "电商", "教育科技"])),
            target_sizes=normalize_list(payload.get("target_sizes", ["50-200", "200-1000"])),
            target_personas=normalize_list(payload.get("target_personas", ["销售总监", "增长负责人", "市场负责人"])),
            target_markets=normalize_list(payload.get("target_markets", ["中国", "东南亚"])),
            business_goal=payload.get("business_goal", "提升高质量线索转化率并缩短销售首触达时间"),
            offer=payload.get("offer", "提供 30 分钟增长诊断和 14 天试用方案"),
            tone=payload.get("tone", "专业、直接"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_name": self.campaign_name,
            "product_name": self.product_name,
            "product_value": self.product_value,
            "target_industries": self.target_industries,
            "target_sizes": self.target_sizes,
            "target_personas": self.target_personas,
            "target_markets": self.target_markets,
            "business_goal": self.business_goal,
            "offer": self.offer,
            "tone": self.tone,
        }


class BaseAgent:
    name = "Base Agent"
    purpose = ""

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class LeadScoutAgent(BaseAgent):
    name = "Lead Scout Agent"
    purpose = "筛选与 ICP 高度匹配的目标客户"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief: CampaignBrief = state["brief"]
        qualified: list[dict[str, Any]] = []

        for lead in state["raw_leads"]:
            match_reasons: list[str] = []
            score = 0

            if contains_any(lead["industry"], brief.target_industries):
                match_reasons.append("行业匹配")
                score += 32
            if contains_any(lead["company_size"], brief.target_sizes):
                match_reasons.append("规模匹配")
                score += 18
            if contains_any(lead["role"], brief.target_personas):
                match_reasons.append("决策角色匹配")
                score += 24
            if contains_any(lead["region"], brief.target_markets):
                match_reasons.append("区域匹配")
                score += 14
            if lead.get("trigger_event"):
                match_reasons.append("存在增长触发事件")
                score += 10

            if score >= 50 or (contains_any(lead["role"], brief.target_personas) and contains_any(lead["industry"], brief.target_industries)):
                lead_copy = dict(lead)
                lead_copy["qualification_score"] = score
                lead_copy["match_reasons"] = match_reasons
                qualified.append(lead_copy)

        qualified.sort(key=lambda item: item["qualification_score"], reverse=True)
        summary = f"从 {len(state['raw_leads'])} 条样本线索中筛出 {len(qualified)} 条高匹配客户。"

        return {
            "timeline": {
                "agent": self.name,
                "purpose": self.purpose,
                "summary": summary,
                "highlights": [lead["company"] for lead in qualified[:3]],
            },
            "state_updates": {"qualified_leads": qualified},
        }


class ResearchAgent(BaseAgent):
    name = "Research Agent"
    purpose = "分析客户当前阶段、潜在痛点与成交优先级"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief: CampaignBrief = state["brief"]
        researched: list[dict[str, Any]] = []
        product_keywords = normalize_list(brief.product_value) + normalize_list(brief.business_goal) + normalize_list(brief.offer)

        for lead in state["qualified_leads"]:
            lead_copy = dict(lead)
            text_pool = [lead["company"], lead["industry"], lead["trigger_event"], " ".join(lead["challenges"])]
            signal_points = overlap_score(text_pool, product_keywords)
            challenge_count = len(lead["challenges"])
            trigger_bonus = 12 if lead["trigger_event"] else 0
            fit_score = min(
                98,
                lead["qualification_score"]
                + signal_points * 3
                + trigger_bonus
                + challenge_count * 2
                + math.ceil(len(lead["stack"]) / 3),
            )
            urgency = "高" if fit_score >= 82 else "中" if fit_score >= 68 else "低"
            priority = "P1" if fit_score >= 82 else "P2" if fit_score >= 68 else "P3"
            primary_pain = first_non_empty(lead["challenges"], "线索管理分散")
            hook = self._build_hook(lead_copy, brief)
            lead_copy.update(
                {
                    "fit_score": fit_score,
                    "urgency": urgency,
                    "priority": priority,
                    "pain_hypothesis": primary_pain,
                    "recommended_hook": hook,
                }
            )
            researched.append(lead_copy)

        researched.sort(key=lambda item: item["fit_score"], reverse=True)
        avg_fit = round(sum(item["fit_score"] for item in researched) / len(researched), 1) if researched else 0
        summary = f"完成客户研究，平均匹配分 {avg_fit}，优先级 P1 客户 {sum(1 for item in researched if item['priority'] == 'P1')} 个。"

        return {
            "timeline": {
                "agent": self.name,
                "purpose": self.purpose,
                "summary": summary,
                "highlights": [item["recommended_hook"] for item in researched[:2]],
            },
            "state_updates": {"researched_leads": researched},
        }

    def _build_hook(self, lead: dict[str, Any], brief: CampaignBrief) -> str:
        if "融资" in lead["trigger_event"] or "funding" in normalize_text(lead["trigger_event"]):
            return f"{lead['company']} 刚完成融资，适合用 {brief.product_name} 在扩张期快速建立获客自动化闭环。"
        if "招聘" in lead["trigger_event"] or "hiring" in normalize_text(lead["trigger_event"]):
            return f"{lead['company']} 正在扩张团队，说明他们对高质量线索和标准化触达流程有迫切需求。"
        return f"{lead['company']} 当前面临“{lead['challenges'][0]}”压力，可以切入 {brief.product_value[:22]} 的场景。"


class SegmentAgent(BaseAgent):
    name = "Segment Agent"
    purpose = "将客户分层并设计差异化运营策略"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief: CampaignBrief = state["brief"]
        segmented: list[dict[str, Any]] = []
        segment_counter = Counter()

        for lead in state["researched_leads"]:
            lead_copy = dict(lead)
            segment, angle, cta = self._segment_lead(lead_copy, brief)
            lead_copy.update(
                {
                    "segment": segment,
                    "campaign_angle": angle,
                    "cta": cta,
                }
            )
            segment_counter.update([segment])
            segmented.append(lead_copy)

        summary = f"完成客户分层，当前主力客群是“{segment_counter.most_common(1)[0][0]}”。" if segmented else "没有可分层客户。"
        return {
            "timeline": {
                "agent": self.name,
                "purpose": self.purpose,
                "summary": summary,
                "highlights": [f"{name}: {count}" for name, count in segment_counter.most_common(3)],
            },
            "state_updates": {"segmented_leads": segmented},
        }

    def _segment_lead(self, lead: dict[str, Any], brief: CampaignBrief) -> tuple[str, str, str]:
        trigger = normalize_text(lead["trigger_event"])
        challenges = normalize_text(" ".join(lead["challenges"]))
        industry = normalize_text(lead["industry"])

        if "funding" in trigger or "融资" in trigger or "expansion" in trigger:
            return (
                "扩张增长型",
                f"强调 {brief.product_name} 如何在团队扩张时统一线索评分、文案生成和跟进节奏。",
                "预约 30 分钟增长自动化诊断",
            )
        if "retention" in challenges or "留存" in challenges or "复购" in challenges:
            return (
                "激活提效型",
                "以用户激活、复购和再营销自动化为切口，主打精细化运营。",
                "领取再营销策略清单",
            )
        if "saas" in industry or "software" in industry or "tech" in industry:
            return (
                "流程标准化型",
                "切入线索管理和 SDR 标准动作，把销售触达动作产品化。",
                "获取标准化触达模板包",
            )
        return (
            "渠道拓展型",
            "突出跨渠道获客、跟进可视化和低成本扩量。",
            "申请渠道拓展试跑计划",
        )


class OutreachAgent(BaseAgent):
    name = "Outreach Agent"
    purpose = "生成多渠道个性化触达内容"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief: CampaignBrief = state["brief"]
        messaged: list[dict[str, Any]] = []

        for lead in state["segmented_leads"]:
            lead_copy = dict(lead)
            email_subject = f"{lead['company']} 的增长自动化机会"
            email_body = (
                f"{lead['contact_name']}，你好。我注意到 {lead['company']} 最近 {lead['trigger_event']}，"
                f"同时团队在处理“{lead['pain_hypothesis']}”这类问题。"
                f"{brief.product_name} 可以帮助你们把线索筛选、个性化触达和跟进节奏自动化，"
                f"减少销售手动整理名单和写文案的时间。"
                f"如果你愿意，我可以基于你们当前渠道结构准备一份 {brief.offer}。"
            )
            linkedin_message = (
                f"{lead['contact_name']}，看到 {lead['company']} 正在推进 {lead['trigger_event']}。"
                f"我们最近帮助类似团队把首触达速度缩短到当天内，"
                f"如果你对 {lead['campaign_angle']} 这类方案感兴趣，我可以发你一个简版案例。"
            )
            call_opener = (
                f"想和你快速确认一下，{lead['company']} 目前在 {lead['pain_hypothesis']} 上，"
                f"是不是也遇到线索优先级难统一的问题？"
            )
            lead_copy.update(
                {
                    "recommended_channels": lead["preferred_channels"][:2] if lead["preferred_channels"] else ["Email", "LinkedIn"],
                    "email_subject": email_subject,
                    "email_body": email_body,
                    "linkedin_message": linkedin_message,
                    "call_opener": call_opener,
                }
            )
            messaged.append(lead_copy)

        summary = f"已生成 {len(messaged)} 组个性化触达内容，覆盖邮件、LinkedIn 和电话开场。"
        return {
            "timeline": {
                "agent": self.name,
                "purpose": self.purpose,
                "summary": summary,
                "highlights": [lead["email_subject"] for lead in messaged[:3]],
            },
            "state_updates": {"messaged_leads": messaged},
        }


class SequenceAgent(BaseAgent):
    name = "Sequence Agent"
    purpose = "制定自动化跟进节奏与任务编排"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        sequenced: list[dict[str, Any]] = []

        for lead in state["messaged_leads"]:
            lead_copy = dict(lead)
            cadence = [
                {"day": "D0", "channel": lead_copy["recommended_channels"][0], "action": "发送首触达信息"},
                {"day": "D2", "channel": "LinkedIn", "action": "补充行业案例并二次触达"},
                {"day": "D5", "channel": "Email", "action": "发送 ROI 场景与演示邀请"},
                {"day": "D8", "channel": "Phone", "action": "电话确认优先级与真实需求"},
                {"day": "D12", "channel": "Email", "action": "发送最后一次温和跟进"},
            ]
            lead_copy["cadence"] = cadence
            sequenced.append(lead_copy)

        summary = f"已为所有目标客户生成 5 步跟进序列，支持自动化执行。"
        return {
            "timeline": {
                "agent": self.name,
                "purpose": self.purpose,
                "summary": summary,
                "highlights": ["D0 首触达", "D2 案例补充", "D8 电话确认"],
            },
            "state_updates": {"sequenced_leads": sequenced},
        }


class OpsManagerAgent(BaseAgent):
    name = "Ops Manager Agent"
    purpose = "汇总结果并给出运营执行建议"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        leads = list(state["sequenced_leads"])
        leads.sort(key=lambda item: item["fit_score"], reverse=True)
        top_leads = leads[:8]
        segment_counter = Counter(lead["segment"] for lead in top_leads)
        top_segment = segment_counter.most_common(1)[0][0] if top_leads else "暂无"

        playbook = {
            "core_strategy": f"优先打 {top_segment} 客群，用“触发事件 + 痛点 + 试用/诊断”三段式话术开局。",
            "execution_focus": [
                "优先联系 P1 客户，保证 24 小时内完成首触达。",
                "邮件与 LinkedIn 双通道协同，避免单一渠道沉默。",
                "第 5 天补充案例与 ROI 结果，提升回复率。",
            ],
            "weekly_kpis": {
                "qualified_leads": len(top_leads),
                "first_touch_sla": "24 小时内",
                "reply_rate_target": "18%+",
                "meeting_booking_target": "6 场/周",
            },
        }

        summary = f"运营经理 Agent 已输出执行剧本，建议优先推进 {len(top_leads)} 条高价值线索。"
        return {
            "timeline": {
                "agent": self.name,
                "purpose": self.purpose,
                "summary": summary,
                "highlights": playbook["execution_focus"],
            },
            "state_updates": {"result_leads": top_leads, "playbook": playbook},
        }
