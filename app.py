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

try:
    from keyauth import api
except Exception as e:
    print(f"[WARNING] KeyAuth not available: {e}")
    api = None

APP_NAME = "CRZ FREE PANEL"
OWNER_ID = "EckNXwLHE7"
VERSION = "1.0"
    
keyauthapp = None
if api is not None:
    try:
        keyauthapp = api(
            name=APP_NAME,
            ownerid=OWNER_ID,
            version=VERSION,
            hash_to_check=""
        )
    except Exception as e:
        print(f"[WARNING] KeyAuth setup failed: {e}")
        keyauthapp = None

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ch1_name": "Main Channel", "ch1_url": "", "ch1_vid": "", "ch1_subs": "0", "ch1_views": "0", "ch1_likes": "0",
    "ch2_name": "Second Channel", "ch2_url": "", "ch2_vid": "", "ch2_subs": "0", "ch2_views": "0", "ch2_likes": "0",
    "ch3_name": "Third Channel", "ch3_url": "", "ch3_vid": "", "ch3_subs": "0", "ch3_views": "0", "ch3_likes": "0",
    "ch4_name": "Fourth Channel", "ch4_url": "", "ch4_vid": "", "ch4_subs": "0", "ch4_views": "0", "ch4_likes": "0",
    "ch5_name": "Fifth Channel", "ch5_url": "", "ch5_vid": "", "ch5_subs": "0", "ch5_views": "0", "ch5_likes": "0",
    "ch6_name": "Sixth Channel", "ch6_url": "", "ch6_vid": "", "ch6_subs": "0", "ch6_views": "0", "ch6_likes": "0",
    "ch7_name": "Seventh Channel", "ch7_url": "", "ch7_vid": "", "ch7_subs": "0", "ch7_views": "0", "ch7_likes": "0"
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
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to write configuration file: {e}")

