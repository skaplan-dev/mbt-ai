import json


def create_station_index():
    file = open("./stations.json")
    rtStations = json.load(file)
    index = {}
    merged_stations = {
        **rtStations,
    }
    for line_data in merged_stations.values():
        for station in line_data["stations"]:
            for stop_direction, stops in station["stops"].items():
                for stop in stops:
                    index[stop] = station
    return index


station_index = create_station_index()


def get_station_by_id(station_stop_id: str):
    return station_index.get(station_stop_id)["stop_name"]
