import csv
import json
import os
import glob
from collections import defaultdict
from tqdm import tqdm

def load_existing_json(json_file_path):
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                print(f"📂 Loaded existing data from {json_file_path}")
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"⚠️  Could not load existing JSON, starting fresh")
    
    return {"brands": {}}

def clean_model_name(model_name, brand):
    cleaned = model_name.title()
    brand_variations = [
        brand.upper(),
        brand.lower(), 
        brand.title(),
        brand.capitalize()
    ]
    
    for brand_var in brand_variations:
        if cleaned.startswith(brand_var + " "):
            cleaned = cleaned[len(brand_var) + 1:].strip()
            break
        elif cleaned.startswith(brand_var):
            cleaned = cleaned[len(brand_var):].strip()
            break
    
    if brand.lower() == "apple":
        if cleaned.lower().startswith("iphone "):
            cleaned = "iPhone" + cleaned[6:]
        elif cleaned.lower() == "iphone":
            cleaned = "iPhone"
    
    cleaned = cleaned.strip(" -_")
    return cleaned if cleaned else model_name

def format_brand_name(brand):
    """
    Format brand name with proper capitalization rules
    
    Args:
        brand (str): Original brand name
        
    Returns:
        str: Formatted brand name
    """
    brand_lower = brand.lower().strip()
    
    special_cases = {
        'apple': 'Apple',
        'samsung': 'Samsung',
        'google': 'Google',
        'huawei': 'Huawei',
        'oneplus': 'OnePlus',
        'redmagic': 'RedMagic',
        'lg': 'LG',
        'htc': 'HTC',
        'sony': 'Sony',
        'nokia': 'Nokia',
        'motorola': 'Motorola',
        'xiaomi': 'Xiaomi',
        'oppo': 'Oppo',
        'vivo': 'Vivo',
        'nothing': 'Nothing'
    }
    
    if brand_lower in special_cases:
        return special_cases[brand_lower]
    
    return brand.capitalize()

def process_csv_to_json(csv_files, json_file_path):
    final_data = load_existing_json(json_file_path)
    brands_data = defaultdict(lambda: defaultdict(lambda: {
        'tacs': set(), 
        'alt_names': set(),
        'image': ""
    }))
    
    for brand_name, brand_data in final_data.get("brands", {}).items():
        for model_entry in brand_data.get("models", []):
            for model_name, model_info in model_entry.items():
                brands_data[brand_name][model_name]['tacs'].update(model_info.get('tacs', []))
                brands_data[brand_name][model_name]['alt_names'].update(model_info.get('alt_names', []))
                brands_data[brand_name][model_name]['image'] = model_info.get('image', "")
    
    total_files = len(csv_files)
    grand_total_rows = 0
    grand_processed_rows = 0
    
    print(f"📁 Found {total_files} CSV files to process")
    
    for file_idx, csv_file_path in enumerate(csv_files, 1):
        print(f"\n📄 Processing file {file_idx}/{total_files}: {os.path.basename(csv_file_path)}")
        total_rows = 0
        processed_rows = 0
        print("   Counting rows...")
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            total_rows = sum(1 for row in reader)
        
        grand_total_rows += total_rows
        print(f"   Found {total_rows} rows to process...")
        
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            with tqdm(total=total_rows, desc=f"   Processing {os.path.basename(csv_file_path)}") as pbar:
                for row in reader:
                    brand_raw = row['Brand'].strip()
                    optus_model = row['Optus Model Name'].strip()
                    telstra_model = row['Telstra Model Name'].strip()
                    model_info = row.get('Model Info', '').strip()
                    tac = row['TAC'].strip()
                    
                    if not brand_raw or not optus_model or not tac:
                        pbar.update(1)
                        continue
                    
                    brand = format_brand_name(brand_raw)
                    
                    if model_info:
                        raw_model_name = model_info
                    else:
                        raw_model_name = optus_model.title()
                    
                    model_name = clean_model_name(raw_model_name, brand)
                    
                    if len(tac) == 8 and tac.isdigit():
                        brands_data[brand][model_name]['tacs'].add(tac)
                    
                    if telstra_model and telstra_model != "N/A":
                        cleaned_telstra = clean_model_name(telstra_model, brand)
                        if cleaned_telstra and cleaned_telstra != model_name:
                            brands_data[brand][model_name]['alt_names'].add(cleaned_telstra)
                    
                    if model_info and optus_model:
                        cleaned_optus = clean_model_name(optus_model.title(), brand)
                        if cleaned_optus and cleaned_optus != model_name:
                            brands_data[brand][model_name]['alt_names'].add(cleaned_optus)
                    
                    processed_rows += 1
                    pbar.update(1)
        
        grand_processed_rows += processed_rows
        print(f"   ✅ Processed {processed_rows} rows from {os.path.basename(csv_file_path)}")
    
    final_data = {"brands": {}}
    
    total_brands = 0
    total_models = 0
    total_tacs = 0
    
    print(f"\n📊 Structuring data from all {total_files} files...")
    
    for brand, models in tqdm(brands_data.items(), desc="Processing brands"):
        total_brands += 1
        final_data["brands"][brand] = {"models": []}
        
        for model_name, model_data in models.items():
            if model_data['tacs']:
                total_models += 1
                total_tacs += len(model_data['tacs'])
                
                model_entry = {
                    model_name: {
                        "tacs": sorted(list(model_data['tacs'])),
                        "alt_names": sorted(list(model_data['alt_names'])),
                        "image": model_data['image']
                    }
                }
                final_data["brands"][brand]["models"].append(model_entry)
    
    print(f"\n💾 Writing data to {json_file_path}...")
    with open(json_file_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(final_data, jsonfile, indent=4, ensure_ascii=False)
    
    print("\n" + "="*60)
    print("🎉 PROCESSING COMPLETE!")
    print("="*60)
    print(f"📁 Total CSV files processed: {total_files}")
    print(f"📊 Total rows processed: {grand_processed_rows:,} (from {grand_total_rows:,} total)")
    print(f"🏢 Total brands: {total_brands}")
    print(f"📱 Total device models: {total_models}")
    print(f"🔢 Total TACs: {total_tacs:,}")
    print(f"💾 Output file: {json_file_path}")
    print("="*60)
    
    return total_brands, total_models, total_tacs

def main():
    """Main function"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = script_dir
    json_file = os.path.join(os.path.dirname(script_dir), "isthisphoneblocked.json")
    csv_pattern = os.path.join(raw_data_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)
    
    if not csv_files:
        print(f"❌ Error: No CSV files found in {raw_data_dir}")
        return
    
    print("🚀 Starting IsThisPhoneBlocked data processing...")
    print(f"📁 Raw data directory: {raw_data_dir}")
    print(f"📁 Output JSON: {json_file}")
    print(f"📂 Found CSV files:")
    for i, csv_file in enumerate(csv_files, 1):
        print(f"   {i}. {os.path.basename(csv_file)}")
    print()
    
    try:
        brands, models, tacs = process_csv_to_json(csv_files, json_file)
        
        if os.path.exists(json_file):
            file_size = os.path.getsize(json_file)
            print(f"✅ Success! File created/updated successfully ({file_size:,} bytes)")
        else:
            print("❌ Error: Output file was not created")
            
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        raise

if __name__ == "__main__":
    main()
