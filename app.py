import smtplib
import dns.resolver
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
HUNTER_API_KEY = "87a007d5823fc78829c96a38fce6c6ed5d6f6fd8"
APOLLO_API_KEY = "LAMrYiH6ZJC90bg88mM9vg"

def free_handshake_verify(email):
    """Tier 3: The 'Bypass' logic - Ultra-fast 2s timeouts"""
    try:
        domain = email.split('@')[-1]
        # DNS lookup restricted to 2 seconds
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2
        resolver.lifetime = 2
        records = resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        
        # SMTP check restricted to 2 seconds
        server = smtplib.SMTP(timeout=2)
        server.connect(mx_record)
        server.helo()
        server.mail('test@ttsfx.com')
        code, _ = server.rcpt(email)
        server.quit()
        
        if code == 250:
            return {"status": "Deliverable", "risk": "Low", "mx": mx_record, "source": "Free Handshake"}
    except:
        pass
    # Always return a dict to avoid 'bool' object subscriptable error
    return {"status": "Undeliverable", "risk": "Medium", "mx": "N/A", "source": "Free Handshake"}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/verify', methods=['POST'])
def verify():
    email = request.json.get('email', '').strip()
    if not email:
        return jsonify({"error": "No email provided"}), 400

    # --- TIER 1: TRY HUNTER.IO (VERIFIER) ---
    try:
        hunter_url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}"
        r = requests.get(hunter_url, timeout=2) # Fast timeout
        if r.status_code == 200:
            res_data = r.json().get('data', {})
            if res_data.get('status') not in ['unknown', None]:
                return jsonify({
                    "email": email,
                    "status": res_data.get('status', 'deliverable'),
                    "risk_score": f"{res_data.get('score', 0)}%",
                    "mx_server": res_data.get('mx_records', [{}])[0].get('exchange', 'Cloud') if res_data.get('mx_records') else 'None',
                    "first_name": res_data.get('first_name') or 'Lead',
                    "last_name": res_data.get('last_name') or 'Found',
                    "location": "Global",
                    "source": "Hunter.io (Premium)"
                })
    except Exception as e:
        print(f"Hunter Verifier Error: {e}")

    # --- TIER 2: TRY APOLLO.IO (PEOPLE MATCH) ---
    try:
        apollo_url = "https://api.apollo.io/v1/people/match"
        headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
        params = {"api_key": APOLLO_API_KEY, "email": email}
        
        r = requests.post(apollo_url, headers=headers, json=params, timeout=2)
        if r.status_code == 200:
            person = r.json().get('person', {})
            if person:
                return jsonify({
                    "email": email,
                    "status": "Verified",
                    "risk_score": "95%",
                    "mx_server": "Social Match",
                    "first_name": person.get('first_name') or 'Lead',
                    "last_name": person.get('last_name') or 'Found',
                    "location": f"{person.get('city', '')}, {person.get('country', 'Global')}".strip(', '),
                    "source": "Apollo.io (Global)"
                })
    except Exception as e:
        print(f"Apollo Error: {e}")

    # --- TIER 3: HUNTER DOMAIN SEARCH (COMPANY FALLBACK) ---
    try:
        domain = email.split('@')[-1]
        d_url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
        dr = requests.get(d_url, timeout=2)
        if dr.status_code == 200:
            d_data = dr.json().get('data', {})
            if d_data.get('organization'):
                return jsonify({
                    "email": email, "status": "Deliverable", "risk_score": "80%", "mx_server": "Enterprise",
                    "first_name": d_data.get('organization'), "last_name": "Official",
                    "location": d_data.get('country', 'Global'), "source": "Hunter.io (Domain)"
                })
    except:
        pass

    # --- TIER 4: FINAL FALLBACK (HANDSHAKE) ---
    res = free_handshake_verify(email)
    return jsonify({
        "email": email,
        "status": res.get('status'),
        "risk_score": res.get('risk'),
        "mx_server": res.get('mx'),
        "first_name": "Unknown",
        "last_name": "Lead",
        "location": "Global",
        "source": res.get('source')
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)