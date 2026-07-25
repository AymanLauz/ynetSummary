# ynetSummary

An agent that scrapes the top headlines from [Ynet](https://www.ynet.co.il/), summarizes each article into 5 Hebrew bullet points using a locally-hosted LLM (via [LM Studio](https://lmstudio.ai/)), and generates a styled RTL HTML daily briefing.

## How it works

1. Scrapes the Ynet homepage for links to the latest articles.
2. Downloads and parses the full text of each article.
3. Sends each article to a local LLM (served through LM Studio's OpenAI-compatible API) with a prompt to summarize it in 5 Hebrew bullet points.
4. Renders all summaries into a single HTML report (`daily_briefing.html`) with headlines, summaries, and links back to the original articles.

An example output is included: [`daily_briefing.html`](daily_briefing.html) — [view it live](https://aymanlauz.github.io/ynetSummary/daily_briefing.html).

## Setup

1. Install [LM Studio](https://lmstudio.ai/), load a model, and start the local server (default: `http://localhost:1234/v1`).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python main.py
   ```

## Notes

This project was built for personal use to generate a quick daily news digest. It scrapes and summarizes copyrighted news content — intended for personal/educational use only, not redistribution.
