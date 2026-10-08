def point_inside_aoi(
    lat: float,
    lon: float,
    center_lat: float,
    center_lon: float,
    buffer_deg: float,
) -> bool:
    return abs(lat - center_lat) <= buffer_deg and abs(lon - center_lon) <= buffer_deg
