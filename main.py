import requests
from bs4 import BeautifulSoup
from newspaper import Article
from openai import OpenAI
import os
import time
import sys
import threading
import itertools

# --- CONFIGURATION ---
LM_STUDIO_URL = "http://localhost:1234/v1"
URL_TO_SCRAPE = "https://www.ynet.co.il/"

# CONTROL HOW MANY ARTICLES TO SCRAPE HERE
NUM_ARTICLES = 10

# --- THE SETUP ---
client = OpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio")


# --- SPINNER ANIMATION ---
def spinner_animation(event, message="Processing"):
	spinner = itertools.cycle(['-', '/', '|', '\\'])
	while not event.is_set():
		sys.stdout.write(f'\r{message} {next(spinner)}')
		sys.stdout.flush()
		time.sleep(0.1)
	sys.stdout.write('\r')


def get_active_model_name():
	try:
		models = client.models.list()
		if not models.data:
			print("\n❌ ERROR: LM Studio is running, but NO model is loaded.")
			print("   Please open your terminal and run: lms load <your-model-name>")
			sys.exit(1)
		
		model_id = models.data[0].id
		print(f"✅ Success! Connected to model: {model_id}")
		return model_id
	except Exception as e:
		print(f"\n❌ Connection Error: {e}")
		sys.exit(1)


MODEL_NAME = get_active_model_name()


def get_ynet_links(limit=10):
	print(f"\nScanning {URL_TO_SCRAPE} for top stories...")
	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
	
	try:
		response = requests.get(URL_TO_SCRAPE, headers=headers)
		soup = BeautifulSoup(response.content, 'html.parser')
		valid_links = []
		for a_tag in soup.find_all('a', href=True):
			href = a_tag['href']
			if '/articles/' in href or '/news/article/' in href:
				if not href.startswith('http'):
					href = f"https://www.ynet.co.il{href}"
				if href not in valid_links:
					valid_links.append(href)
			if len(valid_links) >= limit:
				break
		print(f"Found {len(valid_links)} articles.")
		return valid_links
	except Exception as e:
		print(f"Error scraping Ynet: {e}")
		return []


def get_article_content(url):
	try:
		article = Article(url)
		article.download()
		article.parse()
		return {'title': article.title, 'text': article.text, 'url': url}
	except Exception:
		return None


def summarize_with_local_ai(text):
	# FIXED: Reduced to 1200 to fit inside the 2048 token limit
	truncated_text = text[:1200]
	
	system_prompt = (
		"You are a helpful news assistant. "
		"Summarize the Hebrew text provided by the user into exactly 5 concise bullet points in Hebrew. "
		"Do not use English. Output only the bullet points."
	)
	
	stop_spinner = threading.Event()
	spinner_thread = threading.Thread(target=spinner_animation, args=(stop_spinner, "  -> AI is thinking"))
	spinner_thread.start()
	
	try:
		start_time = time.time()
		completion = client.chat.completions.create(
			model=MODEL_NAME,
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": truncated_text}
			],
			temperature=0.3,
			max_tokens=250,
			timeout=120
		)
		duration = time.time() - start_time
		stop_spinner.set()
		spinner_thread.join()
		
		print(f"  -> Done! ({duration:.1f}s)")
		return completion.choices[0].message.content
	
	except Exception as e:
		stop_spinner.set()
		spinner_thread.join()
		return f"Error from AI: {e}"


def generate_html_report(news_items):
	html_template = """
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Briefing - Ynet Machine</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ text-align: center; color: #cc0000; border-bottom: 2px solid #cc0000; padding-bottom: 10px; }}
            .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; overflow: hidden; }}
            .card-content {{ padding: 20px; }}
            .headline {{ font-size: 1.4em; font-weight: bold; margin-bottom: 10px; color: #222; }}
            .summary {{ background: #f9f9f9; padding: 15px; border-radius: 5px; line-height: 1.6; }}
            .link {{ display: block; margin-top: 15px; text-align: left; color: #0066cc; text-decoration: none; font-weight: bold; }}
            .timestamp {{ text-align: center; color: #888; margin-top: 40px; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>כותרות היום המובילות מתומצתות כל אחת בכמה נקודות.</h1>
        <p style="text-align:center;">סיכום זה נוצר על ידי מודל שפה לוקאלי ({model_name}) </p>
        {content}
        <div class="timestamp">Generated on {date}</div>
    </body>
    </html>
    """
	
	articles_html = ""
	for item in news_items:
		summary_html = item['summary'].replace('\n', '<br>')
		articles_html += f"""
        <div class="card">
            <div class="card-content">
                <div class="headline">{item['title']}</div>
                <div class="summary">{summary_html}</div>
                <a href="{item['url']}" target="_blank" class="link">למאמר המלא</a>
            </div>
        </div>
        """
	
	final_html = html_template.format(
		content=articles_html,
		date=time.strftime("%d/%m/%Y %H:%M"),
		model_name=MODEL_NAME
	)
	
	with open("daily_briefing.html", "w", encoding="utf-8") as f:
		f.write(final_html)
	print("\nSUCCESS! Open 'daily_briefing.html' to read your news.")


if __name__ == "__main__":
	links = get_ynet_links(limit=NUM_ARTICLES)
	news_data = []
	
	for i, link in enumerate(links):
		print(f"\n[{i + 1}/{len(links)}] Processing: {link}")
		content = get_article_content(link)
		
		if content and len(content['text']) > 100:
			summary = summarize_with_local_ai(content['text'])
			content['summary'] = summary
			news_data.append(content)
		else:
			print("  -> Skipped")
	
	if news_data:
		generate_html_report(news_data)
	else:
		print("No articles processed.")