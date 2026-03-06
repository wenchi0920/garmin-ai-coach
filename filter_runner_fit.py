#!/usr/bin/env python3
import os
import sys
import argparse
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import fitparse

# Purpose: Filter and rename .fit files to a consistent format.
# Only running records are kept.
# Format: YYYYMMDD-HHMMSS+offset.fit

def get_fit_info(file_path):
    try:
        fitfile = fitparse.FitFile(file_path)
        is_running = False
        start_time_utc = None
        offset_hours = 8 # Default for Taiwan if detection fails
        
        # Check if it's running
        for session in fitfile.get_messages('session'):
            sport = session.get_value('sport')
            if sport == 'running':
                is_running = True
                start_time_utc = session.get_value('start_time')
            if is_running:
                break
        
        if not is_running:
            return False, None, None, None
        
        # Detect timezone offset
        found_offset = False
        for activity in fitfile.get_messages('activity'):
            local_ts = activity.get_value('local_timestamp')
            utc_ts = activity.get_value('timestamp')
            if local_ts and utc_ts:
                # Calculate offset in hours
                diff = local_ts - utc_ts
                offset_hours = round(diff.total_seconds() / 3600)
                found_offset = True
                break
        
        if start_time_utc:
            local_start_time = start_time_utc + timedelta(hours=offset_hours)
            return True, local_start_time, offset_hours, True
        
        return False, None, None, True
    except (fitparse.utils.FitHeaderError, fitparse.utils.FitEOFError):
        return False, None, None, False
    except Exception as e:
        print(f"Error parsing FIT file {file_path}: {e}")
        return False, None, None, False

def get_gpx_info(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        
        # Check if it's running
        # Usually looking at the track name or type
        is_running = False
        track_name = root.find('.//gpx:trk/gpx:name', ns)
        if track_name is not None and ('跑' in track_name.text or 'Run' in track_name.text):
            is_running = True
        
        if not is_running:
            return False, None, None
        
        # Get start time
        first_pt_time = root.find('.//gpx:trkpt/gpx:time', ns)
        if first_pt_time is not None:
            # Format: 2023-10-21T21:28:19Z
            utc_time = datetime.strptime(first_pt_time.text, "%Y-%m-%dT%H:%M:%SZ")
            # For GPX, we assume +0800 if it matches the name's date
            # In 2023_長榮馬.fit, UTC is 10-21 21:28, name is 20231022. So +8h makes sense.
            offset_hours = 8
            local_time = utc_time + timedelta(hours=offset_hours)
            return True, local_time, offset_hours
            
        return False, None, None
    except Exception as e:
        # print(f"Error parsing GPX file {file_path}: {e}")
        return False, None, None

def process_file(file_path, folder_path):
    filename = os.path.basename(file_path)
    
    # Check if already in target format
    # 20240913-235534+0800.fit
    pattern = r'^\d{8}-\d{6}[+-]\d{4}\.fit$'
    is_correct_format = bool(re.match(pattern, filename))
    
    # Even if correct format, we should check if it's running (according to RENAME.md point 2)
    # But RENAME.md point 1 says "只要不是 ... 的格式，就讀取 *.fit"
    # This implies we might skip re-parsing if the format is correct.
    # However, "非跑步的紀錄要刪除檔案" is a general rule.
    # To be safe, we check everything.
    
    is_running, local_time, offset, is_fit = get_fit_info(file_path)
    
    if not is_fit and filename.endswith('.fit'):
        # Try GPX
        is_running, local_time, offset = get_gpx_info(file_path)
    
    if not is_running:
        print(f"Deleting non-running file: {filename}")
        os.remove(file_path)
        return

    # Generate new filename
    offset_str = f"{offset:+03d}00" # e.g. +0800
    new_filename = local_time.strftime(f"%Y%m%d-%H%M%S{offset_str}.fit")
    
    if filename != new_filename:
        new_path = os.path.join(folder_path, new_filename)
        if os.path.exists(new_path):
            print(f"Target already exists, deleting duplicate: {filename} (target: {new_filename})")
            os.remove(file_path)
        else:
            print(f"Renaming {filename} -> {new_filename}")
            os.rename(file_path, new_path)

def main():
    parser = argparse.ArgumentParser(description='Filter and rename runner FIT files.')
    parser.add_argument('path', help='Path to a folder or a .fit file')
    args = parser.parse_args()

    if os.path.isdir(args.path):
        for f in os.listdir(args.path):
            if f.endswith('.fit'):
                process_file(os.path.join(args.path, f), args.path)
    elif os.path.isfile(args.path):
        if args.path.endswith('.fit'):
            process_file(args.path, os.path.dirname(args.path))
    else:
        print(f"Error: Path {args.path} not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
