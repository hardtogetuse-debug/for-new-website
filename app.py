import builtins
import os
import sys
import json
import re
import time
import threading
import requests
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from jinja2 import DictLoader
from functools import wraps
from datetime import datetime, timedelta

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
# 1. CORE APPLICATION
# =========================================================
app = Flask(__name__)
app.secret_key = os.urandom(32)

CONFIG_FILE = "config.json"

# =========================================================
# KEYAUTH INTEGRATION
# =========================================================
try:
    from keyauth import api as keyauth_api
    KEYAUTH_AVAILABLE = True
except ImportError:
    KEYAUTH_AVAILABLE = False

APP_NAME = "CRZ FREE PANEL"
OWNER_ID = "EckNXwLHE7"
VERSION = "1.0"

keyauthapp = None
if KEYAUTH_AVAILABLE:
    try:
        keyauthapp = keyauth_api(name=APP_NAME, ownerid=OWNER_ID, version=VERSION, hash_to_check="")
        print("[SYSTEM] KeyAuth initialized")
    except:
        KEYAUTH_AVAILABLE = False

# =========================================================
# YOUR YOUTUBE API KEY
# =========================================================
YOUTUBE_API_KEY = "AIzaSyA7II2iMBSzpHnjsU9zlK6srzOrS-CZGqQ"

