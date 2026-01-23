import os
from PIL import Image
from PIL.ExifTags import TAGS

def check_metadata(file_path):
    print(f"Checking: {file_path}")
    try:
        img = Image.open(file_path)
        info = img.info
        
        # Check standard PNG info keys
        if 'Copyright' in info:
            print(f"  [FOUND] Copyright: {info['Copyright']}")
        elif 'Rights' in info:
            print(f"  [FOUND] Rights: {info['Rights']}")
        elif 'Author' in info:
            print(f"  [FOUND] Author: {info['Author']}")
        else:
            # Check EXIF data if present (less common in PNGs but possible)
            exif_data = img.getexif()
            found = False
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == 'Copyright' or tag == 'Artist' or tag == 'UserComment':
                        print(f"  [FOUND] EXIF {tag}: {value}")
                        found = True
            
            if not found:
                print("  [CLEAN] No obvious copyright tags found in metadata.")
                # Print all keys just in case
                if info:
                    print(f"  All Info Keys: {list(info.keys())}")
                else:
                    print("  No metadata dictionary found.")

    except Exception as e:
        print(f"  [ERROR] Could not read metadata: {e}")

base_path = r"C:\Users\golde\source\repos\meow\assets\img"
files_to_check = [
    os.path.join(base_path, "1119", "80144-FM Boulder 10.png"),
    os.path.join(base_path, "1639", "162870-SDTC Chimney 1 2x1.png"),
    os.path.join(base_path, "2121", "636769-VTDM Alcove Large 1 4x4.png"),
    os.path.join(base_path, "hextiles1", "1142315-Marshland 1 .png"),
    os.path.join(base_path, "hextiles2", "1232666-Highland 1 .png")
]

for f in files_to_check:
    check_metadata(f)
