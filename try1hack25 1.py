import os
import re
import json
import math
import time
import pandas as pd
from typing import List, Dict, Any
import openai

openai.api_key = os.getenv("sk-proj-REDACTED")  # set this in your environment
anthropic_api_key = os.getenv("Sk-ant-api03-AF3SDrKxY2axueMBgcs3xYq_16C70M91rv7DtpScKSo90nBiAbREY2Bo5U65H7h-4TST9CIkl_UKPPABZhjdFg-Tju68wAA ")
# for Anthropic models

# Utility: safely parse JSON the model returns (strip code fences, trailing text)
def safe_json_parse(text: str):
    text = text.strip()
    # strip markdown code fences if present
    if text.startswith("```"):
        # remove leading/trailing ``` and optional language
        parts = text.split("```")
        # find first non-empty JSON-like part
        for p in parts[1:]:
            candidate = p.strip()
            if candidate:
                # if there's a language marker, remove the first line
                if candidate.splitlines()[0].startswith(("json", "json\n")):
                    candidate = "\n".join(candidate.splitlines()[1:])
                try:
                    return json.loads(candidate)
                except Exception:
                    continue
    # fallback: try to find first {...} or [...]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            pass
    # last resort: try entire text
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Unable to parse JSON from model output: {e}\n---raw output---\n{text[:2000]}")

