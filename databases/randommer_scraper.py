# this script is not very good, it has fixed cookies and does not handle failed requests well
# if you're using this you'll need to go to https://randommer.io/imei-generator, make a request
# and get ur own cf_clearance cookie from the browser dev tools because they expire after a while
# and they're also ip specific
#
# this script is also like 99% ai generated because i was too lazy to do it myself
# randommer seems to have imei tacs for devices up to 2019, newer than osmocom, older than eyeMEI
# and isthisphoneblocked, it also has a bunch of duplicates and bad data
# (one of my favourite brands is Apple iPhone 4s, which should be a model
# but is actually a brand for reasons and stuff)
#
# the data from randommer isn't useful for anything by itself, it needs to be cleaned up
# and possibly merged into the eyeMEI db, like I've started doing with the isthisphoneblocked one

import requests
import json
import time
import os
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor
import queue
try:
    from colorama import init, Fore, Style, Cursor
    init(autoreset=True)  # Initialize colorama for Windows
    COLORS_AVAILABLE = True
except ImportError:
    print("Warning: colorama not installed. Install with 'pip install colorama' for colored output.")
    COLORS_AVAILABLE = False
    # Fallback empty strings if colorama not available
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = ""
    class Style:
        RESET_ALL = ""
    class Cursor:
        UP = DOWN = ""