# =========================================================
# DEEP RECENT CATALOG AGGREGATION METRICS ENGINE
# =========================================================
def parse_subscribers_safely(html_content):
    if not html_content:
        return None
    match1 = re.search(r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"', html_content)
    if match1:
        res = re.sub(r'(subscribers|subscriber).*', '', match1.group(1), flags=re.IGNORECASE).strip()
        if res: return res
    match2 = re.search(r'"subscriberCountText":\{\s*"simpleText"\s*:\s*"([^"]+)"\}', html_content)
    if match2:
        res = match2.group(1).replace("subscribers", "").replace("subscriber", "").strip()
        if res: return res
    match3 = re.search(r'"label":"([\d,M\.K\s]+)(subscribers|subscriber)"', html_content, flags=re.IGNORECASE)
    if match3:
        res = match3.group(1).strip()
        if res: return res
    return None

def youtube_monitor_worker():
    print("[SYSTEM] Video playlist deep-crawler tracking layer activated.")
    while True:
        try:
            config = load_config()
            is_config_altered = False
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }

            for i in range(1, 8):
                channel_url = config.get(f"ch{i}_url", "")
                if not channel_url or not isinstance(channel_url, str) or "youtube.com" not in channel_url.lower():
                    continue

                base_url = channel_url.strip().rstrip('/')
                is_currently_live = False
                discovered_video_ids = []

                try:
                    live_endpoint = f"{base_url}/live"
                    response = requests.get(live_endpoint, headers=headers, timeout=4)
                    if response.status_code == 200:
                        live_html = response.text
                        if '"isLive":true' in live_html or 'label":"LIVE"' in live_html:
                            id_match = re.search(r'"videoId":"([^"]+)"', live_html)
                            if id_match:
                                discovered_video_ids.append(id_match.group(1))
                                is_currently_live = True
                except Exception:
                    pass

                try:
                    videos_endpoint = f"{base_url}/videos"
                    response = requests.get(videos_endpoint, headers=headers, timeout=4)
                    if response.status_code == 200:
                        video_html = response.text
                        extracted_subs = parse_subscribers_safely(video_html)
                        if extracted_subs:
                            config[f"ch{i}_subs"] = extracted_subs
                            is_config_altered = True

                        for item in re.finditer(r'"videoId":"([^"]+)"', video_html):
                            v_id = item.group(1)
                            if v_id not in discovered_video_ids:
                                discovered_video_ids.append(v_id)
                except Exception:
                    pass

                if discovered_video_ids:
                    latest_id = discovered_video_ids[0]
                    if config.get(f"ch{i}_vid") != latest_id:
                        config[f"ch{i}_vid"] = latest_id
                        is_config_altered = True

                target_calculation_pool = discovered_video_ids[:5]
                running_views_total = 0
                running_likes_total = 0

                for target_id in target_calculation_pool:
                    try:
                        watch_url = f"https://www.youtube.com/watch?v={target_id}"
                        watch_res = requests.get(watch_url, headers=headers, timeout=3)
                        if watch_res.status_code == 200:
                            w_html = watch_res.text

                            v_match = re.search(r'"viewCount":"(\d+)"', w_html)
                            if v_match:
                                running_views_total += int(v_match.group(1))
                            else:
                                lbl_views = re.search(r'"label":"([\d,]+)\s+views"', w_html)
                                if lbl_views:
                                    running_views_total += int(lbl_views.group(1).replace(',', ''))

                            l_match = re.search(r'"likeCount":"(\d+)"', w_html)
                            if l_match:
                                running_likes_total += int(l_match.group(1))
                            else:
                                lbl_likes = re.search(r'"label":"([\d,]+)\s+likes"', w_html)
                                if lbl_likes:
                                    running_likes_total += int(lbl_likes.group(1).replace(',', ''))
                    except Exception:
                        pass

                config[f"ch{i}_views"] = f"{running_views_total:,}" if running_views_total > 0 else "0"
                config[f"ch{i}_likes"] = f"{running_likes_total:,}" if running_likes_total > 0 else "0"
                is_config_altered = True

                raw_display_name = config.get(f"ch{i}_name", "")
                sanitized_name = re.sub(r'\s*\(LIVE\)$', '', raw_display_name, flags=re.IGNORECASE).strip()
                target_name = f"{sanitized_name} (LIVE)" if is_currently_live else sanitized_name

                if raw_display_name != target_name:
                    config[f"ch{i}_name"] = target_name
                    is_config_altered = True

            if is_config_altered:
                save_config(config)

        except Exception as system_loop_error:
            print(f"[CRITICAL] Loop error inside parsing engine core: {system_loop_error}")

        time.sleep(10)

if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    worker_thread = threading.Thread(target=youtube_monitor_worker, daemon=True)
    worker_thread.start()

