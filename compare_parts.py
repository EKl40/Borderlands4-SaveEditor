import os
import re
import csv
import sys

def extract_parts_from_file(filepath):
    parts = []
    # Try different encodings
    for enc in ['utf-8', 'utf-16', 'utf-16le', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                for line in f:
                    line = line.strip()
                    if line.lower().startswith('- part_'):
                        parts.append(line[2:].strip())
            break
        except UnicodeError:
            continue
            
    # Remove lowercase duplicates
    part_dict = {}
    for p in parts:
        low = p.lower()
        if low not in part_dict:
            part_dict[low] = []
        part_dict[low].append(p)
        
    final_parts = set()
    for low, variants in part_dict.items():
        if len(variants) > 1:
            # Pick one with uppercase letters if possible
            upper_variants = [v for v in variants if v != low]
            if upper_variants:
                final_parts.add(upper_variants[0])
            else:
                final_parts.add(variants[0])
        else:
            final_parts.add(variants[0])
            
    return final_parts

def get_prefixes_from_csv(csv_path):
    prefixes = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) > 5:
                    string_val = row[5]
                    if '.' in string_val:
                        prefix = string_val.split('.')[0]
                        prefixes.add(prefix)
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    # Also manual mappings just in case CSV is incomplete or hasn't loaded properly
    standard_manufacturers = ['TED', 'DAD', 'JAK', 'MAL', 'VLA', 'COV', 'BOR', 'ATL', 'TOR', 'ORD']
    standard_types = ['AR', 'PS', 'SG', 'SM', 'SR']
    for m in standard_manufacturers:
        for t in standard_types:
            prefixes.add(f"{m}_{t}")

    return prefixes

def load_raw_words(filepath):
    text = ""
    for enc in ['utf-8', 'utf-16', 'utf-16le', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                text = f.read()
            break
        except UnicodeError:
            continue
    # Extract all word-like tokens
    return set(re.findall(r'[A-Za-z0-9_]+', text))

def find_in_raw(new_part, raw_words, known_prefixes):
    if "unique" in new_part.lower():
        return new_part, None
        
    parts = new_part.split('_')
    # Use the last part as the specific name
    if len(parts) >= 3 and not (new_part.lower().startswith('part_body_ele_') or new_part.lower().startswith('part_scope_')):
        suffix = parts[-1]
    else:
        suffix = new_part
        
    # If suffix is just a single letter or number, it might be too generic.
    if len(suffix) <= 2 and len(parts) >= 4:
        suffix = parts[-2] + "_" + parts[-1]
        
    matches = [w for w in raw_words if suffix.lower() in w.lower()]
    
    # Sort known_prefixes by length desc to match most specific first
    sorted_prefixes = sorted(list(known_prefixes), key=len, reverse=True)
    
    for match in matches:
        for prefix in sorted_prefixes:
            if prefix.lower() in match.lower():
                return f"{prefix.upper()}.{new_part}", prefix.upper()
                
    # Fallback to dynamic matching (XXX_YY)
    for match in matches:
        m_parts = match.split('_')
        if len(m_parts) >= 3:
            if re.match(r'^[A-Za-z]{3}$', m_parts[0]) and re.match(r'^[A-Za-z]{2,3}$', m_parts[1]):
                prefix = f"{m_parts[0].upper()}_{m_parts[1].upper()}"
                return f"{prefix}.{new_part}", prefix
                
    return new_part, None

def main():
    base_dir = r"c:\Users\SuperExboom\Desktop\BL4\sav_edit"
    v8_path = os.path.join(base_dir, "sth", "v8.txt")
    v10_path = os.path.join(base_dir, "sth", "v10.txt")
    v10_raw_path = os.path.join(base_dir, "sth", "v10 raw.txt")
    csv_path = os.path.join(base_dir, "weapon_edit", "all_weapon_part.csv")
    
    print("Reading v8.txt...")
    v8_parts = extract_parts_from_file(v8_path)
    print("Reading v10.txt...")
    v10_parts = extract_parts_from_file(v10_path)
    
    v8_lower = {p.lower() for p in v8_parts}
    new_parts = [p for p in v10_parts if p.lower() not in v8_lower]
    
    new_parts.sort()
    
    print(f"Found {len(new_parts)} new parts in v10.")
    
    print("Loading prefixes and raw text...")
    prefixes = get_prefixes_from_csv(csv_path)
    raw_words = load_raw_words(v10_raw_path)
    
    PREFIX_TO_ID = {
        "DAD_PS": 2, "JAK_PS": 3, "ORD_PS": 4, "TED_PS": 5, "TOR_PS": 6,
        "BOR_SG": 7, "DAD_SG": 8, "JAK_SG": 9, "MAL_SG": 10, "TED_SG": 11, "TOR_SG": 12,
        "DAD_AR": 13, "TED_AR": 14, "ORD_AR": 15, "VLA_SR": 16, "TOR_AR": 17,
        "VLA_AR": 18, "BOR_SM": 19, "DAD_SM": 20, "MAL_SM": 21, "VLA_SM": 22,
        "BOR_SR": 23, "JAK_SR": 24, "MAL_SR": 25, "ORD_SR": 26, "JAK_AR": 27,
    }

    results = []
    print("Processing new parts...")
    for part in new_parts:
        full_name, prefix = find_in_raw(part, raw_words, prefixes)
        if prefix:
            wid = PREFIX_TO_ID.get(prefix, "X")
            
            # Extract specific name for comp_05_legendary string
            name_parts = part.split('_')
            specific_name = name_parts[-1] if len(name_parts) >= 3 else part
            
            comp_str = f'"{prefix}.comp_05_legendary_{specific_name}"'
            seq = f'{wid}, 0, 1, 50| 2, 1003|| {comp_str} "{prefix}.part_body" "{full_name}"'
            results.append(f'{full_name}\t{seq}')
        else:
            results.append(full_name)
        
    output_path = os.path.join(base_dir, "sth", "new_items_extracted.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        # Also print them sorted logically
        for r in results:
            f.write(r + "\n")
            
    print(f"Done. Extracted new items saved to {output_path}")

if __name__ == "__main__":
    main()
