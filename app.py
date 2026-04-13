from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import json

app = Flask(__name__)

def count_trump_mentions():
    url = "https://www.smh.com.au"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()
        return text.count("trump")
    return 0

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
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({"field": None})

        data = request.get_json()
        note = data.get("note", "").strip()
        person = data.get("person", {})

        if not note:
            return jsonify({"field": None})

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You analyze a personal note about someone and extract any direct profile updates.

Person: {person.get('name', 'Unknown')} ({person.get('rel', '')})
Current profile:
  job: {person.get('job') or 'not set'}
  loves/interests: {person.get('loves') or 'not set'}
  dislikes: {person.get('dislikes') or 'not set'}
  birthday: {person.get('bday') or 'not set'}

Note written about them: "{note}"

If the note clearly states a factual update to this specific person's profile, respond with ONLY valid JSON (no explanation):
{{"field": "job", "value": "Software Engineer", "summary": "new job as Software Engineer"}}

Valid fields: job, loves, dislikes, bday
For "loves" and "dislikes": return the single new item to add, not the whole list.
For "job": return the complete new job title.
For "bday": return the date as written.

Rules:
- Only extract definitive statements ("she's now a...", "just got a job as...", "loves X now")
- Do NOT extract speculation, questions, or things about other people
- If nothing clearly maps to a profile field, respond with ONLY: {{"field": null}}"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(message.content[0].text.strip())
        return jsonify(result)

    except Exception:
        return jsonify({"field": None})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
