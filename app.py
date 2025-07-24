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
CORS(app)
EYEMEI_JSON_PATH = 'databases/eyemei.json'
OSMOCOM_JSON_PATH = 'databases/osmocom.json'
ISTHISPHONEBLOCKED_JSON_PATH = 'databases/isthisphoneblocked.json'
RANDOMMER_JSON_PATH = 'databases/randommer.json'

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

class ExternalProviders:
    @staticmethod
    def check_telstra_3g(tac):
        """Check Telstra 3G compatibility."""
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
                'status': status,
                'market_name': result.get('MarketName', 'Unknown'),
                'success': True
            }
        except Exception as e:
            logger.error(f"Telstra API error: {e}")
            return {
                'provider': 'Telstra',
                'status': 'Error',
                'market_name': 'Unable to check',
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def check_amta_imei(imei):
        """Check AMTA IMEI compatibility (requires full IMEI)."""
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
                    'status': status,
                    'device_name': device_name,
                    'result_html': html_result,
                    'success': True
                }
            else:
                return {
                    'provider': 'AMTA',
                    'status': 'Error',
                    'device_name': 'Unknown',
                    'result_html': 'Unable to check',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"AMTA API error: {e}")
            return {
                'provider': 'AMTA',
                'status': 'Error',
                'device_name': 'Unknown',
                'result_html': 'Unable to check',
                'success': False,
                'error': str(e)
            }

eyemei_db = IMEIDatabase(EYEMEI_JSON_PATH)
osmocom_db = IMEIDatabase(OSMOCOM_JSON_PATH)
isthisphoneblocked_db = IMEIDatabase(ISTHISPHONEBLOCKED_JSON_PATH)
randommer_db = IMEIDatabase(RANDOMMER_JSON_PATH)

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
        'provider_checks': []
    }
    
    telstra_result = ExternalProviders.check_telstra_3g(tac)
    results['provider_checks'].append(telstra_result)
    
    amta_result = ExternalProviders.check_amta_imei(imei)
    results['provider_checks'].append(amta_result)
    
    return jsonify(results)

@app.route('/api/privacy-info')
def privacy_info():
    """Return privacy information."""
    return jsonify({
        'tac_only_providers': ['Telstra'],
        'full_imei_providers': ['AMTA'],
        'data_storage': 'eyeMEI only stores TACs to improve its database. No full IMEIs or personal data are stored.',
        'explanation': {
            'tac': 'TAC (Type Allocation Code) is the first 8 digits of an IMEI and identifies the device model, not your specific device.',
            'full_imei': 'Full IMEI is required by some providers for exact device matching and compatibility checks.'
        }
    })

@app.route('/api/database-stats')
def database_stats():
    """Return database statistics."""
    def get_db_stats(db):
        brands_data = db.data.get('brands', {})
        total_brands = len(brands_data)
        total_models = 0
        total_tacs = 0
        
        for brand_name, brand_info in brands_data.items():
            models = brand_info.get('models', [])
            total_models += len(models)
            for model_dict in models:
                for model_name, model_info in model_dict.items():
                    tacs = model_info.get('tacs', [])
                    total_tacs += len(tacs)
        
        return {
            'brands': total_brands,
            'models': total_models,
            'tacs': total_tacs
        }
    
    return jsonify({
        'eyemei': get_db_stats(eyemei_db),
        'isthisphoneblocked': get_db_stats(isthisphoneblocked_db),
        'osmocom': get_db_stats(osmocom_db),
        'randommer': get_db_stats(randommer_db),
        'last_updated': datetime.now().strftime('%d %B %Y')
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
