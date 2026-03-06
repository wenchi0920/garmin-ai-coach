import fitparse

def get_start_location(file_path):
    fitfile = fitparse.FitFile(file_path)
    for m in fitfile.get_messages('record'):
        data = m.get_values()
        lat = data.get('position_lat')
        lon = data.get('position_long')
        if lat is not None and lon is not None:
            lat_deg = lat * (180.0 / 2**31)
            lon_deg = lon * (180.0 / 2**31)
            return lat_deg, lon_deg
    return None, None

file_path = '20251214-090222+0900.fit'
lat, lon = get_start_location(file_path)
print(f"Start GPS: {lat}, {lon}")
