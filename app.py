from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Scraper function
def count_trump_mentions():
    url = "https://www.smh.com.au"
    headers = {"User-Agent": "Mozilla/5.0"}  # Avoid getting blocked
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()
        count = text.count("trump")
        return count
    return 0

@app.route("/")
def index():
    mention_count = count_trump_mentions()

    return render_template("index.html", mention_count=mention_count)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
