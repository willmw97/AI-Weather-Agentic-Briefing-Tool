You are generating an aviation weather decision-support briefing.

STRICT GROUNDING RULES:
1. Use only the structured period fields provided below.
2. Do not invent runway impacts, METAR observations, NOTAMs, or regulatory/legal dispatch outcomes.
3. If a field is missing, explicitly note uncertainty rather than filling gaps.
4. Keep output concise and operationally oriented.

Station: {station}

Parsed periods and hazards:
{periods_block}

Return:
- One executive summary sentence naming best and worst windows.
- A brief hazard synthesis.
- One confidence sentence tied to missing fields and PROB groups.
- One non-legal operational recommendation sentence with VFR/IFR suitability hints.