# =========================================================
# 2. UI LAYOUT WITH UPGRADED HIGH-DENSITY SPARK FIELD
# =========================================================
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Our YouTube Channel</title>
    <style>
        @keyframes fadeInUp {
            0% { opacity: 0; transform: translateY(20px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        html, body { margin: 0; padding: 0; width: 100%; min-height: 100%; background-color: #060607; }
        body { font-family: 'Segoe UI', Arial, sans-serif; color: #e4e4e7; text-align: center; padding: 40px 20px; box-sizing: border-box; position: relative; }
        
        /* Outside particle background canvas */
        #particles-canvas-bg { 
            position: fixed; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            z-index: 1; 
            pointer-events: none;
            transform: translateZ(0);
            will-change: transform;
        }

        .container { 
            position: relative; 
            z-index: 5; 
            max-width: 1200px; 
            margin: auto; 
            background: rgba(18, 18, 20, 0.93); 
            padding: 40px 20px; 
            border-radius: 16px; 
            border: 1px solid #1f1f23; 
            box-shadow: 0 20px 50px rgba(0,0,0,0.8); 
            overflow: hidden; /* Clips inside particles to border-radius */
        }

        /* Inside particle box canvas */
        #particles-canvas-fg { 
            position: absolute; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            z-index: 1; 
            pointer-events: none;
            transform: translateZ(0);
            will-change: transform;
        }

        /* Forces container text/grids to stack cleanly above the foreground canvas layer */
        .container > *:not(#particles-canvas-fg) {
            position: relative;
            z-index: 2;
        }
        
        h1 { color: #ffffff; font-size: 2.7rem; margin-bottom: 5px; letter-spacing: -0.5px; }
        .credits { color: #dc2626; font-weight: bold; font-size: 1.1rem; letter-spacing: 2px; margin-bottom: 30px; text-transform: uppercase; text-shadow: 0 0 10px rgba(220, 38, 38, 0.4); }
        p { color: #a1a1aa; font-size: 1.05rem; }
        
        .channel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 25px; margin: 30px 0; }
        
        .channel-card { 
            background: #18181b; 
            border: 1px solid #27272a; 
            border-radius: 14px; 
            padding: 18px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.4); 
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            animation: fadeInUp 0.6s ease-out both;
        }
        .channel-card:hover { 
            transform: translateY(-6px); 
            border-color: #dc2626; 
            box-shadow: 0 12px 24px rgba(220, 38, 38, 0.2); 
        }
        
        .channel-grid > :nth-child(1) { animation-delay: 0.05s; }
        .channel-grid > :nth-child(2) { animation-delay: 0.1s; }
        .channel-grid > :nth-child(3) { animation-delay: 0.15s; }
        .channel-grid > :nth-child(4) { animation-delay: 0.2s; }
        .channel-grid > :nth-child(5) { animation-delay: 0.25s; }
        .channel-grid > :nth-child(6) { animation-delay: 0.3s; }
        .channel-grid > :nth-child(7) { animation-delay: 0.35s; }

        .channel-card h3 { margin-top: 0; color: #ffffff; font-size: 1.25rem; min-height: 34px; display: flex; align-items: center; justify-content: center; }
        .video-container { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 8px; border: 1px solid #27272a; margin-bottom: 15px; }
        .video-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
        .video-placeholder { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #0b0b0c; color: #71717a; font-size: 0.9rem; font-weight: 500; }
        
        .stats-badge-container { display: flex; justify-content: space-around; background: #0b0b0c; padding: 12px 6px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #1f1f23; font-size: 0.85rem; }
        .stat-item { text-align: center; width: 33%; }
        .stat-val { display: block; color: #ffffff; font-weight: 700; font-size: 0.95rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 2px; }
        .channel-card:hover .stat-val { color: #fca5a5; }
        .stat-lbl { color: #71717a; font-size: 0.72rem; text-transform: uppercase; font-weight: 500; letter-spacing: 0.5px; }
        
        .btn { display: inline-block; background: #dc2626; color: #ffffff; padding: 11px 20px; border: none; border-radius: 8px; cursor: pointer; text-decoration: none; font-weight: 600; font-size: 0.95rem; transition: all 0.2s ease; width: 100%; box-sizing: border-box; }
        .btn:hover { background: #ef4444; box-shadow: 0 0 12px rgba(220, 38, 38, 0.4); }
        .btn-secondary { background: #27272a; color: #e4e4e7; border: 1px solid #3f3f46; width: auto; padding: 6px 16px; }
        .btn-secondary:hover { background: #3f3f46; }
        
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; text-align: left; }
        .admin-section { background: #18181b; border: 1px solid #27272a; padding: 20px; border-radius: 8px; margin-bottom: 10px; }
        .admin-section h4 { margin-top: 0; color: #dc2626; border-bottom: 1px solid #27272a; padding-bottom: 8px; }
        .form-group { text-align: left; margin-bottom: 15px; }
        label { display: block; margin-bottom: 6px; color: #d4d4d8; font-weight: 500; font-size: 0.9rem; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #3f3f46; background: #0b0b0c; color: #fff; border-radius: 6px; box-sizing: border-box; font-size: 0.95rem; }
        .alert { background: rgba(220, 38, 38, 0.2); border: 1px solid #dc2626; color: #fca5a5; padding: 14px; border-radius: 6px; margin-bottom: 25px; font-weight: bold; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px; }
        .footer { margin-top: 50px; border-top: 1px solid #27272a; padding-top: 20px; }
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

                    if (this.x - this.size <= 0) {
                        this.x = this.size;
                        this.speedX *= -1;
                    } else if (this.x + this.size >= this.canvas.width) {
                        this.x = this.canvas.width - this.size;
                        this.speedX *= -1;
                    }

                    if (this.y - this.size <= 0) {
                        this.y = this.size;
                        this.speedY *= -1;
                    } else if (this.y + this.size >= this.canvas.height) {
                        this.y = this.canvas.height - this.size;
                        this.speedY *= -1;
                    }
                }
                draw(ctx) {
                    ctx.beginPath();
                    ctx.fillStyle = `rgba(220, 38, 38, ${this.opacity})`;
                    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            function setupParticleSystem(canvasId, densityDivider, absoluteMax) {
                const canvas = document.getElementById(canvasId);
                if (!canvas) return null;
                const ctx = canvas.getContext('2d');
                let particlesArray = [];

                function resize() {
                    if (canvasId === 'particles-canvas-bg') {
                        canvas.width = window.innerWidth;
                        canvas.height = window.innerHeight;
                    } else {
                        canvas.width = canvas.offsetWidth;
                        canvas.height = canvas.offsetHeight;
                    }
                    populate();
                }

                function populate() {
                    particlesArray = [];
                    // Increased particle generation limits to yield a much higher density field
                    const count = Math.min(Math.floor(canvas.width / densityDivider), absoluteMax);
                    for (let i = 0; i < count; i++) {
                        particlesArray.push(new MicroParticle(canvas));
                    }
                }

                window.addEventListener('resize', resize);
                resize();

                return {
                    renderFrame: function() {
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        for (let i = 0; i < particlesArray.length; i++) {
                            particlesArray[i].update();
                            particlesArray[i].draw(ctx);
                        }
                    }
                };
            }

            // High density systems initialized with broad scale caps
            const outsideSystem = setupParticleSystem('particles-canvas-bg', 2.5, 450);
            const insideSystem = setupParticleSystem('particles-canvas-fg', 2.5, 350);

            function executionLoop() {
                if (outsideSystem) outsideSystem.renderFrame();
                if (insideSystem) insideSystem.renderFrame();
                requestAnimationFrame(executionLoop);
            }

            executionLoop();
        })();
    </script>
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>Our YouTube Channel</h1>
    <div class="credits">Developed by HARSHITH</div>
    <p>Explore our networks, watch featured content, and subscribe directly below!</p>
    <div class="channel-grid">
        {% for i in ['1', '2', '3', '4', '5', '6', '7'] %}
        {% set ch_url = config.get('ch' ~ i ~ '_url', '') %}
        
        {% if ch_url and ch_url|string|trim != "" %}
        <div class="channel-card">
            <h3>{{ config.get('ch' ~ i ~ '_name', 'YouTube Channel') | replace('(LIVE)', '<span style="color: #ef4444; font-weight: bold; margin-left:5px; text-shadow: 0 0 8px rgba(239,68,68,0.6);">(LIVE)</span>') | safe }}</h3>
            
            <div class="video-container">
                {% if config.get('ch' ~ i ~ '_vid') %}
                    <iframe src="https://www.youtube.com/embed/{{ config['ch' ~ i ~ '_vid'] }}" frameborder="0" allowfullscreen></iframe>
                {% else %}
                    <div class="video-placeholder">Synchronizing Latest Stream...</div>
                {% endif %}
            </div>
            
            <div class="stats-badge-container">
                <div class="stat-item">
                    <span class="stat-val">{{ config.get('ch' ~ i ~ '_subs', '0') }}</span>
                    <span class="stat-lbl">Subs</span>
                </div>
                <div class="stat-item">
                    <span class="stat-val">{{ config.get('ch' ~ i ~ '_views', '0') }}</span>
                    <span class="stat-lbl">Total Views</span>
                </div>
                <div class="stat-item">
                    <span class="stat-val">{{ config.get('ch' ~ i ~ '_likes', '0') }}</span>
                    <span class="stat-lbl">Total Likes</span>
                </div>
            </div>

            <a href="{{ ch_url }}" target="_blank" class="btn">🚀 Visit Channel</a>
        </div>
        {% endif %}
        {% endfor %}
    </div>
    <div class="footer">
        <a href="{{ url_for('login') }}" class="btn btn-secondary" style="font-size: 0.85rem;">Admin Access</a>
    </div>
{% endblock %}
"""

LOGIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h2>Admin Verification</h2>
    <div class="credits" style="font-size:0.9rem; margin-bottom:15px;">System Security Console</div>
    {% if error %}<div class="alert">⚠️ {{ error }}</div>{% endif %}
    <form method="POST" style="max-width: 450px; margin: 0 auto;">
        <div class="form-group">
            <label>KeyAuth Username</label>
            <input type="text" name="username" required>
        </div>
        <div class="form-group">
            <label>KeyAuth Password</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="btn" style="width: 100%; padding: 12px;">Authenticate</button>
    </form>
    <p style="margin-top: 20px;"><a href="{{ url_for('index') }}" style="color: #a1a1aa; text-decoration: none;">← Return Home</a></p>
{% endblock %}
"""

ADMIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h2>Dashboard Control Panel</h2>
    <div class="credits">System Access Node</div>
    <form method="POST" style="margin-top: 30px;">
        <div class="form-grid">
            {% for i in ['1', '2', '3', '4', '5', '6', '7'] %}
            <div class="admin-section">
                <h4>Channel {{ i }} Control</h4>
                <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" name="ch{{ i }}_name" value="{{ config.get('ch' ~ i ~ '_name', '') }}">
                </div>
                <div class="form-group">
                    <label>URL Link (Clear field completely to hide card)</label>
                    <input type="text" name="ch{{ i }}_url" value="{{ config.get('ch' ~ i ~ '_url', '') }}">
                </div>
                <div class="form-group">
                    <label>Override Video ID (Optional - Engine auto-detects if left blank)</label>
                    <input type="text" name="ch{{ i }}_vid" value="{{ config.get('ch' ~ i ~ '_vid', '') }}">
                </div>
            </div>
            {% endfor %}
        </div>
        <button type="submit" class="btn" style="background: #16a34a; max-width: 300px; padding: 14px; font-size: 1.1rem; margin-top: 20px;">Save All Modifications</button>
    </form>
    <div class="footer"><a href="{{ url_for('logout') }}" class="btn btn-secondary">Logout</a></div>
{% endblock %}
"""

app.jinja_loader = DictLoader({'base': BASE_LAYOUT})

# =========================================================
# 3. ROUTING & CONTROLLERS
# =========================================================
@app.route('/')
def index():
    current_config = load_config()
    return render_template_string(INDEX_TEMPLATE, config=current_config), 200, {'Content-Type': 'text/html'}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_authed'):
        return redirect(url_for('admin'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if keyauthapp is None:
            error = "Authentication system unavailable"
        else:
            try:
                keyauthapp.login(username, password)
                session['admin_authed'] = True
                return redirect(url_for('admin'))
            except Exception:
                error = "Invalid credentials"
                
    return render_template_string(LOGIN_TEMPLATE, error=error), 200, {'Content-Type': 'text/html'}

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_authed'):
        return redirect(url_for('login'))
        
    current_config = load_config()
    if request.method == 'POST':
        for idx in range(1, 8):
            current_config[f'ch{idx}_name'] = request.form.get(f'ch{idx}_name', '').strip()
            current_config[f'ch{idx}_url'] = request.form.get(f'ch{idx}_url', '').strip()
            current_config[f'ch{idx}_vid'] = request.form.get(f'ch{idx}_vid', '').strip()
            
            if not current_config[f'ch{idx}_url']:
                current_config[f'ch{idx}_subs'] = "0"
                current_config[f'ch{idx}_views'] = "0"
                current_config[f'ch{idx}_likes'] = "0"
                current_config[f'ch{idx}_vid'] = ""
        
        save_config(current_config)
        return redirect(url_for('index'))
        
    return render_template_string(ADMIN_TEMPLATE, config=current_config), 200, {'Content-Type': 'text/html'}

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
