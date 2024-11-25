from flask import Flask, render_template, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler

# Initialize the Flask app
app = Flask(__name__)

# Database setup functions
def setup_database(db_name, table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_data(db_name, table_name, data):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    for item in data:
        cursor.execute(f'''
            INSERT INTO {table_name} (title, url)
            VALUES (?, ?)
        ''', (item['title'], item['url']))
    conn.commit()
    conn.close()

def fetch_data_from_db(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT title, url FROM notifications')
    rows = cursor.fetchall()
    conn.close()
    return [{'title': row[0], 'url': row[1]} for row in rows]

# Set up databases
setup_database('jkpsc_data.db', 'notifications')
setup_database('jkssb_data.db', 'notifications')
setup_database('jkbopee_data.db', 'notifications')

# Scraping functions
def scrape_jkpsc_notifications():
    url = 'https://www.jkpsc.nic.in/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    notifications = []
    for li in soup.select('ul.notificationnews li a[visible="true"]'):
        notifications.append({
            'title': li.text.strip(),
            'url': url + li['href'].strip(),
        })
    insert_data('jkpsc_data.db', 'notifications', notifications)

def scrape_jkssb_notifications():
    base_url = "https://jkssb.nic.in/"
    notifications_url = f"{base_url}Whatsnew.html"
    response = requests.get(notifications_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    notifications = []
    links = soup.find_all('a', class_='linkText')
    for link in links:
        title = link.text.strip()
        relative_link = link.get('href')
        if relative_link:
            absolute_link = urljoin(base_url, relative_link.lstrip('../'))
            notifications.append({"title": title, "url": absolute_link})
    insert_data('jkssb_data.db', 'notifications', notifications)

def scrape_jkbopee_notifications():
    base_url = "https://www.jkbopee.gov.in/"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    notifications = []
    rows = soup.select('div#Div1 table tbody tr')
    for row in rows:
        link = row.find('a', class_='title')
        if link:
            title = link.text.strip()
            relative_link = link.get('href')
            absolute_link = urljoin(base_url, relative_link)
            notifications.append({"title": title, "url": absolute_link})
    insert_data('jkbopee_data.db', 'notifications', notifications)

# Schedule scraping at midnight
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_jkpsc_notifications, 'cron', hour=0, minute=0)
scheduler.add_job(scrape_jkssb_notifications, 'cron', hour=0, minute=0)
scheduler.add_job(scrape_jkbopee_notifications, 'cron', hour=0, minute=0)
scheduler.start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/fetch-notifications')
def fetch_jkpsc_notifications():
    notifications = fetch_data_from_db('jkpsc_data.db')
    return jsonify({'notifications': notifications})

@app.route('/fetch-jkssb-notifications')
def fetch_jkssb_notifications():
    notifications = fetch_data_from_db('jkssb_data.db')
    return jsonify({'notifications': notifications})

@app.route('/fetch-jkbopee-notifications')
def fetch_jkbopee_notifications():
    notifications = fetch_data_from_db('jkbopee_data.db')
    return jsonify({'notifications': notifications})

if __name__ == '__main__':
    app.run(debug=True)
