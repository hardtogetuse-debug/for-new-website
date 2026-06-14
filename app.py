import builtins
import os
import sys
import json
import re
import time
import threading
import requests
from flask import Flask, render_template_string, request, redirect, url_for, session
from jinja2 import DictLoader
from functools import wraps

# =========================================================
# 0. ABSOLUTE GLOBAL ANTI-CRASH INTERCEPTOR 
# =========================================================
class KeyAuthExitBypass(Exception):
    pass

def anti_crash_exit(*args, **kwargs):
    raise KeyAuthExitBypass("Terminal exit sequence blocked safely.")

sys.exit = anti_crash_exit
os._exit = anti_crash_exit
if hasattr(builtins, 'exit'): builtins.exit = anti_crash_exit
if hasattr(builtins, 'quit'): builtins.quit = anti_crash_exit

# =========================================================
# 1. CORE APPLICATION INSTANTIATION & CONFIG
# =========================================================
app = Flask(__name__)
app.secret_key = os.urandom(32)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Simple admin credentials (hardcoded for reliability)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ch1_name": "Main Channel", "ch1_url": "", "ch1_vid": "", "ch1_subs": "0", "ch1_views": "0", "ch1_likes": "0", "ch1_manual_vid": "false",
    "ch2_name": "Second Channel", "ch2_url": "", "ch2_vid": "", "ch2_subs": "0", "ch2_views": "0", "ch2_likes": "0", "ch2_manual_vid": "false",
    "ch3_name": "Third Channel", "ch3_url": "", "ch3_vid": "", "ch3_subs": "0", "ch3_views": "0", "ch3_likes": "0", "ch3_manual_vid": "false",
    "ch4_name": "Fourth Channel", "ch4_url": "", "ch4_vid": "", "ch4_subs": "0", "ch4_views": "0", "ch4_likes": "0", "ch4_manual_vid": "false",
    "ch5_name": "Fifth Channel", "ch5_url": "", "ch5_vid": "", "ch5_subs": "0", "ch5_views": "0", "ch5_likes": "0", "ch5_manual_vid": "false",
    "ch6_name": "Sixth Channel", "ch6_url": "", "ch6_vid": "", "ch6_subs": "0", "ch6_views": "0", "ch6_likes": "0", "ch6_manual_vid": "false",
    "ch7_name": "Seventh Channel", "ch7_url": "", "ch7_vid": "", "ch7_subs": "0", "ch7_views": "0", "ch7_likes": "0", "ch7_manual_vid": "false"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to write configuration file: {e}")

# =========================================================
# SIMPLE YOUTUBE VIDEO FETCHER (NO SUBSCRIBERS)
# =========================================================