class SurveyRuleExtractor:
    def __init__(self, model="gpt-4", temperature=0.2, max_retries=3, backoff=1.5):
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.backoff = backoff

    def _send_chat(self, messages: List[Dict[str, str]]) -> str:
        # Wrapper for the OpenAI ChatCompletion call. Adjust if you use a different client.
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=2000
                )
                # modern response shape: choices[0].message.content
                return resp.choices[0].message["content"]
            except Exception as e:
                if attempt == self.max_retries:
                    raise
                sleep = (self.backoff ** attempt)
                time.sleep(sleep)

    def _build_prompt(self, responses: List[str], question: str):
        # Keep prompt tight and request explicit JSON format
        sample_lines = "\n".join(f"- {r}" for r in responses[:200])  # limit items; we batch anyway
        prompt = f"""
Analyze these free-text responses to the survey question: "{question}"

Responses:
{sample_lines}

Please provide output as a single JSON object with keys:
- themes: array of 3-8 short theme strings (common phrases that appear)
- categories: array of category objects with fields: name (string), description (1 sentence)
- rules: array of rule objects for the categories. Each rule object should have: category (name), examples (list of short example phrases that indicate this category), keywords (list of short keywords/phrases), pattern (optional regex string that would match this category)
- insights: short bullet list or sentence of high-level takeaways

Important:
- Return only valid JSON (no surrounding commentary). If you must, you can return code fence with json, but the content must parse as JSON.
- Keep categories mutually exclusive if possible.
"""
        return prompt

    def extract_for_question(self, responses: List[str], question: str, batch_size=80):
        """Process responses in batches and return aggregated JSON rules for the question."""
        all_rules = []
        all_themes = []
        all_insights = []

        # chunking simple by count; you may want to chunk by tokens in heavy cases
        for i in range(0, len(responses), batch_size):
            batch = responses[i:i+batch_size]
            prompt = self._build_prompt(batch, question)
            messages = [
                {"role": "system", "content": "You are a qualitative research expert. Extract themes, categories and deterministic classification rules."},
                {"role": "user", "content": prompt}
            ]
            raw = self._send_chat(messages)
            try:
                parsed = safe_json_parse(raw)
            except ValueError as e:
                # best-effort: try asking the model to return JUST the JSON
                # but here we'll fail loudly so the user can inspect response
                raise

            # collect
            if "rules" in parsed:
                all_rules.append(parsed["rules"])
            if "themes" in parsed:
                all_themes.append(parsed["themes"])
            if "insights" in parsed:
                all_insights.append(parsed["insights"])

        # Aggregate rules across batches into consolidated ruleset
        consolidated = self._consolidate_rules(all_rules, all_themes, all_insights)
        return consolidated

    def _consolidate_rules(self, rules_batches, themes_batches, insights_batches):
        # rules_batches is list of lists-of-rule-objects
        cat_map = {}  # name -> {examples:set, keywords:set, patterns:set, descriptions:set}
        for batch in rules_batches:
            for r in batch:
                cat = r.get("category") or r.get("name")
                if not cat:
                    continue
                entry = cat_map.setdefault(cat, {"examples": set(), "keywords": set(), "patterns": set(), "descriptions": set()})
                for ex in r.get("examples", []):
                    entry["examples"].add(ex.strip())
                for kw in r.get("keywords", []):
                    entry["keywords"].add(kw.strip().lower())
                pat = r.get("pattern")
                if pat:
                    entry["patterns"].add(pat)
                desc = r.get("description") or r.get("desc") or r.get("explanation")
                if desc:
                    entry["descriptions"].add(desc.strip())
        # build final rules list
        final_rules = []
        for name, v in cat_map.items():
            # produce a combined keyword set and a safe regex
            keywords = sorted(v["keywords"])
            # build a regex that matches any keyword as whole words (escape them)
            if keywords:
                ors = "|".join(re.escape(k) for k in keywords if k)
                regex = rf"(?i)\b({ors})\b"
            else:
                # try to use examples to create loose patterns
                exs = list(v["examples"])[:5]
                if exs:
                    ors = "|".join(re.escape(e) for e in exs)
                    regex = rf"(?i)({ors})"
                else:
                    regex = None
            final_rules.append({
                "category": name,
                "description": list(v["descriptions"])[0] if v["descriptions"] else "",
                "keywords": keywords,
                "pattern": regex,
                "examples": list(v["examples"])[:10]
            })
        return {
            "themes": sum(themes_batches, []),
            "insights": sum(insights_batches, []),
            "rules": final_rules
        }

    def build_classifier(self, consolidated_rules):
        """Compile regexes for fast classification. Returns list of (category, compiled_regex)."""
        compiled = []
        for r in consolidated_rules["rules"]:
            if r["pattern"]:
                try:
                    compiled.append((r["category"], re.compile(r["pattern"], flags=re.IGNORECASE)))
                except re.error:
                    # pattern invalid; fallback to join keywords
                    kws = r.get("keywords", [])
                    if kws:
                        ors = "|".join(re.escape(k) for k in kws)
                        compiled.append((r["category"], re.compile(rf"(?i)\b({ors})\b")))
            else:
                kws = r.get("keywords", [])
                if kws:
                    ors = "|".join(re.escape(k) for k in kws)
                    compiled.append((r["category"], re.compile(rf"(?i)\b({ors})\b")))
        return compiled

    def classify_text(self, text: str, classifiers) -> Dict[str, Any]:
        """Apply classifiers list[(category, compiled_re)] to a single text. Returns best match + confidence."""
        text = text or ""
        matches = []
        for cat, cre in classifiers:
            if cre.search(text):
                # simple confidence heuristic: more keyword matches -> higher confidence
                matches.append(cat)
        if not matches:
            return {"category": None, "confidence": 0.0}
        # if multiple matches, pick first (or you can compute scores)
        return {"category": matches[0], "confidence": 0.9}

    # optional: fallback to model classification for a batch of uncovered responses
    def classify_with_model(self, responses: List[str], question: str, rules: Dict[str, Any]):
        prompt = (
            f"Using these rules (JSON):\n{json.dumps(rules, indent=2)}\n\n"
            f"Categorize the following responses to the question: {question}\n\n"
            + "\n".join(f"{i+1}. {r}" for i, r in enumerate(responses))
            + "\n\nReturn JSON array of {{response_index, category, confidence}}"
        )
        messages = [
            {"role": "system", "content": "You are a classification expert; apply the rules precisely."},
            {"role": "user", "content": prompt}
        ]
        raw = self._send_chat(messages)
        parsed = safe_json_parse(raw)
        return parsed
