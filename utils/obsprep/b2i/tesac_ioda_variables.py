import bufr
from b2iconverter.ioda_variables import IODAVariables


class TesacIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/BTOCN/DBSS')
        q.add('temp', '*/BTOCN/STMP')
        q.add('saln', '*/BTOCN/SALN')
        return q

    def filter(self):
        super().filter()
        # Separate TESAC profiles tesac tank
        id_mask = [True if id.isdigit() and id != 0 else False for id in self.metadata.stationID]
        mask = id_mask \
            & self.TemperatureFilter() \
            & self.SalinityFilter()
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