def get_channel_latest_video(channel_url):
    """Get the latest video ID from a channel (no subscriber tracking)."""
    if not channel_url:
        return None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        # Try to get the channel's videos page
        videos_url = f"{channel_url.rstrip('/')}/videos"
        response = requests.get(videos_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # Look for video IDs in the page
            patterns = [
                r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"',
                r'/watch\?v=([a-zA-Z0-9_-]{11})',
                r'watch\?v=([a-zA-Z0-9_-]{11})'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html)
                if matches:
                    # Return the first unique video ID
                    for match in matches:
                        if len(match) == 11:
                            return match
        
        # Fallback: try the channel homepage
        response = requests.get(channel_url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            matches = re.findall(r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)
            if matches:
                return matches[0]
                
    except Exception as e:
        print(f"[Video Fetch Error] {e}")
    
    return None

def get_video_stats(video_id):
    """Get view and like count for a video."""
    if not video_id:
        return 0, 0
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    views = 0
    likes = 0
    
    try:
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(watch_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # Get views
            view_patterns = [
                r'"viewCount"\s*:\s*"(\d+)"',
                r'"viewCountText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"',
                r'(\d+(?:,\d+)*)\s+views'
            ]
            for pattern in view_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    raw = re.sub(r'[^\d]', '', match.group(1))
                    if raw:
                        views = int(raw)
                        break
            
            # Get likes
            like_patterns = [
                r'"likeCount"\s*:\s*"(\d+)"',
                r'"likeCountText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"',
                r'(\d+(?:,\d+)*)\s+likes'
            ]
            for pattern in like_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    raw = re.sub(r'[^\d]', '', match.group(1))
                    if raw:
                        likes = int(raw)
                        break
                        
    except Exception as e:
        print(f"[Video Stats Error] {e}")
    
    return views, likes

def process_single_channel(config, i):
    """Process a single channel - get video and stats only."""
    channel_url = config.get(f"ch{i}_url", "")
    if not channel_url or "youtube.com" not in channel_url.lower():
        return False
    
    is_config_altered = False
    
    # Get latest video if not manually overridden
    manual_override = config.get(f"ch{i}_manual_vid") == "true"
    if not manual_override:
        latest_video = get_channel_latest_video(channel_url)
        if latest_video and latest_video != config.get(f"ch{i}_vid", ""):
            config[f"ch{i}_vid"] = latest_video
            is_config_altered = True
    
    # Get video stats for the current video
    current_vid = config.get(f"ch{i}_vid", "")
    if current_vid:
        video_views, video_likes = get_video_stats(current_vid)
        
        if video_views > 0:
            formatted_views = f"{video_views:,}"
            if config.get(f"ch{i}_views", "0") != formatted_views:
                config[f"ch{i}_views"] = formatted_views
                is_config_altered = True
        
        if video_likes > 0:
            formatted_likes = f"{video_likes:,}"
            if config.get(f"ch{i}_likes", "0") != formatted_likes:
                config[f"ch{i}_likes"] = formatted_likes
                is_config_altered = True
    
    return is_config_altered

def youtube_monitor_worker():
    """Background worker that updates video stats."""
    print("[SYSTEM] Video stats tracker activated.")
    
    while True:
        try:
            config = load_config()
            is_config_altered = False
            
            for i in range(1, 8):
                try:
                    if process_single_channel(config, i):
                        is_config_altered = True
                    time.sleep(0.5)
                except Exception as channel_error:
                    print(f"[ERROR] Channel {i}: {channel_error}")
            
            if is_config_altered:
                save_config(config)
                print(f"[SYSTEM] Video stats updated")
                
        except Exception as system_error:
            print(f"[CRITICAL] Worker error: {system_error}")
        
        # Update every 2 minutes (less frequent to avoid rate limiting)
        time.sleep(120)

# Start background worker
worker_thread_started = False

def start_worker():
    global worker_thread_started
    if not worker_thread_started:
        worker_thread_started = True
        thread = threading.Thread(target=youtube_monitor_worker, daemon=True)
        thread.start()
        print("[SYSTEM] Background worker started")

# =========================================================
# 2. UI LAYOUT WITH PARTICLE EFFECTS (NO SUBSCRIBER DISPLAY)
# =========================================================
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>YouTube Channel Dashboard</title>
    <style>
        @keyframes fadeInUp {
            0% { opacity: 0; transform: translateY(20px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        html, body { margin: 0; padding: 0; width: 100%; min-height: 100%; background-color: #060607; }
        body { font-family: 'Segoe UI', Arial, sans-serif; color: #e4e4e7; text-align: center; padding: 40px 20px; box-sizing: border-box; position: relative; }
        #particles-canvas-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none; }
        .container { position: relative; z-index: 5; max-width: 1400px; margin: auto; background: rgba(18, 18, 20, 0.93); padding: 40px 20px; border-radius: 16px; border: 1px solid #1f1f23; box-shadow: 0 20px 50px rgba(0,0,0,0.8); overflow: hidden; }
        #particles-canvas-fg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none; }
        .container > *:not(#particles-canvas-fg) { position: relative; z-index: 2; }
        h1 { color: #ffffff; font-size: 2.7rem; margin-bottom: 5px; letter-spacing: -0.5px; }
        .credits { color: #dc2626; font-weight: bold; font-size: 1.1rem; letter-spacing: 2px; margin-bottom: 30px; text-transform: uppercase; text-shadow: 0 0 10px rgba(220, 38, 38, 0.4); }
        .channel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; margin: 30px 0; }
        .channel-card { background: #18181b; border: 1px solid #27272a; border-radius: 14px; padding: 18px; transition: all 0.3s; animation: fadeInUp 0.6s ease-out both; }
        .channel-card:hover { transform: translateY(-6px); border-color: #dc2626; box-shadow: 0 12px 24px rgba(220, 38, 38, 0.2); }
        .channel-name { font-size: 1.25rem; font-weight: 600; margin-bottom: 15px; display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; }
        .video-container { position: relative; padding-bottom: 56.25%; height: 0; border-radius: 8px; border: 1px solid #27272a; margin-bottom: 15px; background: #0b0b0c; }
        .video-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
        .video-placeholder { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #0b0b0c; color: #71717a; flex-direction: column; gap: 10px; }
        .stats-badge-container { display: flex; justify-content: space-around; background: #0b0b0c; padding: 12px 6px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #1f1f23; }
        .stat-item { text-align: center; flex: 1; }
        .stat-val { display: block; color: #ffffff; font-weight: 700; font-size: 1rem; }
        .stat-lbl { color: #71717a; font-size: 0.7rem; text-transform: uppercase; font-weight: 500; }
        .btn { display: inline-block; background: #dc2626; color: #ffffff; padding: 11px 20px; border: none; border-radius: 8px; cursor: pointer; text-decoration: none; font-weight: 600; transition: all 0.2s ease; width: 100%; box-sizing: border-box; text-align: center; }
        .btn:hover { background: #ef4444; transform: scale(0.98); }
        .btn-secondary { background: #27272a; width: auto; padding: 6px 16px; }
        .footer { margin-top: 50px; border-top: 1px solid #27272a; padding-top: 20px; }
        .last-updated { color: #71717a; font-size: 0.8rem; margin-bottom: 20px; }
        .alert { background: rgba(220, 38, 38, 0.2); border: 1px solid #dc2626; color: #fca5a5; padding: 14px; border-radius: 6px; margin-bottom: 25px; }
        .form-group { margin-bottom: 15px; text-align: left; }
        label { display: block; margin-bottom: 6px; color: #d4d4d8; }
        input { width: 100%; padding: 10px; background: #0b0b0c; border: 1px solid #3f3f46; color: #fff; border-radius: 6px; }
        .admin-section { background: #18181b; border: 1px solid #27272a; padding: 20px; border-radius: 8px; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
    </style>
</head>
<body>
    <canvas id="particles-canvas-bg"></canvas>
    <div class="container">
        <canvas id="particles-canvas-fg"></canvas>
        {% block content %}{% endblock %}
    </div>
    <script>
        (function() {
            class MicroParticle {
                constructor(canvas) {
                    this.canvas = canvas;
                    this.size = Math.random() * 2.6 + 0.6;
                    this.x = Math.random() * (canvas.width - this.size * 2) + this.size;
                    this.y = Math.random() * (canvas.height - this.size * 2) + this.size;
                    this.speedX = (Math.random() * 1.6) - 0.8; 
                    this.speedY = (Math.random() * 1.6) - 0.8; 
                    this.opacity = Math.random() * 0.6 + 0.25;
                }
                update() {
                    this.x += this.speedX;
                    this.y += this.speedY;
                    if (this.x - this.size <= 0) { this.x = this.size; this.speedX *= -1; }
                    else if (this.x + this.size >= this.canvas.width) { this.x = this.canvas.width - this.size; this.speedX *= -1; }
                    if (this.y - this.size <= 0) { this.y = this.size; this.speedY *= -1; }
                    else if (this.y + this.size >= this.canvas.height) { this.y = this.canvas.height - this.size; this.speedY *= -1; }
                }
                draw(ctx) { ctx.beginPath(); ctx.fillStyle = `rgba(220, 38, 38, ${this.opacity})`; ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fill(); }
            }
            function setupParticleSystem(canvasId, densityDivider, absoluteMax) {
                const canvas = document.getElementById(canvasId);
                if (!canvas) return null;
                const ctx = canvas.getContext('2d');
                let particlesArray = [];
                function resize() {
                    if (canvasId === 'particles-canvas-bg') { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
                    else { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; }
                    populate();
                }
                function populate() {
                    particlesArray = [];
                    const count = Math.min(Math.floor(canvas.width / densityDivider), absoluteMax);
                    for (let i = 0; i < count; i++) particlesArray.push(new MicroParticle(canvas));
                }
                window.addEventListener('resize', resize);
                resize();
                return { renderFrame: function() { ctx.clearRect(0, 0, canvas.width, canvas.height); for (let i = 0; i < particlesArray.length; i++) { particlesArray[i].update(); particlesArray[i].draw(ctx); } } };
            }
            const outsideSystem = setupParticleSystem('particles-canvas-bg', 2.5, 450);
            const insideSystem = setupParticleSystem('particles-canvas-fg', 2.5, 350);
            function executionLoop() { if (outsideSystem) outsideSystem.renderFrame(); if (insideSystem) insideSystem.renderFrame(); requestAnimationFrame(executionLoop); }
            executionLoop();
        })();
    </script>
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>🎬 Our YouTube Channel</h1>
    <div class="credits">Developed by HARSHITH</div>
    <div class="last-updated">🔄 Auto-updates every 2 minutes</div>
    <div class="channel-grid">
        {% for i in ['1', '2', '3', '4', '5', '6', '7'] %}
        {% set ch_url = config.get('ch' ~ i ~ '_url', '') %}
        {% if ch_url and ch_url|string|trim != "" %}
        {% set ch_name = config.get('ch' ~ i ~ '_name', 'YouTube Channel') %}
        <div class="channel-card">
            <div class="channel-name">{{ ch_name }}</div>
            <div class="video-container">
                {% set video_id = config.get('ch' ~ i ~ '_vid', '') %}
                {% if video_id and video_id|length == 11 %}
                    <iframe src="https://www.youtube.com/embed/{{ video_id }}?autoplay=0&modestbranding=1&rel=0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                {% else %}
                    <div class="video-placeholder"><span>📹</span><span>Loading video...</span></div>
                {% endif %}
            </div>
            <div class="stats-badge-container">
                <div class="stat-item"><span class="stat-val">{{ config.get('ch' ~ i ~ '_views', '0') }}</span><span class="stat-lbl">VIEWS</span></div>
                <div class="stat-item"><span class="stat-val">{{ config.get('ch' ~ i ~ '_likes', '0') }}</span><span class="stat-lbl">LIKES</span></div>
            </div>
            <a href="{{ ch_url }}" target="_blank" class="btn">▶ Visit Channel</a>
        </div>
        {% endif %}
        {% endfor %}
    </div>
    <div class="footer"><a href="{{ url_for('login') }}" class="btn btn-secondary">🔒 Admin Access</a></div>
{% endblock %}
"""

LOGIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h2>🔐 Admin Verification</h2>
    <div class="credits">System Security Console</div>
    {% if error %}<div class="alert">⚠️ {{ error }}</div>{% endif %}
    <form method="POST" style="max-width: 450px; margin: 0 auto;">
        <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
        <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
        <button type="submit" class="btn" style="width: 100%;">Authenticate</button>
    </form>
    <p style="margin-top: 20px;"><a href="{{ url_for('index') }}" style="color: #a1a1aa;">← Return Home</a></p>
{% endblock %}
"""

ADMIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h2>⚙️ Dashboard Control Panel</h2>
    <div class="credits">Channel Management</div>
    <form method="POST">
        <div class="form-grid">
            {% for i in ['1', '2', '3', '4', '5', '6', '7'] %}
            <div class="admin-section">
                <h4>Channel {{ i }}</h4>
                <div class="form-group"><label>Display Name</label><input type="text" name="ch{{ i }}_name" value="{{ config.get('ch' ~ i ~ '_name', '') }}"></div>
                <div class="form-group"><label>YouTube URL</label><input type="text" name="ch{{ i }}_url" value="{{ config.get('ch' ~ i ~ '_url', '') }}" placeholder="https://youtube.com/@channel"></div>
                <div class="form-group"><label>Manual Video ID (Optional)</label><input type="text" name="ch{{ i }}_vid" value="{{ config.get('ch' ~ i ~ '_vid', '') }}" placeholder="11-character ID"></div>
            </div>
            {% endfor %}
        </div>
        <button type="submit" class="btn" style="background: #16a34a; margin-top: 20px;">💾 Save All Changes</button>
    </form>
    <div class="footer"><a href="{{ url_for('logout') }}" class="btn btn-secondary">🚪 Logout</a></div>
{% endblock %}
"""

app.jinja_loader = DictLoader({'base': BASE_LAYOUT})

# =========================================================
# 3. ROUTING & CONTROLLERS
# =========================================================
@app.route('/')
def index():
    current_config = load_config()
    return render_template_string(INDEX_TEMPLATE, config=current_config)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_authed'):
        return redirect(url_for('admin'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple hardcoded admin check (reliable)
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_authed'] = True
            session.permanent = True
            return redirect(url_for('admin'))
        else:
            error = "don't try u mother fucker"
    
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_authed'):
        return redirect(url_for('login'))
    
    current_config = load_config()
    if request.method == 'POST':
        for idx in range(1, 8):
            current_config[f'ch{idx}_name'] = request.form.get(f'ch{idx}_name', '').strip()
            current_config[f'ch{idx}_url'] = request.form.get(f'ch{idx}_url', '').strip()
            
            vid_input = request.form.get(f'ch{idx}_vid', '').strip()
            current_config[f'ch{idx}_vid'] = vid_input
            current_config[f'ch{idx}_manual_vid'] = "true" if vid_input else "false"
            
            if not current_config[f'ch{idx}_url']:
                current_config[f'ch{idx}_views'] = "0"
                current_config[f'ch{idx}_likes'] = "0"
                current_config[f'ch{idx}_vid'] = ""
                current_config[f'ch{idx}_manual_vid'] = "false"
        
        save_config(current_config)
        return redirect(url_for('index'))
    
    return render_template_string(ADMIN_TEMPLATE, config=current_config)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Start background worker
start_worker()

# This is the WSGI application that Render needs
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