class RandommerScraper:
    def __init__(self):
        self.url = "https://randommer.io/imei-generator"
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-AU,en-GB;q=0.9,en;q=0.8,en-US;q=0.7,fr-CH;q=0.6,fr-FR;q=0.5,fr;q=0.4",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "dnt": "1",
            "origin": "https://randommer.io",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"134.0.6998.207"',
            "sec-ch-ua-full-version-list": '"Chromium";v="134.0.6998.207", "Not:A-Brand";v="24.0.0.0", "Google Chrome";v="134.0.6998.207"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"19.0.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        
        self.cookies = {
            "ezosuibasgeneris-1": "d7bb0c83-79e5-4789-4efc-f65d83421ec2",
            "_ez_retention_enabled": "false",
            "cf_clearance": "2O77OyElNhROiMzaHhw5sltzul0tybT5Rz10tw.BwKE-1754113504-1.2.1.1-3VJJJWxFeoSPNL4PN67ckbkakPuuDSN6rEIuhAuLSEW6yWv2jNO9iAUHXUcCzRWDzKbVOpvAHwZeoJ1vJSxOERyZIvi2AXIez6rIx2INvcul5omHYnTy6hAIu9LFi9VYymiQd4XoMyo_Vt5GHx8YFG.DQnqD2G5Viz0y.QqrWMtWWzl6p_7ZB71VXU1SasgTSBGA2tfQg8eXGZniX0TxSP0LWvefr23bIxMwX_Lq97g",
            "ezoictest": "stable",
            "ezopvc_232529": "1",
            "ezoab_232529": "mod255",
            "active_template::232529": "pub_site.1753357098",
            "ezoadgid_232529": "-1"
        }
        
        self.data = "id=1&X-Requested-With=XMLHttpRequest"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.database_path = os.path.join(script_dir, "randommer.json")
        self.database = {"brands": {}}
        self.database_lock = threading.Lock()
        self.save_queue = queue.Queue()
        self.status_line_shown = False
        self.current_request_count = 0
        self.current_new_additions = 0
        self.load_existing_database()
        
    def load_existing_database(self):
        """Load existing database if it exists"""
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    self.database = json.load(f)
                print(f"Loaded existing database with {len(self.database.get('brands', {}))} brands")
            except Exception as e:
                print(f"Error loading existing database: {e}")
                self.database = {"brands": {}}
        else:
            print("Creating new database...")
            dir_path = os.path.dirname(self.database_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
    
    def make_request(self):
        """Make a single request to the API"""
        try:
            response = requests.post(
                self.url,
                headers=self.headers,
                cookies=self.cookies,
                data=self.data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print(f"{Fore.RED}❌ Error 403: Access forbidden. You need to get a new cf_clearance cookie from your browser!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}💡 Go to https://randommer.io/imei-generator, make a request, and copy the new cf_clearance cookie from browser dev tools{Style.RESET_ALL}")
                return None
            else:
                print(f"{Fore.RED}❌ Request failed with status code: {response.status_code}{Style.RESET_ALL}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}❌ Request error: {e}{Style.RESET_ALL}")
            return None
    
    def extract_tac(self, imei):
        """Extract TAC (first 8 digits) from IMEI"""
        return imei[:8] if len(imei) >= 8 else imei
    
    def normalize_brand(self, brand):
        """Normalize brand name - handle case insensitive duplicates"""
        if not brand or brand.strip().lower() in ['not found', 'unknown', 'n/a', '', 'null']:
            return None
            
        brand = brand.strip()
        
        for existing_brand in self.database["brands"]:
            if existing_brand.lower() == brand.lower():
                return existing_brand
        
        return brand
    
    def clean_model_name(self, model, brand):
        """Clean model name by removing brand prefix and invalid values"""
        if not model or model.strip().lower() in ['not found', 'unknown', 'n/a', '', 'null']:
            return None
            
        model = model.strip()
        
        if brand and model.lower().startswith(brand.lower()):
            model = model[len(brand):].strip()
            
        if not model:
            return None
            
        return model
    
    def add_to_database(self, brand, model, imei):
        """Add device data to database in eyemei.json format - only adds new TACs"""
        tac = self.extract_tac(imei)
        
        normalized_brand = self.normalize_brand(brand)
        if not normalized_brand:
            self.log_message(f"{Fore.RED}❌ Skipping invalid brand: '{brand}'{Style.RESET_ALL}")
            return False
            
        cleaned_model = self.clean_model_name(model, normalized_brand)
        if not cleaned_model:
            self.log_message(f"{Fore.RED}❌ Skipping invalid model: '{model}' for brand '{normalized_brand}'{Style.RESET_ALL}")
            return False
        
        with self.database_lock:
            if normalized_brand not in self.database["brands"]:
                self.database["brands"][normalized_brand] = {"models": []}
                self.log_message(f"{Fore.CYAN}🆕 New brand added: {normalized_brand}{Style.RESET_ALL}")
            
            model_found = False
            tac_added = False
            for model_entry in self.database["brands"][normalized_brand]["models"]:
                for model_name, model_data in model_entry.items():
                    if model_name == cleaned_model:
                        if tac not in model_data["tacs"]:
                            model_data["tacs"].append(tac)
                            self.log_message(f"{Fore.GREEN}✅ Added TAC {tac} to existing model: {normalized_brand} {cleaned_model}{Style.RESET_ALL}")
                            tac_added = True
                        else:
                            self.log_message(f"{Fore.YELLOW}🔄 TAC {tac} already exists for model: {normalized_brand} {cleaned_model}{Style.RESET_ALL}")
                        model_found = True
                        break
                if model_found:
                    break
            
            if not model_found:
                new_model = {
                    cleaned_model: {
                        "tacs": [tac]
                    }
                }
                self.database["brands"][normalized_brand]["models"].append(new_model)
                self.log_message(f"{Fore.CYAN}🆕 New device added: {normalized_brand} {cleaned_model} with TAC {tac}{Style.RESET_ALL}")
                tac_added = True
            
            return tac_added
    
    def save_database(self):
        """Save database to file - thread safe"""
        try:
            with self.database_lock:
                with open(self.database_path, 'w', encoding='utf-8') as f:
                    json.dump(self.database, f, indent=4, ensure_ascii=False)
                self.log_message(f"💾 Database saved to {self.database_path}")
        except Exception as e:
            self.log_message(f"{Fore.RED}❌ Error saving database: {e}{Style.RESET_ALL}")
    
    def process_request(self):
        """Process a single request - used for threading"""
        data = self.make_request()
        if data:
            brand = data.get("brand", "Unknown")
            model = data.get("model", "Unknown")
            imei = data.get("imei", "")
            return brand, model, imei
        return None
    
    def get_stats(self):
        """Get current database statistics"""
        total_brands = len(self.database["brands"])
        total_models = 0
        total_tacs = 0
        
        for brand_data in self.database["brands"].values():
            total_models += len(brand_data["models"])
            for model_entry in brand_data["models"]:
                for model_data in model_entry.values():
                    total_tacs += len(model_data["tacs"])
        
        return total_brands, total_models, total_tacs
    
    def update_status_line(self, request_count, new_additions):
        """Update the persistent status line at the bottom"""
        self.current_request_count = request_count
        self.current_new_additions = new_additions
        brands, models, tacs = self.get_stats()
        status = f"{Fore.MAGENTA}📊 Live Stats: {Fore.CYAN}Requests: {request_count} | {Fore.GREEN}New: {new_additions} | {Fore.CYAN}Brands: {brands} | Models: {models} | TACs: {tacs}{Style.RESET_ALL}"
        
        if self.status_line_shown:
            # Move cursor up and clear the line, then print status
            print(f"\033[1A\033[2K{status}")
        else:
            print(status)
            self.status_line_shown = True
    
    def log_message(self, message):
        """Print a log message above the status line"""
        if self.status_line_shown:
            # Move cursor up, clear line, print message
            print(f"\033[1A\033[2K{message}")
            # Re-print the status line with current stats
            brands, models, tacs = self.get_stats()
            status = f"{Fore.MAGENTA}📊 Live Stats: {Fore.CYAN}Requests: {self.current_request_count} | {Fore.GREEN}New: {self.current_new_additions} | {Fore.CYAN}Brands: {brands} | Models: {models} | TACs: {tacs}{Style.RESET_ALL}"
            print(status)
        else:
            print(message)
            # If this is the first message and no status line yet, show status line after
            if not self.status_line_shown:
                self.update_status_line(self.current_request_count, self.current_new_additions)
    
    def run(self):
        """Main scraping loop with multithreading"""
        print("Starting IMEI scraper with multithreading...")
        print("Press Ctrl+C to stop and save data")
        print(f"Database will be saved to: {self.database_path}")
        print("-" * 50)
        
        request_count = 0
        save_interval = 25
        max_workers = 3
        new_additions = 0
        
        # Initialize status line
        self.update_status_line(request_count, new_additions)
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                while True:
                    futures = [executor.submit(self.process_request) for _ in range(max_workers)]
                    
                    for future in futures:
                        try:
                            result = future.result(timeout=30)
                            if result:
                                brand, model, imei = result
                                request_count += 1
                                
                                # Don't print regular request info, just log important events
                                
                                was_new = self.add_to_database(brand, model, imei)
                                if was_new:
                                    new_additions += 1
                                
                                # Update status line with current stats
                                self.update_status_line(request_count, new_additions)
                                
                                # Auto-save periodically
                                if new_additions > 0 and new_additions % save_interval == 0:
                                    self.save_database()
                            else:
                                self.log_message(f"{Fore.RED}❌ Failed to get data from one request...{Style.RESET_ALL}")
                                self.update_status_line(request_count, new_additions)
                                
                        except Exception as e:
                            self.log_message(f"{Fore.RED}❌ Request failed: {e}{Style.RESET_ALL}")
                            self.update_status_line(request_count, new_additions)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⏹️  Stopping scraper...{Style.RESET_ALL}")
            self.save_database()
            brands, models, tacs = self.get_stats()
            print(f"\n{Fore.MAGENTA}📈 Final stats:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Total requests made: {request_count}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}New additions: {new_additions}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Brands: {brands}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Models: {models}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}TACs: {tacs}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Database saved to: {self.database_path}{Style.RESET_ALL}")

if __name__ == "__main__":
    scraper = RandommerScraper()
    scraper.run()
