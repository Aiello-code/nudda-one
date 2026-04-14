from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import json

app = Flask(__name__)

# Cache client at startup — avoid re-instantiating on every request
_claude_client = None
def get_claude_client():
    global _claude_client
    if _claude_client is not None:
        return _claude_client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    import anthropic
    _claude_client = anthropic.Anthropic(api_key=api_key)
    return _claude_client

def count_trump_mentions():
    try:
        url = "https://www.smh.com.au"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text().lower()
            return text.count("trump")
    except Exception:
        pass
    return 0

@app.route("/ping")
def ping():
    return jsonify({"ok": True})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/trump")
def trump():
    mention_count = count_trump_mentions()
    return render_template("trump.html", mention_count=mention_count)

@app.route("/property")
def property_check():
    return render_template("property.html")

@app.route("/heartstring")
def heartstring():
    return render_template("heartstring.html")

@app.route("/api/analyze-note", methods=["POST"])
def analyze_note():
    try:
        client = get_claude_client()
        if not client:
            return jsonify({"field": None})

        data = request.get_json()
        note = data.get("note", "").strip()
        person = data.get("person", {})
        if not note:
            return jsonify({"field": None})

        prompt = f"""Analyze this note about {person.get('name', 'someone')} and extract ALL profile updates mentioned.

Current profile:
  job: {person.get('job') or 'not set'}
  loves/interests: {person.get('loves') or 'not set'}
  dislikes: {person.get('dislikes') or 'not set'}
  birthday: {person.get('bday') or 'not set'}

Note: "{note}"

Extract every definitive factual update to THIS person's profile. Respond with ONLY valid JSON:
{{"updates": [{{"field": "job", "value": "Lawyer", "summary": "started working as a Lawyer"}}, {{"field": "loves", "value": "hiking", "summary": "loves hiking"}}]}}

Valid fields: job, loves, dislikes, bday
For loves/dislikes: return just the single new item to add (one entry per item).
For job: return the complete new title.
For bday: return in format like "March 5" or "1990-03-05".
If nothing clearly maps to a profile field, respond with ONLY: {{"updates": []}}
Only extract definitive statements, not guesses or things about other people."""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            timeout=12.0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        parsed = json.loads(raw)
        if 'updates' in parsed:
            return jsonify(parsed)
        elif parsed.get('field'):
            return jsonify({"updates": [{"field": parsed['field'], "value": parsed['value'], "summary": parsed.get('summary','')}]})
        else:
            return jsonify({"updates": []})
    except Exception:
        return jsonify({"updates": []})

@app.route("/api/generate-insights", methods=["POST"])
def generate_insights():
    try:
        client = get_claude_client()
        if not client:
            return jsonify({"error": "no key"})

        data = request.get_json()
        people_data = data.get("people", [])

        context_parts = []
        for p in people_data:
            notes = [n["text"] for n in p.get("recentNotes", [])[:4]]
            events = [e["name"] + " on " + e["date"] for e in p.get("events", [])]
            context_parts.append(
                f"\n{p['name']} ({p['rel']}):"
                f"\n  Job: {p.get('job') or 'unknown'}"
                f"\n  Loves: {p.get('loves') or 'unknown'}"
                f"\n  Dislikes: {p.get('dislikes') or 'unknown'}"
                f"\n  Upcoming: {', '.join(events) or 'none'}"
                f"\n  Recent notes: {'; '.join(notes) or 'none'}"
            )

        prompt = f"""You help someone maintain meaningful relationships. Generate personalised insights based on what they know about these people.

Circle:{''.join(context_parts)}

Respond ONLY with valid JSON in exactly this format:
{{
  "reflection": {{"person": "Name", "text": "A warm, specific, actionable 1-2 sentence reflection about one person, referencing something concrete from their notes or upcoming events."}},
  "questions": [
    {{"person": "Name", "items": ["specific question 1", "specific question 2", "specific question 3"]}}
  ]
}}

Rules:
- One reflection total, pick the most interesting person/situation
- One entry in questions per person
- Questions must be specific to their actual situation, not generic
- Tone: warm, caring, like a thoughtful friend"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            timeout=20.0,
            messages=[{"role": "user", "content": prompt}]
        )
        result = json.loads(message.content[0].text.strip())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
