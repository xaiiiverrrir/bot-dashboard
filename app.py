import os
import urllib.parse as urlparse
import psycopg2
from flask import Flask, render_template_string, jsonify, request, redirect, url_for

app = Flask(__name__)

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return None
    try:
        # Parse the URL explicitly to avoid any DSN formatting errors with psycopg2
        url = urlparse.urlparse(database_url.strip().strip('"').strip("'"))
        conn = psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            sslmode='require'
        )
        return conn
    except Exception as e:
        print(f"Connection error: {e}")
        return None
