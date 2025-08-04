import json
import requests
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

def is_running_under_gunicorn():
    """Check if the application is running under gunicorn."""
    return (
        "gunicorn" in os.environ.get("SERVER_SOFTWARE", "") or
        "gunicorn" in str(os.environ.get("WSGI_SERVER", "")) or
        os.environ.get("GUNICORN_PID") is not None or
        "gunicorn" in str(globals().get("__name__", ""))
    )

if is_running_under_gunicorn():
    # Production CORS configuration
    allowed_origins = [
        "https://eyemei.cc",
        "https://www.eyemei.cc",
        "https://joshattic.us",
        "https://www.joshattic.us",
        "https://eyemei.joshattic.us"
    ]
    
    CORS(app, origins=allowed_origins, supports_credentials=True)
    logger.info("Production mode: CORS configured for eyemei.cc and joshattic.us domains")
else:
    # Development CORS configuration
    dev_origins = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:5000",
        "http://0.0.0.0:8000"
    ]
    
    CORS(app, origins=dev_origins, supports_credentials=True)
    logger.info("Development mode: CORS configured for localhost only")
    
EYEMEI_JSON_PATH = 'databases/eyemei.json'
OSMOCOM_JSON_PATH = 'databases/osmocom.json'
ISTHISPHONEBLOCKED_JSON_PATH = 'databases/isthisphoneblocked.json'
RANDOMMER_JSON_PATH = 'databases/randommer.json'
LOOKUP_LOG_JSON_PATH = 'databases/lookup_log.json'

class IMEIDatabase:
    def __init__(self, json_path):
        self.json_path = json_path
        self.data = self.load_database()
        
    def load_database(self):
        """Load the JSON database."""
        try:
            if os.path.exists(self.json_path):
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                brands_data = data.get('brands', {})
                total_brands = len(brands_data)
                total_tacs = 0
                total_models = 0
                
                for brand_name, brand_info in brands_data.items():
                    models = brand_info.get('models', [])
                    total_models += len(models)
                    for model_dict in models:
                        for model_name, model_info in model_dict.items():
                            tacs = model_info.get('tacs', [])
                            total_tacs += len(tacs)
                
                estimated_devices = total_tacs * 1_000_000
                
                logger.info(f"Loaded database {os.path.basename(self.json_path)}: "
                           f"{total_brands:,} brands, {total_models:,} models, "
                           f"{total_tacs:,} TACs, ~{estimated_devices:,} estimated unique devices")
                return data
            else:
                logger.warning(f"Database file not found: {self.json_path}")
                return {"brands": {}}
        except Exception as e:
            logger.error(f"Error loading database {self.json_path}: {e}")
            return {"brands": {}}
    
    def lookup_tac(self, tac):
        """Look up device information by TAC."""
        brands_data = self.data.get('brands', {})
        
        for brand_name, brand_info in brands_data.items():
            models = brand_info.get('models', [])
            for model_dict in models:
                for model_name, model_info in model_dict.items():
                    tacs = model_info.get('tacs', [])
                    if tac in tacs:
                        image = model_info.get('image', '')
                        if not image:
                            image = 'public/images/devices/unknown-device.svg'
                        
                        return {
                            'brand': brand_name,
                            'model': model_name,
                            'tac': tac,
                            'alt_names': model_info.get('alt_names', []),
                            'image': image
                        }
        return None

class LookupLogger:
    def __init__(self, json_path):
        self.json_path = json_path
        self.ensure_log_file_exists()
    
    def ensure_log_file_exists(self):
        """Ensure the log file exists with proper structure."""
        if not os.path.exists(self.json_path):
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            initial_data = {
                "lookups": [],
                "stats": {
                    "total_lookups": 0,
                    "first_lookup": None,
                    "last_lookup": None
                }
            }
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
    
    def log_lookup(self, imei, tac, results):
        """Log an IMEI lookup with all results."""
        try:
            # Read current data
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            timestamp = datetime.now().isoformat()
            
            # Create lookup entry
            lookup_entry = {
                "timestamp": timestamp,
                "imei": imei,
                "tac": tac,
                "database_type": results.get('database_type'),
                "country": results.get('country'),
                "eyemei_device_info": results.get('eyemei_device_info'),
                "secondary_device_info": results.get('secondary_device_info'),
                "secondary_db_name": results.get('secondary_db_name'),
                "provider_checks": results.get('provider_checks', [])
            }
            
            # Add to lookups list
            data["lookups"].append(lookup_entry)
            
            # Update stats
            data["stats"]["total_lookups"] += 1
            data["stats"]["last_lookup"] = timestamp
            if data["stats"]["first_lookup"] is None:
                data["stats"]["first_lookup"] = timestamp
            
            # Keep only last 10000 lookups to prevent file from getting too large
            if len(data["lookups"]) > 10000:
                data["lookups"] = data["lookups"][-10000:]
            
            # Write back to file
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Logged lookup for IMEI: {imei[:4]}****{imei[-4:]} (Total lookups: {data['stats']['total_lookups']})")
            
        except Exception as e:
            logger.error(f"Error logging lookup: {e}")

