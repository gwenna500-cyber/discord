from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Medical Bot is running and alive!"

def run():
    # Render assigns a port dynamically via the PORT environment variable
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
