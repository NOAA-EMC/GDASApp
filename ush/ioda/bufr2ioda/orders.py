def ORDERS(IN,ISORT,IDATA,INDEX,N,M,I1,I2):
    import numpy as np

    ICHEK = np.zeros(1, dtype=np.int64)
    RCHEK = np.zeros(1, dtype=np.float64)
    SMAL = np.zeros(1, dtype=np.float64)
    INDX = np.zeros(256, dtype=np.int64)
    KNDX = np.zeros(256, dtype=np.int64)

    ITYPE = IN % 10
    if IN < 10:
        INDEX = [i for i in range(1, N + 1)]

    if I1 == 4:
        if ITYPE == 0:
            IDATA = ORDEC4(IN,ISORT,IDATA,INDEX,N,M,I1,I2)
        else:
            IDATA = ORDER4(IN,ISORT,IDATA,INDEX,N,M,I1,I2)
        return IDATA
    elif I1 == 8:
        if ITYPE == 0:
            IDATA = ORDEC8(IN,ISORT,IDATA,INDEX,N,M,I1,I2)
        if ITYPE == 0:
            return
    elif I1 != 8:
        print('ORDERS argument i1 (keyword size) can be 4 or 8, but here it is ', i1)
        exit()
###
    if ITYPE > 0:
        SMAL = 1
        for I in range(N):
            ICHEK = IDATA[0, I]
            if ITYPE == 1 and ICHEK < SMAL:
                SMAL = ICHEK
            if ITYPE == 2 and RCHEK < SMAL:
                SMAL = RCHEK
       SMAL = 1 - SMAL
       for I in range(N):
            ICHEK = IDATA[0, I]
            if ITYPE == 1:
                ICHEK = ICHEK + SMAL
            if ITYPE == 2:
                RCHEK = RCHEK + SMAL
            IDATA[0, I] = ICHEK

    for IBYT in range(I1):
        KNDX[0] = 1
        for I in range(256):
            INDX[I] = 0

        for I in range(N):
            JBYT = (IData[0,INDEX[I]] >> (IBYT*8)) & 255
            INDX[JBYT] = INDX[JBYT] + 1
            ISORT[I] = INDEX[I]

        for I in range(1, 256):
            KNDX[I] = KNDX[I-1] + INDX[I-1]

        for I in range(N):
            JBYT = (IData[0,ISORT[I]] >> (IBYT*8)) & 255
            INDEX[KNDX[JBYT]] = ISORT[I]
            KNDX[JBYT] = KNDX[JBYT] + 1

    if ITYPE > 0:
        for i in range(N):
            ICHEK = IDATA[0][i]
            if ITYPE == 1:
                ICHEK = ICHEK - SMAL
            if ITYPE == 2:
                RCHEK = RCHEK - SMAL
            IDATA[0][i] = ICHEK


def order4(IN, ISORT, IDATA, INDEX, N, M, I1, I2):
    """
    Sorts the IDATA array using 4-byte integers.

    Args:
    Same as the ORDERS function

    Returns:
    None
    """
    ITYPE = IN % 10
    if IN < 10:
        INDEX = [i for i in range(1, N + 1)]

    if ITYPE > 0:
        SMAL = 1
        for i in range(N):
            ICHEK = IDATA[0][i]
            if ITYPE == 1 and ICHEK < SMAL:
                SMAL = ICHEK
            if ITYPE == 2 and RCHEK < SMAL:
                SMAL = RCHEK
        SMAL = 1 - SMAL
        for i in range(N):
            ICHEK = IDATA[0][i]
            if ITYPE == 1:
                ICHEK = ICHEK + SMAL
            if ITYPE == 2:
                RCHEK = RCHEK + SMAL
            IDATA[0][i] = ICHEK

    for IBYT in range(I1):
        KNDX = [1] * 256
        INDX = [0] * 256

        for i in range(N):
            JBYT = (IDATA[0][INDEX[i]] >> (IBYT * 8)) & 255
            INDX[JBYT] += 1
            ISORT[i] = INDEX[i]

        for i in range(1, 256):
            KNDX[i] = KNDX[i - 1] + INDX[i - 1]

        for i in range(N):
            JBYT = (IDATA[0][ISORT[i]] >> (IBYT * 8)) & 255
            INDEX[KNDX[JBYT]] = ISORT[i]
            KNDX[JBYT] += 1

    if ITYPE > 0:
        for i in range(N):
            ICHEK = IDATA[0][i]
            if ITYPE == 1:
                ICHEK = ICHEK - SMAL
            if ITYPE == 2:
                RCHEK = RCHEK - SMAL
            IDATA[0][i] = ICHEK


def ordec8(IN, ISORT, IDATA, INDEX, N, M, I1, I2):
    """
    Sorts the IDATA array using 8-byte characters.

    Args:
    Same as the ORDERS function

    Returns:
    None
    """
    ITYPE = IN % 10
    if IN < 10:
        INDEX = [i for i in range(1, N + 1)]

    for IBYT in range(I1):
        KNDX = [1] * 256
        INDX = [0] * 256
        II = I1 - IBYT

        for i in range(N):
            JBYT = ord(IDATA[0][INDEX[i]][II])
            INDX[JBYT] += 1
            ISORT[i] = INDEX[i]

        for i in range(1, 256):
            KNDX[i] = KNDX[i - 1] + INDX[i - 1]

        for i in range(N):
            JBYT = ord(IDATA[0][ISORT[i]][II])
            INDEX[KNDX[JBYT]] = ISORT[i]
            KNDX[JBYT] += 1


def ordec4(IN, ISORT, IDATA, INDEX, N, M, I1, I2):
    """
    Sorts the IDATA array using 4-byte characters.

    Args:
    Same as the ORDERS function

    Returns:
    None
    """
    ITYPE = IN % 10
    if IN < 10:
        INDEX = [i for i in range(1, N + 1)]

    for IBYT in range(I1):
        KNDX = [1] * 256
        INDX = [0] * 256
        II = I1 - IBYT

        for i in range(N):
            JBYT = ord(IDATA[0][INDEX[i]][II])
            INDX[JBYT] += 1
            ISORT[i] = INDEX[i]

        for i in range(1, 256):
            KNDX[i] = KNDX[i - 1] + INDX[i - 1]

        for i in range(N):
            JBYT = ord(IDATA[0][ISORT[i]][II])
            INDEX[KNDX[JBYT]] = ISORT[i]
            KNDX[JBYT] += 1