class ExternalProviders:
    @staticmethod
    def check_telstra_3g(tac):
        """Check Telstra 3G compatibility (Australia)."""
        try:
            url = "https://www.telstrawholesale.com.au/bin/tw/TAC"
            data = {'tacnumber': tac}
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            raw_status = result.get('TACNUMBER', 'Unknown')
            
            if raw_status == 'WDA_Ref_Not_blocked':
                status = 'Not Blocked'
            elif raw_status == 'WDA_Ref_Blocked':
                status = 'Blocked'
            elif raw_status == 'Not Phone':
                status = 'Not Phone'
            elif raw_status == 'Unknown':
                status = 'Unknown'
            else:
                status = raw_status
            
            return {
                'provider': 'Telstra',
                'country': 'Australia',
                'status': status,
                'market_name': result.get('MarketName', 'Unknown'),
                'success': True
            }
        except Exception as e:
            logger.error(f"Telstra API error: {e}")
            return {
                'provider': 'Telstra',
                'country': 'Australia',
                'status': 'Error',
                'market_name': 'Unable to check',
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def check_amta_imei(imei):
        """Check AMTA IMEI compatibility (Australia - requires full IMEI)."""
        try:
            url = "https://amta.org.au/wp-admin/admin-ajax.php"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://amta.org.au/pages/amta/resources/3g-closure/',
            }
            data = {
                'action': 'imei_check',
                'imei': imei
            }
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success'):
                html_result = result.get('data', {}).get('result', '')
                
                device_name = 'Unknown'
                if html_result:
                    import re
                    clean_text = re.sub(r'<[^>]+>', '', html_result)
                    device_match = re.search(r'^([^.•]+?)(?:\s*[.•]|\s+OK|\s+–)', clean_text.strip())
                    if device_match:
                        device_name = device_match.group(1).strip()
                        if '•' in device_name:
                            parts = device_name.split('•')
                            if len(parts) >= 2 and parts[0].strip() == parts[1].strip():
                                device_name = parts[0].strip()
                
                if ('OK' in html_result or '<strong>OK</strong>' in html_result) and ("don't need to do anything" in html_result or "work normally" in html_result):
                    status = 'Compatible'
                elif 'NOT OK' in html_result or '<strong>NOT OK</strong>' in html_result:
                    status = 'Not Compatible'
                else:
                    status = 'Unknown'
                
                return {
                    'provider': 'AMTA',
                    'country': 'Australia',
                    'status': status,
                    'device_name': device_name,
                    'result_html': html_result,
                    'success': True
                }
            else:
                return {
                    'provider': 'AMTA',
                    'country': 'Australia',
                    'status': 'Error',
                    'device_name': 'Unknown',
                    'result_html': 'Unable to check',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"AMTA API error: {e}")
            return {
                'provider': 'AMTA',
                'country': 'Australia',
                'status': 'Error',
                'device_name': 'Unknown',
                'result_html': 'Unable to check',
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def check_att_imei(imei):
        """Check AT&T IMEI compatibility (USA - requires full IMEI)."""
        try:
            url = "https://www.att.com/msapi/sales/websalesdeviceorchms/v1/devices/validateimei"
            headers = {
                'accept': '*/*',
                'accept-language': 'en-AU,en-GB;q=0.9,en;q=0.8,en-US;q=0.7,fr-CH;q=0.6,fr-FR;q=0.5,fr;q=0.4',
                'cache-control': 'no-cache',
                'content-type': 'application/json',
                'dnt': '1',
                'origin': 'https://www.att.com',
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'referer': 'https://www.att.com/buy/prepaid-byod/',
                'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
            }
            
            cookies = {
                'AKA_A2': 'A',
                'at_check': 'true'
            }
            
            data = {
                "imei": imei,
                "paymentType": "prepaid",
                "stack": "UNIFIED",
                "cartExists": False,
                "mode": "byod"
            }
            
            response = requests.post(url, headers=headers, cookies=cookies, json=data, timeout=15)
            
            if response.status_code == 400:
                try:
                    result = response.json()
                    if 'error' in result and 'not compatible' in result['error'].get('message', '').lower():
                        return {
                            'provider': 'AT&T',
                            'country': 'USA',
                            'status': 'Not Compatible',
                            'device_name': 'Unknown',
                            'success': True
                        }
                    else:
                        return {
                            'provider': 'AT&T',
                            'country': 'USA',
                            'status': 'Error',
                            'device_name': 'Unknown',
                            'success': False,
                            'error': result.get('error', {}).get('message', 'Unknown error')
                        }
                except:
                    return {
                        'provider': 'AT&T',
                        'country': 'USA',
                        'status': 'Error',
                        'device_name': 'Unknown',
                        'success': False,
                        'error': f'Bad Request (400) - {response.text[:200]}'
                    }
            
            if response.status_code != 200:
                response.raise_for_status()
                
            result = response.json()
            
            if 'content' in result and 'deviceDetails' in result['content']:
                device_details = result['content']['deviceDetails']
                device_name = device_details.get('deviceFriendlyName', 'Unknown')
                if not device_name or device_name == 'Unknown':
                    make = device_details.get('make', '')
                    model = device_details.get('model', '')
                    if make and model:
                        device_name = f"{make} {model}".strip()
                
                sim_details = result['content'].get('simDetails', [])
                sim_support = []
                for sim in sim_details:
                    sim_type = sim.get('simType', '')
                    if sim_type == 'psim':
                        sim_support.append('Physical SIM')
                    elif sim_type == 'esimcard':
                        sim_support.append('eSIM')
                    elif sim_type:
                        sim_support.append(sim_type.upper())
                
                sim_support_text = ' + '.join(sim_support) if sim_support else 'Unknown'
                
                device_category = device_details.get('deviceCategoryType', 'Unknown')
                make = device_details.get('make', 'Unknown')
                model = device_details.get('model', 'Unknown')
                imei_type = device_details.get('imeiType', 'Unknown')
                
                return {
                    'provider': 'AT&T',
                    'country': 'USA',
                    'status': 'Compatible',
                    'device_name': device_name,
                    'device_category': device_category,
                    'make': make,
                    'model': model,
                    'imei_type': imei_type,
                    'sim_support': sim_support_text,
                    'sim_details': sim_support,
                    'success': True
                }
            
            else:
                return {
                    'provider': 'AT&T',
                    'country': 'USA',
                    'status': 'Unknown',
                    'device_name': 'Unknown',
                    'success': False,
                    'error': 'Unexpected response format'
                }
                
        except Exception as e:
            logger.error(f"AT&T API error: {e}")
            return {
                'provider': 'AT&T',
                'country': 'USA',
                'status': 'Error',
                'device_name': 'Unknown',
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_providers_for_country(country):
        """Get available providers for a specific country."""
        providers = {
            'australia': ['telstra', 'amta'],
            'usa': ['att'],
        }
        return providers.get(country.lower(), [])

eyemei_db = IMEIDatabase(EYEMEI_JSON_PATH)
osmocom_db = IMEIDatabase(OSMOCOM_JSON_PATH)
isthisphoneblocked_db = IMEIDatabase(ISTHISPHONEBLOCKED_JSON_PATH)
randommer_db = IMEIDatabase(RANDOMMER_JSON_PATH)
lookup_logger = LookupLogger(LOOKUP_LOG_JSON_PATH)

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/privacy-policy')
def privacy_policy():
    """Serve the privacy policy page."""
    return render_template('privacy-policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    """Serve the terms of service page."""
    return render_template('terms-of-service.html')

@app.route('/public/<path:filename>')
def serve_public_files(filename):
    """Serve files from the public directory."""
    return send_from_directory('public', filename)

@app.route('/api/lookup', methods=['POST'])
def lookup_imei():
    """Perform IMEI lookup."""
    data = request.get_json()
    imei = data.get('imei', '').strip()
    database_type = data.get('database_type', 'isthisphoneblocked')
    country = data.get('country', 'australia').lower()
    
    if not imei:
        return jsonify({'error': 'IMEI is required'}), 400
    
    if not imei.isdigit() or len(imei) != 15:
        return jsonify({'error': 'IMEI must be exactly 15 digits'}), 400
    
    tac = imei[:8]
    eyemei_device_info = eyemei_db.lookup_tac(tac)
    
    if database_type == 'osmocom':
        secondary_device_info = osmocom_db.lookup_tac(tac)
        secondary_db_name = 'OsmocomTAC'
    elif database_type == 'randommer':
        secondary_device_info = randommer_db.lookup_tac(tac)
        secondary_db_name = 'Randommer'
    else:
        secondary_device_info = isthisphoneblocked_db.lookup_tac(tac)
        secondary_db_name = 'IsThisPhoneBlocked'
    
    results = {
        'imei': imei,
        'tac': tac,
        'eyemei_device_info': eyemei_device_info,
        'secondary_device_info': secondary_device_info,
        'secondary_db_name': secondary_db_name,
        'database_type': database_type,
        'country': country,
        'provider_checks': []
    }
    
    available_providers = ExternalProviders.get_providers_for_country(country)
    
    if 'telstra' in available_providers:
        telstra_result = ExternalProviders.check_telstra_3g(tac)
        results['provider_checks'].append(telstra_result)
    
    if 'amta' in available_providers:
        amta_result = ExternalProviders.check_amta_imei(imei)
        results['provider_checks'].append(amta_result)
    
    if 'att' in available_providers:
        att_result = ExternalProviders.check_att_imei(imei)
        results['provider_checks'].append(att_result)
    
    if not available_providers:
        results['provider_checks'].append({
            'provider': 'No Providers Available',
            'country': country.title(),
            'status': 'No providers available for this country yet',
            'success': False,
            'error': f'No external providers are currently supported for {country.title()}'
        })
    
    # Log the lookup
    lookup_logger.log_lookup(imei, tac, results)
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
