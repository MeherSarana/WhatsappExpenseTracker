# --- GPT categorizer helpers (drop into routes/dashboard.py) ---
import os, json
from typing import List, Dict, Any, Tuple
from openai import AsyncOpenAI
from import_env import *

ALLOWED_CATS = [
    "Fruits", "Groceries", "Restaurant Food", "Raw Meat & Seafood",
    "Snacks", "Beverages", "Fashion Accessories", "Home Appliances",
    "Electronics", "Transport", "Entertainment", "Others"
]

# single client (reuse)
_oai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _items_for_llm(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # keep only what the model needs
    out: List[Dict[str, Any]] = []
    for r in rows:  # for-loop (your preference)
        name = (r.get("item_name") or "").strip()
        amt = int(r.get("amount") or 0)
        if not name:
            continue
        out.append({"item_name": name, "amount": amt})
    return out

def _mk_prompt(items: List[Dict[str, Any]]) -> str:
    # concise but strict; we demand a JSON object with category totals
    return f"""
You are an expense categorizer. Map each (item_name, amount) to one of these categories:
{ALLOWED_CATS}.

Rules:
- Understand real-world dishes (e.g., "Chicken 65" → "Restaurant Food").
- "Raw Meat & Seafood" is only for uncooked meat/fish/poultry.
- Fruits/Vegetables into "Fruits" or "Groceries" based on common sense.
- If unsure, use "Others".

Input JSON (list):
{json.dumps(items, ensure_ascii=False)}

Output JSON (object) EXACTLY in this schema:
{{
  "categories": [
    {{"category": "<one of allowed>", "total_amount": <int>}}
  ]
}}
No extra text, no markdown, only JSON.
""".strip()

async def gpt_category_totals(rows: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
    items = _items_for_llm(rows)
    if not items:
        return []

    prompt = _mk_prompt(items)

    resp = await _oai_client.chat.completions.create(
        model="gpt-5-nano",  # or the model you use in the project
        temperature=1,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content.strip()

    # Parse safe JSON
    try:
        obj = json.loads(raw)
        cat_list = obj.get("categories", []) or []
        out: List[Tuple[str, int]] = []
        for c in cat_list:  # for-loop
            cat = str(c.get("category") or "Others").strip()
            amt = int(c.get("total_amount") or 0)
            out.append((cat, amt))
        # sort high → low
        out.sort(key=lambda x: x[1], reverse=True)
        return out
    except Exception:
        # Fallback: local simple sum into Others
        total = sum(int(x["amount"]) for x in items)
        return [("Others", total)]

def make_markdown_table(cat_list: List[Tuple[str, int]]) -> str:
    # return a markdown table string
    if not cat_list:
        return "*(no categories)*"
    lines = ["| Category | Amount |", "|---|---:|"]
    for name, amt in cat_list:  # for-loop
        lines.append(f"| {name} | ₹{amt} |")
    return "\n".join(lines)
