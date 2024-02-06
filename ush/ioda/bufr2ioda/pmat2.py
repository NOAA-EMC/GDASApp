import numpy as np

def ldltb(m, mah1, a):
    """
    float version of [ldltb]
    """
    for j in range(m):
        imost = min(m, j + mah1)
        jp = j + 1
        ajj = a[j, 0]
        if ajj == 0:
            print("Fails in LDLTB: Matrix requires pivoting or is singular")
            exit()
        ajji = 1.0 / ajj
        a[j, 0] = ajji
        for i in range(jp, imost):
            aij = a[i, j - i]
            a[i, j - i] = ajji * aij
            for k in range(jp, i + 1):
                a[i, k - i] -= aij * a[k, j - k]

    return a

def ltdlbv(m, mah1, a, v):
    """
    Function equivalent of the Fortran subroutine [ltdlbv]
    """
    a = a
    for j in range(m):
        vj = v[j]
        for i in range(j + 1, min(m, j + mah1) + 1):
            v[i] -= a[i, j - i] * vj
        v[j] = a[j, 0] * vj
    for j in range(m - 1, 0, -1):
        vj = v[j]
        for i in range(max(0, j - mah1), j):
            v[i] -= a[j, i - j] * vj

    return a, v
