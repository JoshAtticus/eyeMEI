#!/usr/bin/env python3
"""
eyeMEI Database Admin Panel
A web interface for reviewing lookup logs and managing the eyeMEI database.
"""

import json
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='admin_templates')

# Database paths
EYEMEI_JSON_PATH = 'databases/eyemei.json'
LOOKUP_LOG_JSON_PATH = 'databases/lookup_log.json'

class AdminDatabaseManager:
    def __init__(self, eyemei_path, lookup_log_path):
        self.eyemei_path = eyemei_path
        self.lookup_log_path = lookup_log_path
    
    def load_lookup_log(self):
        """Load the lookup log database."""
        try:
            if os.path.exists(self.lookup_log_path):
                with open(self.lookup_log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"lookups": [], "stats": {"total_lookups": 0}}
        except Exception as e:
            logger.error(f"Error loading lookup log: {e}")
            return {"lookups": [], "stats": {"total_lookups": 0}}
    
    def load_eyemei_db(self):
        """Load the eyeMEI database."""
        try:
            if os.path.exists(self.eyemei_path):
                with open(self.eyemei_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"brands": {}}
        except Exception as e:
            logger.error(f"Error loading eyeMEI database: {e}")
            return {"brands": {}}
    
    def save_eyemei_db(self, data):
        """Save the eyeMEI database."""
        try:
            with open(self.eyemei_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving eyeMEI database: {e}")
            return False
    
    def save_lookup_log(self, data):
        """Save the lookup log database."""
        try:
            with open(self.lookup_log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving lookup log: {e}")
            return False
    
    def get_pending_entries(self):
        """Get lookup entries that could be added to eyeMEI database."""
        lookup_data = self.load_lookup_log()
        eyemei_data = self.load_eyemei_db()
        
        # Get existing TACs from eyeMEI database
        existing_tacs = set()
        for brand_name, brand_info in eyemei_data.get('brands', {}).items():
            for model_dict in brand_info.get('models', []):
                for model_name, model_info in model_dict.items():
                    existing_tacs.update(model_info.get('tacs', []))
        
        # Find unique device info from lookup log
        pending_devices = {}
        for lookup in lookup_data.get('lookups', []):
            tac = lookup.get('tac')
            if not tac or tac in existing_tacs:
                continue
            
            # Try to get device info from various sources
            device_info = None
            device_name = "Unknown Device"
            brand_name = "Unknown Brand"
            
            # Check eyemei_device_info first
            if lookup.get('eyemei_device_info'):
                device_info = lookup['eyemei_device_info']
                brand_name = device_info.get('brand', 'Unknown Brand')
                device_name = device_info.get('model', 'Unknown Device')
            
            # Check secondary device info
            elif lookup.get('secondary_device_info'):
                device_info = lookup['secondary_device_info']
                brand_name = device_info.get('brand', 'Unknown Brand')
                device_name = device_info.get('model', 'Unknown Device')
            
            # Check provider results for device names
            else:
                for provider in lookup.get('provider_checks', []):
                    if provider.get('success') and provider.get('device_name'):
                        device_name = provider['device_name']
                        # Try to extract brand from device name
                        if ' ' in device_name:
                            potential_brand = device_name.split()[0]
                            if potential_brand.lower() not in ['unknown', 'device']:
                                brand_name = potential_brand
                        break
            
            # Create unique key for grouping
            device_key = f"{brand_name}:{device_name}"
            
            if device_key not in pending_devices:
                pending_devices[device_key] = {
                    'brand': brand_name,
                    'model': device_name,
                    'tacs': [],
                    'lookups': [],
                    'provider_info': []
                }
            
            pending_devices[device_key]['tacs'].append(tac)
            pending_devices[device_key]['lookups'].append({
                'timestamp': lookup.get('timestamp'),
                'imei': lookup.get('imei'),
                'country': lookup.get('country'),
                'database_type': lookup.get('database_type')
            })
            
            # Add provider information
            for provider in lookup.get('provider_checks', []):
                if provider.get('success'):
                    pending_devices[device_key]['provider_info'].append(provider)
        
        # Remove duplicates and sort
        for device in pending_devices.values():
            device['tacs'] = sorted(list(set(device['tacs'])))
            device['provider_info'] = list({json.dumps(p, sort_keys=True): p for p in device['provider_info']}.values())
        
        return list(pending_devices.values())
    
    def add_device_to_eyemei(self, brand, model, tacs, alt_names=None, image=""):
        """Add a device to the eyeMEI database."""
        try:
            eyemei_data = self.load_eyemei_db()
            
            if 'brands' not in eyemei_data:
                eyemei_data['brands'] = {}
            
            if brand not in eyemei_data['brands']:
                eyemei_data['brands'][brand] = {'models': []}
            
            # Create new model entry
            new_model = {
                model: {
                    'tacs': tacs if isinstance(tacs, list) else [tacs],
                    'alt_names': alt_names or [],
                    'image': image
                }
            }
            
            eyemei_data['brands'][brand]['models'].append(new_model)
            
            return self.save_eyemei_db(eyemei_data)
        except Exception as e:
            logger.error(f"Error adding device to eyeMEI: {e}")
            return False
    
    def remove_processed_lookups(self, tacs_to_remove):
        """Remove lookup entries for processed TACs."""
        try:
            lookup_data = self.load_lookup_log()
            original_count = len(lookup_data.get('lookups', []))
            
            # Filter out lookups with the specified TACs
            lookup_data['lookups'] = [
                lookup for lookup in lookup_data.get('lookups', [])
                if lookup.get('tac') not in tacs_to_remove
            ]
            
            removed_count = original_count - len(lookup_data['lookups'])
            logger.info(f"Removed {removed_count} lookup entries for processed TACs")
            
            return self.save_lookup_log(lookup_data)
        except Exception as e:
            logger.error(f"Error removing processed lookups: {e}")
            return False

# Initialize database manager
db_manager = AdminDatabaseManager(EYEMEI_JSON_PATH, LOOKUP_LOG_JSON_PATH)

@app.route('/')
def index():
    """Main admin panel page."""
    pending_devices = db_manager.get_pending_entries()
    lookup_data = db_manager.load_lookup_log()
    
    stats = {
        'total_lookups': len(lookup_data.get('lookups', [])),
        'pending_devices': len(pending_devices),
        'unique_tacs': len(set(lookup.get('tac') for lookup in lookup_data.get('lookups', []) if lookup.get('tac')))
    }
    
    return render_template('admin_index.html', 
                         pending_devices=pending_devices, 
                         stats=stats)

@app.route('/api/add_device', methods=['POST'])
def add_device():
    """Add a device to the eyeMEI database."""
    data = request.get_json()
    
    brand = data.get('brand', '').strip()
    model = data.get('model', '').strip()
    tacs = data.get('tacs', [])
    alt_names = data.get('alt_names', [])
    image = data.get('image', '').strip()
    
    if not brand or not model or not tacs:
        return jsonify({'success': False, 'error': 'Brand, model, and TACs are required'}), 400
    
    success = db_manager.add_device_to_eyemei(brand, model, tacs, alt_names, image)
    
    if success:
        # Remove processed lookups
        db_manager.remove_processed_lookups(tacs)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to add device'}), 500

@app.route('/api/ignore_device', methods=['POST'])
def ignore_device():
    """Remove device lookups without adding to database."""
    data = request.get_json()
    tacs = data.get('tacs', [])
    
    if not tacs:
        return jsonify({'success': False, 'error': 'TACs are required'}), 400
    
    success = db_manager.remove_processed_lookups(tacs)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to remove lookups'}), 500

@app.route('/api/lookup_details/<tac>')
def lookup_details(tac):
    """Get detailed lookup information for a specific TAC."""
    lookup_data = db_manager.load_lookup_log()
    
    details = []
    for lookup in lookup_data.get('lookups', []):
        if lookup.get('tac') == tac:
            details.append(lookup)
    
    return jsonify(details)

if __name__ == '__main__':
    # Create admin templates directory if it doesn't exist
    os.makedirs('admin_templates', exist_ok=True)
    app.run(debug=True, host='127.0.0.1', port=5002)
