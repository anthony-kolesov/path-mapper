class Point:
    def __init__(self, lat, lon, trackId):
        self.lat = lat
        self.lon = lon
        self.trackId = trackId

    @staticmethod
    def from_row(row):
        return Point(row[0], row[1], row[2])