# =========================================================
# DEFAULT CONFIG WITH ALL CHANNEL IDs
# =========================================================
DEFAULT_CONFIG = {
    "channel_order": ["1", "2", "3", "4", "5", "6", "7"],
    "youtube_api_key": YOUTUBE_API_KEY,
    "last_update": "",
    # Channel 1 - GAVIN
    "ch1_name": "GAVIN",
    "ch1_url": "https://www.youtube.com/@gavin.eyyyy",
    "ch1_channel_id": "UCwMcl87yaPyLpvg-g_HHr_g",
    "ch1_vid": "",
    "ch1_subs": "0",
    "ch1_views": "0",
    "ch1_likes": "0",
    "ch1_manual_vid": "false",
    "ch1_is_live": "false",
    # Channel 2 - SMOOTHEYYY
    "ch2_name": "SMOOTHEYYY",
    "ch2_url": "https://www.youtube.com/@Smoothnvrdie",
    "ch2_channel_id": "UCXxQ8LpYjZ9WwR7Tq6VyBmN",
    "ch2_vid": "",
    "ch2_subs": "0",
    "ch2_views": "0",
    "ch2_likes": "0",
    "ch2_manual_vid": "false",
    "ch2_is_live": "false",
    # Channel 3 - Xsnickerz
    "ch3_name": "Xsnickerz",
    "ch3_url": "https://www.youtube.com/@xsnickerz_f.f",
    "ch3_channel_id": "UC9hWjmNO8LuqmM",
    "ch3_vid": "",
    "ch3_subs": "0",
    "ch3_views": "0",
    "ch3_likes": "0",
    "ch3_manual_vid": "false",
    "ch3_is_live": "false",
    # Channel 4 - GXNOX
    "ch4_name": "GXNOX",
    "ch4_url": "https://www.youtube.com/@gxnox.ff.1",
    "ch4_channel_id": "UCWwR6TqYpZ8Lx7Vs9BnCmK",
    "ch4_vid": "",
    "ch4_subs": "0",
    "ch4_views": "0",
    "ch4_likes": "0",
    "ch4_manual_vid": "false",
    "ch4_is_live": "false",
    # Empty channels
    "ch5_name": "", "ch5_url": "", "ch5_channel_id": "", "ch5_vid": "", "ch5_subs": "0", "ch5_views": "0", "ch5_likes": "0", "ch5_manual_vid": "false", "ch5_is_live": "false",
    "ch6_name": "", "ch6_url": "", "ch6_channel_id": "", "ch6_vid": "", "ch6_subs": "0", "ch6_views": "0", "ch6_likes": "0", "ch6_manual_vid": "false", "ch6_is_live": "false",
    "ch7_name": "", "ch7_url": "", "ch7_channel_id": "", "ch7_vid": "", "ch7_subs": "0", "ch7_views": "0", "ch7_likes": "0", "ch7_manual_vid": "false", "ch7_is_live": "false",
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
        except:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except:
        pass

# =========================================================
# YOUTUBE API FUNCTIONS
# =========================================================
last_request = 0

def rate_limit():
    global last_request
    now = time.time()
    if now - last_request < 1.0:  # 1 second between requests
        time.sleep(1.0 - (now - last_request))
    last_request = time.time()

def get_channel_stats(channel_id, api_key):
    if not channel_id or not api_key:
        return None, None
    
    rate_limit()
    
    try:
        url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet&id={channel_id}&key={api_key}"
        r = requests.get(url, timeout=15)
        
        if r.status_code == 200 and r.json().get('items'):
            item = r.json()['items'][0]
            stats = item['statistics']
            subs = stats.get('subscriberCount', '0')
            name = item['snippet'].get('title', '')
            
            if subs and subs.isdigit():
                subs = f"{int(subs):,}"
            
            return subs, name
        elif r.status_code == 403:
            print(f"[API] Quota exceeded")
    except Exception as e:
        print(f"[API] Error: {e}")
    
    return None, None

def get_latest_video(channel_id, api_key):
    if not channel_id or not api_key:
        return None
    
    rate_limit()
    
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&maxResults=5&order=date&type=video&key={api_key}"
        r = requests.get(url, timeout=15)
        
        if r.status_code == 200 and r.json().get('items'):
            for item in r.json()['items']:
                title = item['snippet']['title'].lower()
                if 'live' not in title and 'stream' not in title:
                    return item['id']['videoId']
            return r.json()['items'][0]['id']['videoId']
    except Exception as e:
        print(f"[API] Error: {e}")
    
    return None

def get_video_stats(video_id, api_key):
    if not video_id or not api_key:
        return 0, 0
    
    rate_limit()
    
    try:
        url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={api_key}"
        r = requests.get(url, timeout=15)
        
        if r.status_code == 200 and r.json().get('items'):
            stats = r.json()['items'][0]['statistics']
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            return views, likes
    except Exception as e:
        print(f"[API] Error: {e}")
    
    return 0, 0

def check_live(channel_id, api_key):
    """Check if channel is currently live streaming"""
    if not channel_id or not api_key:
        return False, None
    
    rate_limit()
    
    try:
        # Search for live events
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&eventType=live&type=video&key={api_key}"
        r = requests.get(url, timeout=15)
        
        if r.status_code == 200 and r.json().get('items'):
            live_video_id = r.json()['items'][0]['id']['videoId']
            print(f"[LIVE] Live stream detected! Video ID: {live_video_id}")
            return True, live_video_id
    except Exception as e:
        print(f"[API] Live check error: {e}")
    
    return False, None

def process_channel(config, ch):
    channel_id = config.get(f"ch{ch}_channel_id", "")
    api_key = config.get("youtube_api_key", YOUTUBE_API_KEY)
    channel_name = config.get(f"ch{ch}_name", f"Channel {ch}")
    
    if not channel_id or not channel_name:
        return False
    
    changed = False
    
    # Check live status first
    is_live, live_video_id = check_live(channel_id, api_key)
    old_live = config.get(f"ch{ch}_is_live", "false") == "true"
    
    if is_live != old_live:
        config[f"ch{ch}_is_live"] = "true" if is_live else "false"
        changed = True
        if is_live and live_video_id:
            config[f"ch{ch}_vid"] = live_video_id
            changed = True
            print(f"[CH{ch}] 🔴 LIVE! {channel_name}")
    
    # Get subscriber stats
    subs, name = get_channel_stats(channel_id, api_key)
    if subs and subs != config.get(f"ch{ch}_subs", "0"):
        config[f"ch{ch}_subs"] = subs
        changed = True
        print(f"[CH{ch}] {channel_name}: {subs} subscribers")
    
    # Get latest video if not live and not manual
    manual = config.get(f"ch{ch}_manual_vid") == "true"
    if not manual and not is_live:
        vid = get_latest_video(channel_id, api_key)
        if vid and vid != config.get(f"ch{ch}_vid", ""):
            config[f"ch{ch}_vid"] = vid
            changed = True
            print(f"[CH{ch}] New video: {vid}")
    
    # Get video stats for current video
    current_vid = config.get(f"ch{ch}_vid", "")
    if current_vid:
        views, likes = get_video_stats(current_vid, api_key)
        if views > 0:
            views_str = f"{views:,}"
            if config.get(f"ch{ch}_views", "0") != views_str:
                config[f"ch{ch}_views"] = views_str
                changed = True
        if likes > 0:
            likes_str = f"{likes:,}"
            if config.get(f"ch{ch}_likes", "0") != likes_str:
                config[f"ch{ch}_likes"] = likes_str
                changed = True
    
    return changed

def background_worker():
    """Updates every 1 minute for real-time stats"""
    print("[WORKER] Started - Updates every 1 minute (live status, subscribers, views, likes)")
    
    while True:
        try:
            config = load_config()
            changed = False
            
            # Process channels in order
            for ch in config.get("channel_order", ["1", "2", "3", "4", "5", "6", "7"]):
                if process_channel(config, ch):
                    changed = True
                time.sleep(1)  # Small delay between channels
            
            if changed:
                config["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_config(config)
                print(f"[WORKER] Updated at {datetime.now().strftime('%H:%M:%S')}")
                
        except Exception as e:
            print(f"[WORKER] Error: {e}")
        
        time.sleep(60)  # Update every 60 seconds (1 minute)

worker_started = False

def start_worker():
    global worker_started
    if not worker_started:
        worker_started = True
        t = threading.Thread(target=background_worker, daemon=True)
        t.start()

# =========================================================
# HTML TEMPLATES
# =========================================================
BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>YouTube Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0c; font-family: 'Segoe UI', Arial, sans-serif; color: #e4e4e7; padding: 40px 20px; position: relative; }
        
        #particles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; }
        .container { position: relative; z-index: 1; max-width: 1400px; margin: 0 auto; background: rgba(18,18,20,0.95); border-radius: 20px; padding: 40px; border: 1px solid #27272a; }
        
        h1 { font-size: 2.5rem; text-align: center; margin-bottom: 10px; background: linear-gradient(135deg, #fff, #dc2626); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .credits { text-align: center; color: #dc2626; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px; }
        .last-updated { text-align: center; color: #71717a; font-size: 0.8rem; margin-bottom: 30px; }
        
        .channel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 25px; margin: 30px 0; }
        .channel-card { background: #18181b; border: 2px solid #27272a; border-radius: 16px; padding: 20px; transition: all 0.3s; position: relative; }
        .channel-card.live-card { border-color: #dc2626; animation: pulse 1.5s infinite; background: linear-gradient(145deg, #18181b, #1a0a0a); }
        @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.7); } 50% { box-shadow: 0 0 25px 8px rgba(220,38,38,0.4); } }
        .channel-card:hover { transform: translateY(-5px); border-color: #dc2626; }
        
        .channel-name { font-size: 1.3rem; font-weight: bold; text-align: center; margin-bottom: 15px; display: flex; align-items: center; justify-content: center; gap: 10px; flex-wrap: wrap; }
        .live-badge { background: #dc2626; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: bold; animation: badgePulse 1s infinite; display: inline-flex; align-items: center; gap: 6px; letter-spacing: 1px; }
        .live-badge::before { content: "●"; font-size: 12px; animation: blink 1s infinite; }
        @keyframes badgePulse { 0%,100% { background: #dc2626; transform: scale(1); } 50% { background: #ef4444; transform: scale(1.05); } }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
        
        .video-container { position: relative; padding-bottom: 56.25%; background: #000; border-radius: 12px; overflow: hidden; margin-bottom: 15px; }
        .video-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
        .video-placeholder { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #0b0b0c; color: #71717a; flex-direction: column; gap: 10px; }
        
        .stats { display: flex; justify-content: space-around; background: #0b0b0c; padding: 12px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #27272a; }
        .stat { text-align: center; flex: 1; }
        .stat-value { display: block; font-weight: bold; font-size: 1rem; }
        .stat-label { font-size: 0.65rem; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .btn { display: block; background: #dc2626; color: white; text-decoration: none; text-align: center; padding: 10px; border-radius: 8px; font-weight: bold; transition: all 0.2s; }
        .btn:hover { background: #ef4444; transform: scale(0.98); }
        .btn-secondary { background: #27272a; display: inline-block; width: auto; padding: 6px 16px; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #27272a; }
        
        .alert { background: rgba(220,38,38,0.2); border: 1px solid #dc2626; color: #fca5a5; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
        .form-group { margin-bottom: 12px; }
        label { display: block; margin-bottom: 5px; font-size: 0.85rem; color: #a1a1aa; }
        input { width: 100%; padding: 8px 12px; background: #0b0b0c; border: 1px solid #3f3f46; color: white; border-radius: 6px; }
        .admin-section { background: #18181b; border: 1px solid #27272a; padding: 15px; border-radius: 12px; margin-bottom: 15px; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .drag-handle { cursor: grab; margin-right: 8px; color: #71717a; }
        .reorder-btn { background: #27272a; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-bottom: 20px; }
        .note { font-size: 0.7rem; color: #71717a; margin-top: 8px; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
</head>
<body>
    <canvas id="particles"></canvas>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    <script>
        // Particle Animation System
        class Particle {
            constructor(canvas) {
                this.canvas = canvas;
                this.size = Math.random() * 3 + 1;
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.vx = (Math.random() - 0.5) * 1.5;
                this.vy = (Math.random() - 0.5) * 1.5;
                this.opacity = Math.random() * 0.5 + 0.2;
            }
            update() {
                this.x += this.vx;
                this.y += this.vy;
                if (this.x < 0 || this.x > this.canvas.width) this.vx *= -1;
                if (this.y < 0 || this.y > this.canvas.height) this.vy *= -1;
            }
            draw(ctx) {
                ctx.beginPath();
                ctx.fillStyle = `rgba(220, 38, 38, ${this.opacity})`;
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        const canvas = document.getElementById('particles');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        const particles = [];
        for (let i = 0; i < 250; i++) particles.push(new Particle(canvas));
        function animate() {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (let p of particles) { p.update(); p.draw(ctx); }
            requestAnimationFrame(animate);
        }
        animate();
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
        // Auto-refresh every 60 seconds
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>🎬 Our YouTube Channels</h1>
    <div class="credits">DEVELOPED BY HARSHITH</div>
    <div class="last-updated">🔄 Live updates every 1 minute • Last updated: {{ config.get('last_update', 'Never') }}</div>
    
    <div class="channel-grid">
        {% for ch in config.get('channel_order', ['1','2','3','4','5','6','7']) %}
        {% set url = config.get('ch' ~ ch ~ '_url', '') %}
        {% set is_live = config.get('ch' ~ ch ~ '_is_live', 'false') == 'true' %}
        {% if url and url != "" %}
        <div class="channel-card {% if is_live %}live-card{% endif %}">
            <div class="channel-name">
                {{ config.get('ch' ~ ch ~ '_name', 'Channel') }}
                {% if is_live %}
                <span class="live-badge">LIVE</span>
                {% endif %}
            </div>
            <div class="video-container">
                {% set vid = config.get('ch' ~ ch ~ '_vid', '') %}
                {% if vid and vid|length == 11 %}
                <iframe src="https://www.youtube.com/embed/{{ vid }}?autoplay=0&rel=0" allowfullscreen></iframe>
                {% else %}
                <div class="video-placeholder">
                    <span>📹</span>
                    <span>Loading video...</span>
                </div>
                {% endif %}
            </div>
            <div class="stats">
                <div class="stat">
                    <span class="stat-value">{{ config.get('ch' ~ ch ~ '_subs', '0') }}</span>
                    <span class="stat-label">SUBSCRIBERS</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{{ config.get('ch' ~ ch ~ '_views', '0') }}</span>
                    <span class="stat-label">VIEWS</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{{ config.get('ch' ~ ch ~ '_likes', '0') }}</span>
                    <span class="stat-label">LIKES</span>
                </div>
            </div>
            <a href="{{ url }}" target="_blank" class="btn">▶ Visit Channel</a>
        </div>
        {% endif %}
        {% endfor %}
    </div>
    
    <div class="footer">
        <a href="{{ url_for('login') }}" class="btn btn-secondary">🔒 Admin Access</a>
    </div>
{% endblock %}
"""

LOGIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h2>🔐 Admin Login</h2>
    <div class="credits">System Security Console</div>
    {% if error %}<div class="alert">⚠️ {{ error }}</div>{% endif %}
    <form method="POST" style="max-width: 400px; margin: 0 auto;">
        <div class="form-group">
            <label>Username</label>
            <input type="text" name="username" required>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="btn" style="width: 100%;">Authenticate</button>
    </form>
    <div class="footer">
        <a href="{{ url_for('index') }}" class="btn-secondary">← Back</a>
    </div>
{% endblock %}
"""

ADMIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h2>⚙️ Admin Panel</h2>
    <div class="credits">Channel Management</div>
    
    <button class="reorder-btn" onclick="toggleReorder()">📱 Drag to Reorder Channels</button>
    
    <form method="POST">
        <div class="admin-section">
            <h4>🔑 YouTube API Key</h4>
            <div class="form-group">
                <input type="text" name="youtube_api_key" value="{{ config.get('youtube_api_key', '') }}" placeholder="AIzaSy...">
                <div class="note">Get from Google Cloud Console → Enable YouTube Data API v3</div>
            </div>
        </div>
        
        <div class="form-grid" id="adminGrid">
            {% for i in ['1','2','3','4','5','6','7'] %}
            <div class="admin-section" data-id="{{ i }}">
                <h4><span class="drag-handle">⋮⋮</span> Channel {{ i }}</h4>
                <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" name="ch{{ i }}_name" value="{{ config.get('ch' ~ i ~ '_name', '') }}">
                </div>
                <div class="form-group">
                    <label>YouTube URL</label>
                    <input type="text" name="ch{{ i }}_url" value="{{ config.get('ch' ~ i ~ '_url', '') }}" placeholder="https://youtube.com/@handle">
                </div>
                <div class="form-group">
                    <label>Channel ID</label>
                    <input type="text" name="ch{{ i }}_channel_id" value="{{ config.get('ch' ~ i ~ '_channel_id', '') }}" placeholder="UCxxxxxxxxxxxxxxxxxxxx">
                </div>
                <div class="form-group">
                    <label>Manual Video ID (Optional)</label>
                    <input type="text" name="ch{{ i }}_vid" value="{{ config.get('ch' ~ i ~ '_vid', '') }}" placeholder="11 characters">
                </div>
                <div class="note">
                    {% if config.get('ch' ~ i ~ '_is_live', 'false') == 'true' %}
                    🔴 <strong style="color: #dc2626;">LIVE NOW!</strong> • 
                    {% endif %}
                    {% if config.get('ch' ~ i ~ '_channel_id') %}
                    ✓ Channel ID configured
                    {% else %}
                    ⚠️ Channel ID required
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <button type="submit" class="btn" style="background: #16a34a; margin-top: 20px;">💾 Save All Changes</button>
    </form>
    
    <div class="footer">
        <a href="{{ url_for('logout') }}" class="btn btn-secondary">🚪 Logout</a>
    </div>
    
    <script>
        let sortable = null;
        function toggleReorder() {
            if(sortable) {
                sortable.destroy();
                sortable = null;
                event.target.textContent = '📱 Drag to Reorder Channels';
                saveOrder();
            } else {
                sortable = new Sortable(document.getElementById('adminGrid'), {
                    animation: 300,
                    handle: '.drag-handle',
                    onEnd: () => saveOrder()
                });
                event.target.textContent = '✓ Done';
            }
        }
        
        function saveOrder() {
            let order = Array.from(document.querySelectorAll('#adminGrid .admin-section')).map(el => el.getAttribute('data-id'));
            fetch('/save-order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({order: order})
            });
        }
    </script>
{% endblock %}
"""

app.jinja_loader = DictLoader({
    'base': BASE_LAYOUT,
    'index': INDEX_TEMPLATE,
    'login': LOGIN_TEMPLATE,
    'admin': ADMIN_TEMPLATE
})

# =========================================================
# ROUTES
# =========================================================
@app.route('/')
def index():
    return render_template_string(INDEX_TEMPLATE, config=load_config())

@app.route('/save-order', methods=['POST'])
def save_order():
    if session.get('admin_authed'):
        data = request.get_json()
        config = load_config()
        config['channel_order'] = data.get('order', [])
        save_config(config)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_authed'):
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        
        if keyauthapp and KEYAUTH_AVAILABLE:
            try:
                keyauthapp.login(u, p)
                session['admin_authed'] = True
                return redirect(url_for('admin'))
            except:
                return render_template_string(LOGIN_TEMPLATE, error="don't try u mother fucker")
        else:
            if u == "admin" and p == "admin123":
                session['admin_authed'] = True
                return redirect(url_for('admin'))
            else:
                return render_template_string(LOGIN_TEMPLATE, error="don't try u mother fucker")
    
    return render_template_string(LOGIN_TEMPLATE, error=None)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_authed'):
        return redirect(url_for('login'))
    
    config = load_config()
    
    if request.method == 'POST':
        config['youtube_api_key'] = request.form.get('youtube_api_key', '').strip()
        
        for i in range(1, 8):
            config[f'ch{i}_name'] = request.form.get(f'ch{i}_name', '').strip()
            config[f'ch{i}_url'] = request.form.get(f'ch{i}_url', '').strip()
            config[f'ch{i}_channel_id'] = request.form.get(f'ch{i}_channel_id', '').strip()
            vid = request.form.get(f'ch{i}_vid', '').strip()
            config[f'ch{i}_vid'] = vid
            config[f'ch{i}_manual_vid'] = "true" if vid else "false"
            
            if not config[f'ch{i}_url']:
                config[f'ch{i}_subs'] = "0"
                config[f'ch{i}_views'] = "0"
                config[f'ch{i}_likes'] = "0"
                config[f'ch{i}_is_live'] = "false"
                config[f'ch{i}_channel_id'] = ""
        
        save_config(config)
        
        # Force immediate update
        for ch in config.get("channel_order", ["1", "2", "3", "4", "5", "6", "7"]):
            process_channel(config, ch)
            time.sleep(1)
        
        config["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_config(config)
        
        return redirect(url_for('index'))
    
    return render_template_string(ADMIN_TEMPLATE, config=config)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# =========================================================
# START
# =========================================================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("   YOUTUBE DASHBOARD")
    print("="*50)
    
    start_worker()
    
    print("\n[READY] http://localhost:5000")
    print("[READY] Admin: http://localhost:5000/login\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)