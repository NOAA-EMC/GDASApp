'''
Understanding WMO Identifiers for Tropical Moorings

    WMO Identifiers:
        Old Format (5-digit): Used historically for ocean platforms (e.g., moored buoys, drifting buoys) in the form A1bwnnn, where:
            A1: Region (e.g., 4 for Asia, 7 for North America, 8 for South America).
            bw: Platform type or subregion (e.g., 6 for moored buoys in some contexts).
            nnn: Station number (000–999).
            Example: 64787 (A1=6, bw=4, nnn=787) for a moored buoy.
        New Format (7-digit): Introduced to expand identifier capacity,
        especially for BUFR (Binary Universal Form for the Representation
        of meteorological data). The format is A1bwnnnnn, where:
            A1: Region (same as above).
            bw: Platform type/subregion.
            nnnnn: Station number (00000–99999, up to 5 digits).
            Conversion rule: Most 5-digit IDs are mapped to 7-digit by inserting “00” in the 3rd and 4th positions (e.g., 64787 → 6400787).
        WIGOS Station Identifiers (WSI): Modern WMO identifiers
        use a 4-block structure (e.g., 0-22000-0-3100007 for
        a USA moored buoy in WMO area 31).
        The 7-digit format aligns with BUFR reporting but
        may not always map directly to WSI’s local identifier block.
    Tropical Moorings:
        These are moored buoys in arrays like TAO/TRITON (Pacific),
        PIRATA (Atlantic), or RAMA (Indian Ocean), reporting via
        GTS in BUFR format (e.g., IOBX08 KPML).
        WMO numbers for modern T-Flex moorings (replacing ATLAS)
        use 7-digit analogs of older 5-digit codes at the same
        site (e.g., 23010 → 2300010 for a RAMA mooring at 4°S 81°E)
'''


# Function to convert 5-digit to 7-digit WMO code
def convert_5_to_7_digit(wmo_5digit):
    """
    If the code is already 7 digits, it is returned as is.
    Convert a 5-digit WMO code (A1bwnnn) to 7-digit (A1bwnnnnn)
    by inserting '00' after bw.
    Returns the 7-digit code as a string.
    """
    if len(wmo_5digit) == 7:
        return wmo_5digit
    if not wmo_5digit.isdigit() or len(wmo_5digit) != 5:
        return None  # Invalid 5-digit code
    # Extract A1, bw, nnn
    a1 = wmo_5digit[0]
    bw = wmo_5digit[1]
    nnn = wmo_5digit[2:]
    # Convert to 7-digit: A1 + bw + '00' + nnn
    wmo_7digit = f"{a1}{bw}00{nnn}"
    return wmo_7digit


TAO_TRITON = [
    4300011,
    4300008,
    4300301,
    3200303,
    3200011,
    3200320,
    3200321,
    3200322,
    3200304,
    3200305,
    4300001,
    3200315,
    3200316,
    3200323,
    3200317,
    3200318,
    3200319,
    5100307,
    5100015,
    5100016,
    5100011,
    5100017,
    5100018,
    5100308,
    5100013,
    5100006,
    5100007,
    5100008,
    5100311,
    5100009,
    5100014,
    5100012,
    5100301,
    5100020,
    5100021,
    5100023,
    5100022,
    5100019,
    5100302,
    5100309,
    5100303,
    5100305,
    5100010,
    5100306,
    5100304,
    5100310,
    5200315,
    5200309,
    5200310,
    5200311,
    5200312,
    5200313,
    5200316,
    5200303,
    5200006,
    5200003,
    5200001,
    5200321,
    5200002,
    5200004,
    5200007,
    5200304,
    5200308,
    5200083,
    5200319,
    5200084,
    5200008,
    5200082,
    5200011,
    5200085,
    5200317,
    5200088,
    5200012,
    5200086,
    5200010,
    5200305,
    5200078,
    5200302,
    5200077,
    5200301,
    5200079,
    5200318,
    5200306,
    5200087,
    5200320,
    5200073,
    5200314,
    5200080,
    5200307,
    5200081
]

PIRATA = [
    1300001,
    1300002,
    1300008,
    1300009,
    1300010,
    1300011,
    1500007,
    1500001,
    1500002,
    1500003,
    1500005,
    1500006,
    1500008,
    1500009,
    3100001,
    3100002,
    3100003,
    3100004,
    3100005,
    3100006,
    3100007,
    4100139,
    4100026
]

RAMA = [
    5600055,
    5300056,
    5300040,
    5300009,
    2300009,
    2300008,
    2300007,
    2300006,
    2300005,
    2300004,
    5300057,
    2300002,
    2300001,
    2300003,
    2300010,
    5300005,
    5300006,
    5600053,
    2300011,
    2300012,
    2300013,
    2300014,
    2300015,
    2300016,
    2300017,
    1400040,
    1400043,
    2300019,
    1400048,
    1400049,
    1400047,
    1400041,
    1400042,
    1400046
]
