# 2024 NOAA/NCEP/EMC
#
# The original file, pspl.f90 was written by Jim Purser of NOAA/NCEP/EMC
# in May 2014.
# This python script was written by Nick Esposito of NOAA/NCEP/EMC
# in December 2023 - ??? 2024
# The original pspl.f90 file may be found here:
# https://github.com/NOAA-EMC/prepobs/blob/develop/sorc/
#           prepobs_prepacqc.fd/pspl.f90
# Some variables and parameters were taken from:
# https://github.com/NOAA-EMC/prepobs/blob/develop/sorc/
#           prepobs_prepacqc.fd/pietc.f90
# and
# https://github.com/NOAA-EMC/prepobs/blob/develop/sorc/
#           prepobs_prepacqc.fd/pmat2.f90
# in order to reduce the number of calls/references
#####################################################################
#
# The original code was run with print statements to determine
# which variables from the original pspl.f90 code were used commonly.
# Over a period of two days, all of the following functions and
# subroutines from the original code were used:
# coshm enbase_t expmm expm sinhm xcms best_tslalom best_uslalom
# convertd_back convertd count_gates count_routes eval_tsplined
# fit_gtspline fit_tspline int_tspline next_route set_posts
# slalom_tspline tbnewton
#
# The following functions and subroutines were not called during
# the specific period in which the code was tested:
# coshmm eval_itspline eval_iuspline eval_tsplineddd eval_tsplinedd
# eval_tspline eval_usplineddd eval_usplinedd eval_usplined
# eval_uspline fit_guspline fit_uspline int_uspline list_routes
# set_gates slalom_uspline ubnewton
#
# Regardless of whether or not they were used, it was decided to
# keep all of the functions and subroutines should they need to be
# called/used at a later time.
#
#####################################################################
#
import numpy as np

halfgate  =  np.float(30.0)
bigT  =  np.float(120.0)
heps  =  np.float(0.01)


def expm(x):
    # exp(x)-1 (approximately x for small x)
    #  =  I^(1)exp(x), where I^(p) is the integral iterated p times

    eps  =  np.finfo(float).eps
    if abs(x) > 0.5:
        e  =  np.exp(x) - 1.0
    else:
        p  =  np.float(x)
        e  =  np.float(p)
        for i in range(2, 20):
            p  =  (p * x) / i
            e + =  p
            if abs(p) < =  abs(e * eps):
                break

    return np.float(e)


def expmm(x):
    # exp(x)-1-x (approximately x^2/2 for small x)
    #  =  I^(2)exp(x), where I^(p) is the integral iterated p times

    # Define the machine epsilon for floating-point arithmetic
    eps  =  sys.float_info.epsilon
    if abs(x) > 0.5:
        # For larger values of x, use the direct calculation
        e  =  np.exp(x) - 1.0 - x
    else:
        p  =  np.float(x * x * 0.5)
        e  =  np.float(p)
        for i in range(3, 26):
            p  =  (p * x) / i
            e + =  p
            # If the addition of the new term does not change the result,
            # it means we've reached the precision limit
            if abs(p) < =  abs(e * eps):
                break

    return np.float(e)


def coshm(x):
    # Calculate a modified hyperbolic cosine value.
    # exp(x)-1-x (approximately x^2/2 for small x)
    #  =  I^(2)exp(x), where I^(p) is the integral iterated p times
    x  =  np.float(x)
    return 2 * np.sinh(x * 0.5) ** 2


def sinhm(x):
    # Calculate a modified hyperbolic sine of x.
    # sinh(x)-x (approximately x**3/6 for small x)
    #  =  I^(3)cosh(x), where I^(p) is the integral iterated p times
    # Input x and output s should be float
    eps  =  np.finfo(float).eps

    if abs(x) > 0.5:
        s  =  np.sinh(x) - x
    else:
        p  =  np.float(x) ** 3 / 6
        s  =  p
        xx  =  x * x
        for i in range(5, 20, 2):
            p  =  p * xx / (i * (i - 1.0))
            s + =  p
            if abs(p) < =  abs(s * eps):
                break

    return s


def coshmm(x):
    # cosh(x)-1-x^2/2  (approximately x**4/24 for small x)
    #  = I^(4)cosh(x), where I^(p) is the integral iterated p times
    xh  =  x * 0.5
    c  =  sinhm(xh) * (2 * np.sinh(xh) + x)
    return c


def xcms(x):
    # x*coshm(x)-sinhm(x) (approximately x**3/3 for small x)
    # NICKE : x might need to be double precison depending on if
    # it is a time variable and what time is (time since
    # or more recent where it shouldn't matter as much
    x  =  np.float(x)   #might not need this?
    eps  =  np.finfo(float).eps

    if abs(x) > 0.5:
        e  =  np.float(x) * coshm(x) - sinhm(x))
    else:
        p  =  np.float(x) ** 3 / 3
        e  =  p
        xx  =  x * x
        for i in range(2, 16):
            i2  =  i * 2
            p  =  p * xx / (i2 * (i2 + 1))
            e  =  e + i * p
            if abs(p) < =  abs(e * eps):
                break

    return e


def enbase_t(tspan, hspan):
    # For a nondimensional time span, tspan, but a dimensional height
    # span, hspan, return the baseline minimum possible tensioned spline
    # energy integrated over the central span plus the two wings.
    # If the hspan vanishes, return a nominal unit energy.
    # The energy is quadratic in hspan, which can therefore be of either sign,
    # but tspan must be strictly positive for a meaningful positive energy.

    if tspan < 0.0:
        raise ValueError("In enbase_t; tspan must be positive")

    if hspan == 0.0:
        return 1.0

    # Calculate
    r  =  hspan**2 / expmm(-tspan) * 0.5

    return r


def tbnewton(nh, m, hgts, hs, hgtp, p, q):
    # Perform a "bounded Newton" iteration to estimate the vertical velocity,
    # dh/dt, as the trajectory passes through the nh "gates", each at height
    # hs(i) and centered at time hgts(i)*halfgate with the halfwidth of the gate
    # equal to halfgate. The characteristic timescale of the fitted spline is bigT.
    # the time-nodes rescaled by this bigT are at the m points tp, and the
    # corresponding "p" and "q" coefficients of the tensioned spline are p and q
    # respectively.
    # The output is an array of n estimates, dh/dt, at each gate's hs. This
    # involves estimating the time t of passage through each gate, and is done
    # generically by Newton's method, except that the newton increments are
    # bounded to be within a range "gate" = 2*halfgate, so that we eliminate
    # wild excursions when dh/dt is actually very small (or vanishes). When such
    # an excursion is detected, the returned value of dh/dt is simply that
    # evaluated at ts(i), and no further attempt at Newton refinement is made
    # at this i. (The vertical motion in such cases is essentially negligible
    # in any case, and very likely is multivalued as the trajectory wavers about
    # this gate's value of hs(i).)
    halfgate = np.float(30.0)
    heps = np.float(0.01)
    bigT = np.float(120.0)
    nit = int(12)

    gate = 2 * halfgate / bigT
    tr = [x * halfgate / bigT for x in hgtp]
    dhdt = [0.0] * nh
    te = [0.0] * nh
    FF = False

    for i in range(nh):
        tee = hgts[i] * halfgate / bigT
        he = hs[i]
        #  Use Newton iterations to estimate the rescaled time, tee, at which the
        #  height is he
        it = 1
        while it < =  nit:
            hac, dhadt = eval_tsplined(m, tr, p, q, tee)
            if it == 1:
                dhdt[i] = dhadt / bigT
            if dhadt == 0:
                break
            dh = hac - he
            dt = -dh / dhadt
            if abs(dt) > gate:
                print("WARNING! In tbnewton; i,it,dt/gate  = ", i, it, dt / gate)
                break
            if abs(dh) < heps:
                dhdt[i] = dhadt / bigT
                break
            tee = tee + dt
            it = it + 1
        FF = it > nit
        if FF:
            print("In tbnewton; Newton iterations seem not to be converging \\
                   at i = ", i)
            print("tee,he,hac,heps,dhadt:", tee, he, hac, np.finfo(float).eps,
                   dhadt)
        te[i] = tee

    return te, dhdt, FF

def ubnewton(nh, m, hgts, hs, hgtp, p, q):
    # Like tbnewton, but for the case of untensioned (i.e., cubic) splines
    halfgate = np.float(30.0)
    nit = int(12)

    gate = 2 * halfgate
    # tr = hgtp * halfgate
    tr = [h * halfgate for h in hgtp]
    for i in range(nh):
        tee = hgts[i] * halfgate
        he = hs[i]
          # Use Newton iterations to estimate the rescaled time, tee, at which the
          # height is he
        it = 1
        while it < =  nit:
            hac, dhadt = eval_uspline(m, tr, p, q, tee) #, hac, dhadt)  eval_uspline does not return dhadt....
    # NickE gotta fiture this out
            if it == 1:
                dhdt[i] = dhadt
            if dhadt == 0:
                break
            dh = hac - he
            dt = -dh / dhadt
            if abs(dt) > gate:
                print("WARNING! In ubnewton; i,it,dt/gate  = ", i, it, dt / gate)
                break
            if abs(dh) < heps:
                dhdt[i] = dhadt
                break
            tee  =  tee + dt
            it = it + 1
        FF = it > nit
        if FF:
            print("In ubnewton; Newton iterations seem not to be converging \\
                  at i = ", i)
            print("tee,he,hac,heps,dhadt:", tee, he, hac, heps, dhadt)
        te[i] = tee

    return te, dhdt, FF

def fit_gtspline(n, xs, ys, on):
    # Fit the gappy tensioned spline, where only those nodes flagged "on"
    # are effective in the fitting procedure. Owing to the fact that, where
    # constraints are not "on" the spline will generally depart from ys, the
    # actual y (yac) is returned for all nodes, regardless of the partial
    # duplication with the given ys. In other respects, this is just
    # like fit_tspline.
    m = 0
    xa, ya, qa, ja = []
    for i in range(n):
        if on[i]:
            m = m + 1
            xa[m] = xs[i]
            ya[m] = ys[i]
    # NickE #####################
    qa, ja, en, FF = fit_tspline(m, xa[:m], ya[:m]) #, qa[:m], ja[:m], en, FF)
    if FF:
        print("In fit_gtspline; failure flag raised at call to fit_tspline")
        return q, j, yac, en, FF
    k = 0
    for i in range(n):
        if on[i]:
            k = k + 1
            q[i] = qa[k]
            j[i] = ja[k]
            yac[i] = ys[i]
        else:
    #NickE
            yac[i], q[i] = eval_tsplined(m, xa[:m], ya[:m], qa[:m], xs[i])
            j[i] = 0

    return q, j, yac, en, FF

def fit_tspline(n, xs, p):# , q, j, en, FF):
    # Solve for the coefficients, the 3rd-derivative jumps, and the energy,
    # of the standardized tensioned spline passing through the n nodes at (xs,p).
    #
    # The value and successive derivatives on the immediate positive side of
    # each node, xs(i), are to be found as p(i), q(i), r(i), s(i), with j(i)
    # being the discontinuity of 3rd-derivative s between the negative and positive
    # side of the node (value itself, and other derivatives, remaining continuous).
    # In addition, p(0), q(0), r(0) and s(0) are the value and derivatives on the
    # immediate negative side of xs(1). The spline solution minimizes elastic
    # and tensional energy, en, defined as the integral dx of half the sum of the
    # squared first and second derivatives over the whole line. Euler-Lagrange
    # implies the solution is expressible in each segment between or beyond nodes:
    #       y(x') = p + q*x' + r*coshm(x') + s*sinhm(x')
    # where x' = x-xs(i) is the local coordinate relative to the relevant node
    # (the node at the left of the segent except that, implicitly, we take
    # xs(0)== = xs(1), and the two functions, coshm and sinhm, are defined:
    # coshm(x) = cosh(x)-1
    # sinhm(x) = sinh(x)-x.
    # The solution in segment 0, i.e., x< xs(1), must exponentially decay towards
    # a constant as x--> -infinity, while that for segment n must likewise decay
    # as x--> +infinity, in order that energy remains finite. Thus, q(0) = r(0) = s(0)
    # and q(n) = -r(n) = s(n) always. Solutions in these infinite end segments are
    # therefore expressible in terms only of p(0),q(0) for segment 0 and in terms
    # only of p(n), q(n) for segment n and is linear in these coefficients.
    # Between consecutive nodes (segments 0<i<n) the solution y(x') is expressible
    # in terms only of p(i),q(i),p(i+1),q(i+1) and is linear in these coefficients.
    # Being a quadratic functional, the total energy is therefore expressible
    # in vector-matrix quadratic form:
    # En = (1/2)*p^T*PP*p + q^T*QP*p + (1/2)*q^T^QQ*q
    # where p and q are here taken as the column vectors of all their discrete
    # values, i = 0,..n, and PP, QP and QQ are certain tri-diagonal matrices.
    # The spline solution is found as the energy-minimizing solution to:
    # QP*p + QQ*q = 0
    # where the p are known (the y(i)) and q is the vector of unknowns. Having
    # solved for q, we can immediately deduce the r and s, and hence the jump, j.
    # Finally, we can also return the value of the energy as well.
    # The use of a tri-diagonal solver, though seemingly more complicated than
    # naive "shooting" alternatives, is very much better conditioned numerically,
    # and will succeed in very long data series where the naive methods invariably
    # fail.
    # In practice, owing to the formal symmetries of the energy in each interval,
    # we need only consider the change, p(i+1)-p(i), in each interval, and
    # this "odd-symmetry" part of vector, p, only couples with the corresponding
    # symmetry in the q (which is the part, (q(i)+q(i+1))), so two of the
    # tridiagonals actually reduce to diagonals, simplifying the algebra.
    FF = False
    if n < 1:
        raise ValueError("In fit_tspline; size of data array must be positive")
    if n == 1:
        q[:] = 0
        j[:] = 0
        en = 0
        return q, j, en, FF
    # apply a strict monotonicity check on the xs
    for i in range(1, n):
        if xs[i-1] > =  xs[i]:
            FF = True
            print("In fit_tspline; xs data must increase strictly monotonically")
    # NickE what I return??????
            return None, None, None, FF
    # Initialize tri-diagonal kernels for the energy definition:
    # qq = np.zeroes((n,2)) initialize symmetric tridiagonal, kernel for q^T*QQ*q
    #      where "q" are the dp/dx at each node.
    # The coefficients in the quadratic form defining the spline energy also
    # include terms involving factors (p(ip)-p(i))*(q(i)+q(ip)) and
    # (p(ip)-p(i))*(p(ip)-p(i)), but these can be dealt with using, respectively,
    # the  matrices cqp and cpp which are simply diagonal. It is the symmetries
    # in the defiition of energy that allow this simplification.
    qq = np.zeros((n, 2))
    difp = np.zeros(n-1)
    cpp = np.zeros(n-1)
    cqp = np.zeros(n-1)
    sumq = np.zeros(n-1)
    q = np.zeros(n)
    j = np.zeros(n)
    # Loop over the intervals bounded by consecutive nodes:
    for i in range(n-1):
        ip = i + 1
        difp[i] = p[ip] - p[i]
        x = (xs[ip] - xs[i]) * 0.5
        ch = np.cosh(x)
        sh = np.sinh(x)
        xcmsx2 = xcms(x) * 2
    # egg relates to the odd-g-basis function's energy integral coefficient
    # ehh relates to the even-g-basis function's energy integral coefficient
        egg = x * sh / xcmsx2
        ehh = ch / (2 * sh)
    # ccc is the coefficient of energy integral coupling g(i)*g(i) and g(ip)*g(ip)
        ccc = egg + ehh
    #ccp[i] is  Energy coefficient for difp(i)*difp(i)...
        cpp[i] = ch / xcmsx2
    # cqp[i] is for difp(i)*sumq(i)
        cqp[i] = -difp[i] * sh / xcmsx2
        qq[i, 0] = qq[i, 0] + ccc
        qq[ip, -1] = qq[ip, -1] + egg - ehh
        qq[ip, 0] = qq[ip, 0] + ccc
    # Add the exterior energy contributions to qq at both ends:
    qq[0, 0] = qq[0, 0] + 1
    qq[n-1, 0] = qq[n-1, 0] + 1
    # Temporarily, q is made the vector of forcings in the tridiagonal linear
    # system from which the final spline coefficients, q, are solved in place.
    q[:n-1] = -cqp
    q[n-1] = 0
    q[1:n] = q[1:n] - cqp
    # The following 2 lines solve the tridiagonal system for q:
    #NickE these are called by pmat2. figure out the outputs.
    qq = ldltb(n, 1, qq)
    qq, q = ltdlbv(n, 1, qq, q)

    sumq[:] = q[:n-1] + q[1:n]

    # The minimizing energy can now be evaluated as a sum of only 2 terms:
    en = 0.5 * (np.dot(difp**2, cpp) + np.dot(sumq, cqp))
    # Finally, evaluate the 3rd-derivative "jumps", j, at each node:
    # Here, sb is the 3rd-derivative at the right end, sa that at the left end,
    # of whichever interval is under consideration, but for interior intervals,
    # sa = sap+q(i) and sb = sap+q(i+1).
    sb = q[0]
    for i in range(n-1):
        ip = i + 1
        x = (xs[ip] - xs[i]) * 0.5
        xcmsx2 = xcms(x) * 2
        ch = np.cosh(x)
        sh = np.sinh(x)
        sap = (sh * sumq[i] - ch * difp[i]) / xcmsx2
        sa = sap + q[i]
        j[i] = sa - sb
        sb = sap + q[ip]

    # Final "sa" is just q(n) for the right exterior
    j[n-1] = q[n-1] - sb

    #NickE do I return something??
    return q, j, en, False


def int_tspline(n, xs, p, q):# , m):
    # Take the sets of n parameters p and q of the tensioned spline
    # and return the values of its integral at the n-1 interval midpoints, and
    # the value at the last node, assuming that the integral at the first node
    # is set to zero.
    m = np.zeros(n)
    # e is the running integral as we loop over successive nodes, so it starts
    # out zero at the first node:
    e = 0
    # loop over intervals
    for i in range(n-1):
        ip = i + 1
        x = (xs[ip] - xs[i]) * 0.5 # interval half-width
        t2 = x * x * 0.5
        shx = np.sinh(x)
        chmx = coshm(x)
        shmx = sinhm(x)
        chmmx = coshmm(x)
        xcmsx = xcms(x)
        pa = (p[ip] + p[i]) * 0.5
        pd = (p[ip] - p[i]) * 0.5 / x
        qa = (q[ip] + q[i]) * 0.5
        qd = (q[ip] - q[i]) * 0.5 / shx
    # a,b,c,d are analogous to the Taylor coefficients of a cubic about the
    # interval midpoint, but more precisely, c and d relate to basis functions
    # coshm and sinhm (instead of x**2/2 and x**3/6 for the perfect cubic).
        c = qd
        a = pa - c * chmx
        d = (qa - pd) * x / xcmsx
        b = qa - d * chmx
        m[i] = e + a * x - b * t2 + c * shmx - d * chmmx
        e = e + 2 * (a * x + c * shmx)
    m[n-1] = e

    return m

def fit_guspline(n, xs, ys, on): #, q, j, yac, en, FF):
    # Fit the gappy untensioned spline, where only those nodes flagged "on"
    # are effective in the fitting procedure. Owing to the fact that, where
    # constraints are not "on" the spline will generally depart from ys, the
    # actual y (yac) is returned for all nodes, regardless of the partial
    # duplication with the given ys. In other respects, this is just
    # like fit_tspline.
    m = 0
    xa = np.zeros(n)
    ya = np.zeros(n)
    qa = np.zeros(n)
    ja = np.zeros(n)
    for i in range(n):
        if on[i]:
            xa[m] = xs[i]
            ya[m] = ys[i]
            m + =  1
    qa, ja, en, FF = fit_uspline(m, xa[:m], ya[:m]) #, qa[:m], ja[:m], en, FF)
    if FF:
        print("In fit_guspline; failure flag raised at call to fit_uspline")
        return
    k = 0
    for i in range(n):
        if on[i]:
            q[i] = qa[k]
            j[i] = ja[k]
            yac[i] = ys[i]
            k + =  1
        else:
            yac[i], q[i] = eval_usplined(m, xa[:m], ya[:m], qa[:m], xs[i]) #, yac[i], q[i])
            j[i] = 0

    return q, j, yac, en, FF


def fit_uspline(n, xs, p):
    # Solve for the coefficients, the 3rd-derivative jumps, and the energy,
    # of the untensioned (cubic) spline passing through the n nodes at (xs,p).
    #
    # The algorithm follows the pattern given in fit_tspline, except that the
    # hyperbolic functions are all replaced by their asymptotic (x--> 0) limiting
    # forms. These limiting forms are as follows:
    # cosh(x) --> 1
    # sinh(x) --> x
    # coshm(x) --> x**2/2
    # sinhm(x) --> x**3/6
    # xcms(x)  --> x**3/3
    FF = False
    if n < 1:
        raise ValueError("In fit_uspline; size of data array must be positive")
    if n == 1:
        q[:] = 0
        j[:] = 0
        en = 0
        return q, j, en, FF
    # apply a strict monotonicity check on the xs:
    for i in range(1, n):
        if xs[i-1] > =  xs[i]:
            FF = True
            print("In fit_uspline; xs data must increase strictly monotonically")
            return None, None, None, FF
    # Initialize qq = np.zeros((n, 2)) b/c symmetric tridiagonal, kernel for
    #    q^T*QQ*q where "q" are the dp/dx at each node.
    # The coefficients in the quadratic form defining the spline energy also
    # include terms involving factors (p(ip)-p(i))*(q(i)+q(ip)) and
    # (p(ip)-p(i))*(p(ip)-p(i)), but these can be dealt with using, respectively,
    # the  matrices cqp and cpp which are simply diagonal. It is the symmetries
    # in the defiition of energy that allow this simplification.

    q = np.zeros(n)
    j = np.zeros(n)
    qq = np.zeros((n, 2))
    difp = np.zeros(n-1)
    cpp = np.zeros(n-1)
    cqp = np.zeros(n-1)
    sumq = np.zeros(n-1)

    # Loop over the intervals bounded by consecutive nodes:
    for i in range(n-1):
        ip = i + 1
        difp[i] = p[ip] - p[i]
        x2 = xs[ip] - xs[i]
        x = 0.5 * x2
        xcmsx2 = (1 / 3) * x**3 * 2
        ccc = 2 / x
        cpp[i] = 1 / xcmsx2
        cqp[i] = -difp[i] * x / xcmsx2
        qq[i, 0] + =  ccc   #NickE not sure about this
        if ip < n-1:       # NickE not sure about this
            qq[ip, 0] + =  1 / x  #NickE not sure about this
        qq[ip, 0] + =  ccc   #NickE not sure about this

    # Solve the tridiagonal system for q
    q[:-1] = -cqp
    q[1:] - =  cqp
    qq = ldltb(n, 1, qq) #NickE this should be good
    q = ltdlbv(n, 1, qq, q)  #NickE this should be good
    #    q = solve_tridiagonal(qq, q)
    sumq = q[:-1] + q[1:]

    # Calculate minimizing energy
    en = 0.5 * (np.dot(difp**2, cpp) + np.dot(sumq, cqp))

    # Calculate the 3rd-derivative "jumps"
    sb = 0
    for i in range(n-1):
        ip = i + 1
        x = 0.5 * (xs[ip] - xs[i])
        xcmsx2 = (1 / 3) * x**3 * 2
        sa = (x * sumq[i] - difp[i]) / xcmsx2
        j[i] = sa - sb
        sb = sa
    j[-1] = -sb

    return q, j, en, FF


def int_uspline(n, xs, p, q): # m
    # Take the sets of n parameters p and q of the untensioned cubic spline
    # and return the values of its integral at the n-1 interval midpoints, and
    # the value at the last node, assuming that the integral at the first node
    # is set to zero.
    m = np.zeros(n)
    e = 0.0
    for i in range(n-1):
        ip = i + 1
        # Calculate half-width of the interval
        x = (xs[ip] - xs[i]) * 0.5
        t2 = x ** 2 * 0.5
        t3 = t2 * x / 3
        t4 = t3 * x / 4
        pa = (p[ip] + p[i]) * 0.5
        pd = (p[ip] - p[i]) / (2 * x)
        qa = (q[ip] + q[i]) * 0.5
        qd = (q[ip] - q[i]) / (2 * x)
        # a,b,c,d are the Taylor coefficients of the cubic about the
        # interval midpoint
        c = qd
        a = pa - c * t2
        d = (qa - pd) * (3/2) / t2
        b = qa - d * t2
        # Calculate the integral over the interval
        m[i] = e + a * x - b * t2 + c * t3 - d * t4
        # Update the running integral
        e + =   2 * (a * x + c * t3)

    # Set the last element to the total integral
    m[n-1] = e
    return m

def eval_tspline(n, xs, p, q, x): # y
    # Assuming the 1st derivatives, q, are correctly given at the n nodes, xs,
    # of the standardized tensioned spline, where p are the nodal values,
    # evaluate the spline function y at the location x.
    # First find the nonvanishing interval in which x resides, then expand
    # y using basis functions implied by the interval-end values of p and q
    # using the interval midpoint as local origin when x is interior, or the
    # single interval endpoint when it is exterior.
    y = 0.0

    if x < =  xs[0]:
        xr = x - xs[0]
        y = p[0] + q[0] * expm(xr)
        return y
    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        y = p[n-1] - q[n-1] * expm(-xr)
        return y
    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            # only consider intervals of positive width
            continue
        if xs[ib] > =  x:
            # exit once finite interval straddling x is found
            break
    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5  # halfwidth of interval
    xr = x - xs[ia] - xh  # x relative to interval midpoint
    pm = (p[ib] + p[ia]) * 0.5  # average of end values
    qm = (p[ib] - p[ia]) / (2 * xh)  # average gradient
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm  # Half the total excess q at interval ends
    qdh = qbh - qah  # Half the difference of q at interval ends
    shh = np.sinh(xh)
    chh = np.cosh(xh)
    sh = np.sinh(xr)
    ch = np.cosh(xr)
    shm = sinhm(xr)
    chm = coshm(xr)
    shhm = sinhm(xh)
    chhm = coshm(xh)
    xcmsh = xcms(xh)
    qdh = qdh / shh  # rescale qdh, qxh
    qxh = qxh / xcmsh  # rescale qdh, qxh
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)
    return y

def eval_tsplined(n, xs, p, q, x):
    # Like eval_tspline, but also return the derivative dy/dx
    y = 0.0
    dydx = 0.0
    if x < =  xs[0]:
        xr = x - xs[0]
        qemxr = q[0] * expm(xr)
        y = p[0] + qemxr
        dydx = qemxr + q[0]
        return y, dydx
    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        qemxr = q[n-1] * expm(-xr)
        y = p[n-1] - qemxr
        dydx = qemxr + q[n-1]
        return y, dydx
    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            # Skip intervals of non-positive width
            continue
        if xs[ib] > =  x:
            # exit once finite interval straddling x is found
            break
    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5  # halfwidth of interval
    xr = x - xs[ia] - xh  # x relative to interval midpoint
    pm = (p[ib] + p[ia]) * 0.5
    qm = (p[ib] - p[ia]) / (2 * xh)
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm  # Half the total excess q at interval ends
    qdh = qbh - qah  # Half the difference of q at interval ends
    shh = np.sinh(xh)
    chh = np.cosh(xh)
    sh = np.sinh(xr)
    ch = np.cosh(xr)
    shm = sinhm(xr)
    chm = coshm(xr)
    shhm = sinhm(xh)
    chhm = coshm(xh)
    xcmsh = xcms(xh)
    qdh = qdh / shh
    qxh = qxh / xcmsh
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)
    dydx = qm + qdh * sh + qxh * (xh * chm - shhm)
    return y, dydx

def eval_tsplinedd(n, xs, p, q, x):
    # Like eval_tspline, but also return the derivative dy/dx
    y = 0.0
    dydx = 0.0
    ddyddx = 0.0

    if x < =  xs[0]:
        xr = x - xs[0]
        qemxr = q[0] * expm(xr)
        y = p[0] + qemxr
        dydx = qemxr + q[0]
        ddydxx = dydx
        return y, dydx, ddydxx
    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        qemxr = q[n-1] * expm(-xr)
        y = p[n-1] - qemxr
        dydx = qemxr + q[n-1]
        ddydxx = -dydx
        return y, dydx, ddydxx
    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            continue
        if xs[ib] > =  x:
            break
    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5
    xr = x - xs[ia] - xh
    pm = (p[ib] + p[ia]) * 0.5
    qm = (p[ib] - p[ia]) / (2 * xh)
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm
    qdh = qbh - qah
    shh = np.sinh(xh)
    chh = np.cosh(xh)
    sh = np.sinh(xr)
    ch = np.cosh(xr)
    shm = sinhm(xr)
    chm = coshm(xr)
    shhm = sinhm(xh)
    chhm = coshm(xh)
    xcmsh = xcms(xh)
    qdh = qdh / shh
    qxh = qxh / xcmsh
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)
    dydx = qm + qdh * sh + qxh * (xh * chm - shhm)
    ddydxx = qdh * ch + qxh * xh * sh
    return y, dydx, ddydxx

def eval_tsplineddd(n, xs, p, q, x):
    # Like eval_tspline, but also return the derivative dy/dx
    if x < =  xs[0]:
        xr = x - xs[0]
        qemxr = q[0] * expm(xr)
        y = p[0] + qemxr
        dydx = qemxr + q[0]
        ddydxx = dydx
        dddydxxx = dydx
        return y, dydx, ddydxx, dddydxxx
    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        qemxr = q[n-1] * expm(-xr)
        y = p[n-1] - qemxr
        dydx = qemxr + q[n-1]
        ddydxx = -dydx
        dddydxxx = dydx
        return y, dydx, ddydxx, dddydxxx
    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            continue
        if xs[ib] > =  x:
            break
    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5
    xr = x - xs[ia] - xh
    pm = (p[ib] + p[ia]) * 0.5
    qm = (p[ib] - p[ia]) / (2 * xh)
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm
    qdh = qbh - qah
    shh = np.sinh(xh)
    chh = np.cosh(xh)
    sh = np.sinh(xr)
    ch = np.cosh(xr)
    shm = sinhm(xr)
    chm = coshm(xr)
    shhm = sinhm(xh)
    chhm = coshm(xh)
    xcmsh = xcms(xh)
    qdh = qdh / shh
    qxh = qxh / xcmsh
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)
    dydx = qm + qdh * sh + qxh * (xh * chm - shhm)
    ddydxx = qdh * ch + qxh * xh * sh
    dddydxxx = qdh * sh + qxh * xh * ch
    return y, dydx, ddydxx, dddydxxx

def eval_itspline(n, xs, p, q, m, x):
    # Evaluate the integrated tension spline at x, returning the value, y.
    if x < =  xs[0]:
        xr = x - xs[0]
        y = p[0] * xr + q[0] * expmm(xr)
        return y
    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        y = m[n-1] + p[n-1] * xr + q[n-1] * expmm(-xr)
        return y
    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            # only consider intervals of positive width
            continue
        if xs[ib] > =  x:
            # exit once finite interval straddling x is found
            break
    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5
    shx = np.sinh(xh)
    chmx = coshm(xh)
    xcmsx = xcms(xh)
    xr = x - xs[ia] - xh
    pa = (p[ib] + p[ia]) * 0.5
    pd = (p[ib] - p[ia]) * 0.5 / xh
    qa = (q[ib] + q[ia]) * 0.5
    qd = (q[ib] - q[ia]) * 0.5 / shx
    c = qd
    a = pa - c * chmx
    d = (qa - pd) * xh / xcmsx
    b = qa - d * chmx
    t2 = xr**2 / 2
    shmx = sinhm(xr)
    chmmx = coshmm(xr)
    y = m[ia] + a * xr + b * t2 + c * shmx + d * chmmx
    return y


def eval_uspline(n, xs, p, q, x):
    # Assuming the 1st derivatives, q, are correctly given at the n nodes, xs,
    # of the standardized untensioned spline, where p are the nodal values,
    # evaluate the (UNtensioned) spline function y at the location x.
    # First find the nonvanishing interval in which x resides, then expand
    # y using basis functions implied by the interval-end values of p and q
    # using the interval midpoint as local origin when x is interior, or the
    # single interval endpoint when it is exterior.

    if x < =  xs[0]:
        xr = x - xs[0]
        y = p[0] + q[0] * xr
        return y

    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        y = p[n-1] + q[n-1] * xr
        return y

    # Find the interval containing x
    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            continue
        if xs[ib] > =  x:
            break

    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5 # halfwidth of interval
    xr = x - xs[ia] - xh # x relative to interval midpoint
    pm = (p[ib] + p[ia]) * 0.5 # average of end values
    qm = (p[ib] - p[ia]) / (2 * xh) # average gradient
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm # Half the total excess q at interval ends
    qdh = qbh - qah # Half the difference of q at interval ends
    shh = xh
    chh = 1
    sh = xr
    ch = 1
    xcmsh = xh ** 3 / 3
    shm = xr ** 3 / 6
    chm = xr ** 2 * 0.5
    shhm = xh ** 3 / 6
    chhm = xh ** 2 * 0.5
    qdh = qdh / shh # rescale
    qxh = qxh / xcmsh # rescale
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)

    return y


def eval_usplined(n, xs, p, q, x):
    # Like eval_uspline, but also return the derivative dy/dx

    if x < =  xs[0]:
        xr = x - xs[0]
        y = p[0] + q[0] * xr
        dydx = q[0]
        return y, dydx

    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        y = p[n-1] + q[n-1] * xr
        dydx = q[n-1]
        return y, dydx

    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            continue
        if xs[ib] > =  x:
            break

    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5
    xr = x - xs[ia] - xh
    pm = (p[ia] + p[ib]) * 0.5
    qm = (p[ib] - p[ia]) / (xh * 2)
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm
    qdh = qbh - qah
    shh = xh
    chh = 1
    sh = xr
    ch = 1
    shm = xr**3 / 6
    chm = xr**2 * 0.5
    shhm = xh**3 / 6
    chhm = xh**2 * 0.5
    xcmsh = xh**3 / 3
    qdh = qdh / shh
    qxh = qxh / xcmsh
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)
    dydx = qm + qdh * sh + qxh * (xh * chm - shhm)

    return y, dydx


def eval_usplinedd(n, xs, p, q, x):
    # Like eval_uspline, but also return the derivative dy/dx

    if x < =  xs[0]:
        xr = x - xs[0]
        y = p[0] + q[0] * xr
        dydx = q[0]
        ddydxx = 0
        return y, dydx, ddydxx

    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        y = p[n-1] + q[n-1] * xr
        dydx = q[n-1]
        ddydxx = 0
        return y, dydx, ddydxx

    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            continue
        if xs[ib] > =  x:
            break

    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5
    xr = x - xs[ia] - xh
    pm = (p[ia] + p[ib]) * 0.5
    qm = (p[ib] - p[ia]) / (xh * 2)
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm
    qdh = qbh - qah
    shh = xh
    chh = 1
    sh = xr
    ch = 1
    shm = xr**3 / 6
    chm = xr**2 * 0.5
    shhm = xh**3 / 6
    chhm = xh**2 * 0.5
    xcmsh = xh**3 / 3
    qdh = qdh / shh
    qxh = qxh / xcmsh
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)
    dydx = qm + qdh * sh + qxh * (xh * chm - shhm)
    ddydxx = qdh + qxh * xh * sh

    return y, dydx, ddydxx


def eval_usplineddd(n, xs, p, q, x):
    # Like eval_uspline, but also return the derivative dy/dx

    if x < =  xs[0]:
        xr = x - xs[0]
        y = p[0] + q[0] * xr
        dydx = q[0]
        ddydxx = 0
        dddydxxx = 0
        return y, dydx, ddydxx, dddydxxx

    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        y = p[n-1] + q[n-1] * xr
        dydx = q[n-1]
        ddydxx = 0
        dddydxxx = 0
        return y, dydx, ddydxx, dddydxxx

    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            continue
        if xs[ib] > =  x:
            break

    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5
    xr = x - xs[ia] - xh
    pm = (p[ia] + p[ib]) * 0.5
    qm = (p[ib] - p[ia]) / (xh * 2)
    qah = q[ia] * 0.5
    qbh = q[ib] * 0.5
    qxh = qah + qbh - qm
    qdh = qbh - qah
    shh = xh
    chh = 1
    sh = xr
    ch = 1
    # NickE I think also issues here
    shm = xr**3 / 6
    chm = xr**2 * 0.5
    shhm = xh**3 / 6
    chhm = xh**2 * 0.5
    xcmsh = xh**3 / 3
    qdh = qdh / shh
    qxh = qxh / xcmsh
    y = pm + xr * qm + qdh * (chm - chhm) + qxh * (xh * shm - xr * shhm)
    dydx = qm + qdh * sh + qxh * (xh * chm - shhm)
    ddydxx = qdh + qxh * xh * sh
    dddydxxx = qxh * xh

    return y, dydx, ddydxx, dddydxxx


def eval_iuspline(n, xs, p, q, m, x):
    # valuate the integrated untensioned spline at x, returning the value, y.
    if x < =  xs[0]:
        xr = x - xs[0]
        y = p[0] * xr + q[0] * xr**2 * 0.5
        return y
    if x > =  xs[n-1]:
        xr = x - xs[n-1]
        y = m[n-1] + p[n-1] * xr + q[n-1] * xr**2 * 0.5
        return y

    # Find the interval that contains x
    for ib in range(1, n):
        if xs[ib] < =  xs[ib-1]:
            continue
        if xs[ib] > =  x:
            break
    ia = ib - 1
    xh = (xs[ib] - xs[ia]) * 0.5
    xr = x - xs[ia] - xh
    t2 = xh**2 * 0.5
    t3 = t2 * xh / 3
    pa = (p[ib] + p[ia]) * 0.5
    pd = (p[ib] - p[ia]) * 0.5 / xh
    qa = (q[ib] + q[ia]) * 0.5
    qd = (q[ib] - q[ia]) * 0.5 / xh
    # a,b,c,d are the Taylor coefficients of the cubic about the interval midpoint
    c = qd
    a = pa - c * t2
    d = (qa - pd) * 1.5 / t2
    b = qa - d * t2
    t2 = xr**2 * 0.5
    t3 = t2 * xr / 3
    t4 = t3 * xr / 4
    y = m[ia] + a * xr + b * t2 + c * t3 + d * t4
    return y


def best_tslalom(nh, mh, doru, hgts, hs):
    # Run through the different allowed routes between the slalom gates and
    # select as the final solution the one whose spline has the smallest "energy".

    # Initialize output variables
    halfgate = np.float(30)
    bigT = np.float(120.0)

    hgtp = np.zeros(mh*2, dtype = int)
    hp = np.zeros(mh*2)
    qbest = np.zeros(mh*2)
    yabest = np.zeros(mh*2)
    enbest = None
    modebest = np.zeros(mh, dtype = int)
    maxita = maxitb = maxit = maxrts = 0
    FF = False

    # Internal variables
    m = mh*2

    # Examine gate posts of first and last slalom gate to determine whether
    # profile is predominantly descending or ascending:
    hgtn, hn, code, FF = set_gates(nh, mh, doru, hgts, hs)
    descending = False
    if hn[0][1][0] > hn[0][0][mh-1]:
        descending = True
    elif hn[1][1][0] < hn[1][0][mh-1]:
        descending = False
    else:
        descending = (doru == 1)

    hgbigT = bigT / halfgate
    tspan = (hgtn[1][mh-1] - hgtn[0][0]) / hgbigT
    if descending:
        hspan = (hn[0][0][0] - hn[0][1][mh-1])
    else:
        hspan = (hn[1][1][mh-1] - hn[1][0][0])

    enbase = enbase_t(tspan, hspan)

    if FF:
        print('In best_tslalom; failure flag was raised in call to set_gates')
        return  # NickE return
    route_count, FF = count_routes(mh, code) #, route_count, FF)
    maxrts = max(maxrts, route_count)

    if FF:
        print('In best_tslalom; failure flag raised in call to count_routes')
        return hgtp, hp, qbest, yabest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF

    if route_count > 4:
        list_routes(mh, code)
    enbest = float('inf') ### NickE change to float_max * 0.5 i think
    flag = True

    for k in range(1, 1026): # 1026 is from ihu ( = 1025) + 1
        mode, flag = next_route(mh, code, mode, flag)
        if flag:
            flag = False
            break
        bend, hgtp, hp, off = set_posts(mh, mode, hgtn, hn)
        q, ya, en, ita, ittot, maxitb, FF = slalom_tspline(m, bend, hgtp, hp, off)
        en = en / enbase_t(tspan, hspan)
        maxita = max(maxita, ita)
        maxit = max(maxit, ittot)

        if FF:
            print('In best_tslalom; failure flag in call to slalom_tspline')
            return hgtp, hp, qbest, yabest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF

        if en < enbest:
            modebest = mode
            enbest = en
            qbest = q
            yabest = ya

    return hgtp, hp, qbest, yabest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF

def best_uslalom(nh, mh, doru, hgts, hs):
    # Like best_tslalom, except this treats the special limiting case where the
    # spline tension vanishes
    hgtp = np.zeros(mh*2, dtype = int)
    hp = np.zeros(mh*2)
    qbest = np.zeros(mh*2)
    yabest = np.zeros(mh*2)
    enbest = float('inf')  # Initialize to infinity for comparison
    modebest = np.zeros(mh, dtype = int)
    maxita = maxitb = maxit = maxrts = 0
    FF = False

    # Additional variables used within the subroutine
    halfgate = np.float(30.0)
    m = mh*2
    q = np.zeros(mh*2)
    ya = np.zeros(mh*2)
    flag = True

    hgtn, hn, code, FF = set_gates(nh, mh, doru, hgts, hs) #, hgtn, hn, code, FF)
    if FF:
        print('In best_uslalom; failure flag was raised in call to set_gates')
        return hgtp, hp, qbest, yabest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF

    route_count, FF = count_routes(mh, code) #, route_count, FF)
    maxrts = max(maxrts, route_count)
    if FF:
        print('In best_uslalom; failure flag raised in call to count_routes')
        return hgtp, hp, qbest, yabest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF

    if route_count > 4:
        list_routes(mh, code)
    enbest = float('inf') #NickE max_float * 0.5again
    flag = True

    for k in range(1, 1026): # ihu = 1025 + 1 = 1026
        mode, flag = next_route(mh, code)
        if flag:
            flag = False
            break

        bend, hgtp, hp, off = set_posts(mh, mode, hgtn, hn)
        q, ya, en, ita, ittot, maxitb, FF = slalom_uspline(m, bend, hgtp, hp, off)

        maxita = max(maxita, ita)
        maxit = max(maxit, ittot)
        if FF:
            print('best_uslalom; failure flag raised in call to slalom_uspline')
            return hgtp, hp, qbest, yabest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF
        if en < enbest:
            modebest = mode
            enbest = en
            qbest = q
            yabest = ya

    return hgtp, hp, qbest, yabest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF

def count_gates(nh, hgts):
    # Count the number of distinct "time gates" that can accommodate all the data
    # from the given profile. This gate count is mh.

    hgtp = hgts[0] - 1
    mh = 0

    for i in range(nh):
        if hgts[i] < =  hgtp:
            continue

        # A new nominal time of observation aka increment the count of gates
        mh + =  1
        # Update the previous height to the current height
        hgtp = hgts[i]
    return mh

def set_gates(nh, mh, doru, hgts, hs): #, hgtn, hn, code, FF):
    # Be sure to precede this routine by a call to "count_gates" to get a
    # consistent tally of the number of time gates, mh.
    # Set the locations of the "gateposts" and the routing codes of allowed
    # trajectories that thread through them.
    # Halfgate is half the (temporal) gate width (in seconds)
    # The "inferior" gatepost is at hgts - 1, the "superior" at hgts + 1.
    # The aggregated data lead to a tally of gates not exceeding the tally of obs.
    # the gatepost times of the aggregated data are put into array hgtn(:,:) where
    # hgtn(1,:) hold the inferior, and hgtn(2,:) the superior gatepost times, in
    # units of halfgate.
    # In general, it is not known a priori whether the trajectory will end up
    # ascending or descending though a given gate, so both alternatives are
    # accounted for, with hn(:,1,:) holding the height corresponding to tn(:,:)
    # assuming descending passage; hn(:,2:) likewise assuming ascending passage.
    # A running "attitude code" is maintained, atti between gates i-1 and i, and
    # the previous attitude code, attim between gates i-2 and i-1, where applicable.
    # This code is  = 2 when the later gate is wholly above the earlier,  = 1, when
    # later is wholly below the earlier, and remains 0 when altitudes of
    # the consecutive gates overlap. When the consecutive attitude codes are
    # both  = 2, we force the mode of passage through gate i-1 to be ascending (route
    # code = 8) if its route code has not already been determined by one of the
    # overriding contact conditions imposed by temporal contact between gate i-1
    # and its predecessor. Likewise, if consecutive attitude codes are both  = 1,
    # we force the mode of passage through gate i-1 to be descending (route code
    # 4) unless overridden by a previous temporal contact condition.
    # Temporal contact conditions between gates i-1 and i force one of three
    # route codes at gate i:  = 2 when gate i is wholly above gate i-1;  = 3 when
    # gate i is wholly below;  = 5 when the gate height ranges overlap.
    #
    # The purpose of the route code is to specify the possible modes of passage
    # (descending, ascending, or either of these alternatives) through gate i
    # when the actual mode of passage through the preceeding gate is known. It is
    # based on a 2-digit trinary code. The possible modes of passage through
    # gate i are enumerated by the "option code" whose values are:
    # 0 when passage may be either descending or ascending (indeterminate);
    # 1 when passage is definitely descending;
    # 2 when passage is definitely ascending.
    # The "units" digit of the trinary expansion of the route code gives the
    # option code for gate i when passage through gate i-1 is prescribed to be
    # DESCENDING; the "threes" digit of the trinary expansion of the route code
    # gives the option code for gate i when passage through gate i-1 is
    # prescribed to be ASCENDING. These possibilities for the option code for
    # gate i are summarized in the table below.
    #
    #    Route        ;   DESCENDING at (i-1)   ;   ASCENDING at (i-1)
    #   Code(i)       ;   ==> Option code(i)    ;    == > Option Code(i)
    #............................................................................
    #      0                     0                        0
    #      2                     2                        0
    #      3                     0                        1
    #      4                     1                        1
    #      5                     2                        1
    #      8                     2                        2
    #.............................................................................
    #
    # The first route code in a chain of gates, ie., code(1), is alway set
    # to 0, so at the very least, two combinations of routes are always coded
    # according as whether we choose to initialize the spline solution with
    # descent through gate 1 or an ascent. If all the gates are temporally
    # separated, then then final gate's route_code also has this 0 value
    # signifying an indeterminate mode of passage.
    #
    # In the special case where mh = 1 and the given hs data are not enough to
    # decide whether this trajectory is descending or ascending, the tie-breaker
    # code, doru ("down or up") forces the sense of the trajectory as follows:
    # doru = 1 ==> descending
    # doru = 2 ==> ascending

    #NickE this missed a lot. smh fml
    hgtn = np.zeros((2, mh), dtype = int)
    hn = np.zeros((2,2,mh))
    code = np.zeros(np, dtype = int)
    FF = False
    n = nh * 2

    hgtp = hgts[0] - 1
    imh = 0

    for i in range(nh):
        i2 = i * 2
        i2m = i2 - 1
        hp = hs[i]
        if hgts[i] > hgtp:
            imh + =  1
            hgtp = hgts[i]
            hgtn[0][imh-1] = hgtp - 1
            hgtn[1][imh-1] = hgtp + 1
            hn[:,:,imh-1] = hp
        elif hgts[i] < hgtp:
            FF = True
            print('In set_gates; data are not temporally monotonic')
            return hgtn, hn, code, FF
        else:
            hn[0][0][imh-1] = max(hn[0][0][imh-1], hp)
            hn[0][1][imh-1] = min(hn[0][1][imh-1], hp)
            hn[1][1][imh-1] = max(hn[1][1][imh-1], hp)
            hn[1][0][imh-1] = min(hn[1][0][imh-1], hp)
    if imh ! =  mh:
    # When consecutive gates' post times overlap, adjust their hn if the height
    # ranges also overlap:
        raise ValueError('In set_gates; inconsistent gate tallies, imh and mh')
    if mh == 1:
        code[0] = 4 * doru
        return hgtn, hn, code, FF

    attim = 0
    codeim = 9  # arbitrary nonzero number

    for i in range(1, mh):
        atti = 0  # default until more definite information is available
        im = i - 1
        if hgtn[0, i] < =  hgtn[1, im]:
            if hn[1, 1, im] < =  hn[0, 1, i]:
                atti = 2  # ascending attitude at common time
                code[i] = 2
                if attim == 2 and (codeim  ==  0 or codeim  ==  2):
                    code[im] = 8
            elif hn[1, 0, im] > =  hn[0, 0, i]:
                atti = 1  # descending attitude at common time
                code[i] = 3
                if attim == 1 and (codeim  ==  0 or codeim  ==  3):
                    code[im] = 4
            else:
                code[i] = 5
                if hn[1, 0, im] < =  hn[0, 1, i]:
                    hn[0, 1, i] = hn[1, 0, im]
                else:
                    hn[1, 0, im] = hn[0, 1, i]
                if hn[1, 1, im] < =  hn[0, 0, i]:
                    hn[1, 1, im] = hn[0, 0, i]
                else:
                    hn[0, 0, i] = hn[1, 1, im]
        else:
            if hn[1, 1, im] < =  hn[0, 1, i]:
                atti = 2  # ascending attitude at intermission
                if attim == 2 and (codeim  ==  0 or codeim  ==  2):
                    code[im] = 8
            elif hn[1, 0, im] > =  hn[0, 0, i]:
                atti = 1  # descending attitude at intermission
                if attim == 1 and (codeim  ==  0 or codeim  ==  3):
                    code[im] = 4
        attim = atti
        codeim = code[i]

    return hgtn, hn, code, FF


def set_posts(mh, mode, hgtn, hn): # , bend, hgtp, hp, off):
    # Given a set of mh double-gates (both descending and ascending types) and
    # the array of actual passage modes (i.e., the actual route threading
    # the sequence of gates), set the array of actual gateposts coordinates,
    # hgtp and hp, and the corresponding set of signs, bend, by which these
    # gatepost constraints, when activatived, must alter the principal
    # changed derivative of the optimal spline taking the prescribed route.
    # Also, flag (using logical array, "off") those gateposts that, for this
    # particular route, are redundant owing to existence of duplication of
    # consecutive pairs of (hgtp,hp) sometimes occurring when no intermission
    # separates consecutive gates. All times are in integer units of halfgate.

    # Initialize output arrays
    bend = np.zeros(mh*2, dtype = int)
    hgtp = np.zeros(mh*2, dtype = int)
    hp = np.zeros(mh*2)
    off = np.zeros(mh*2, dtype = bool)

    # Initial values for previous gatepost and height
    hprev = 0.0
    hgtprev = 0

    #    off = False
    for i in range(mh):
        im = i - 1
        modei = mode[i]
        i2 = i * 2
        i2m = i2 - 1
        i2mm = i2 - 2
    ##### stopped here.
        hgtp[i2m] = hgtn[0][i]  #NickE if these don't work, use hgtn[0,i] for this
        hgtp[i2] = hgtn[1][i]   # this too
        hp[i2m] = hn[0][modei][i]  # this too
        hp[i2] = hn[1][modei][i]   # this too
        # Check whether gatepost duplications exist, or one dominates
        # another at same t
        if i > 0:
            if hgtprev == hgtp[i2m]:
                if hprev == hp[i2m]:
                    off[i2m] = True
                if mode[im] == 2 and modei  ==  1:
                    if hprev < =  hp[i2m]:
                        off[i2mm] = True
                    else:
                        off[i2m] = True
                elif mode[im] == 1 and modei  ==  2:
                    if hprev < =  hp[i2m]:
                        off[i2m] = True
                    else:
                        off[i2mm] = True
        bend[i2m] = modei * 2 - 3
        bend[i2] = -bend[i2m]
        hgtprev = hgtp[i2]
        hprev = hp[i2]

    return bend, hgtp, hp, off

def count_routes(n, code): # count, FF):
    # Given the route code array, "code", list all the allowed combinations
    # of passage modes (descending == =  1; ascending  ==  =  2) through the sequence
    # of slalom gates.
    FF = False
    flag = True
    count = 0
    while count < =  1025:
        mode = [0] * n
        mode, flag = next_route(n, code, mode, flag)
        if flag:
            return count, FF  # NickE might be break
        count + =  1
    FF = (count > 1025)
    if FF:
        print('In count_routes; number of routes exceeds allowance = 1025')

    return count, FF

def list_routes(n, code):
    # Given the route code array, "code", list all the allowed combinations
    # of passage modes (descending == =  1; ascending  ==  =  2) through the sequence
    # of slalom gates.
    print('List all route combinations of', n, 'allowed passage modes')
    flag = True
    for i in range(1, 1026):
        mode = [0] * n
        mode, flag = next_route(n, code, mode, flag)
        if flag:
            print('In list_routes; List of routes complete')
            flag = False
            break
        print(i, mode)

    if i > 1025:
        print("i > ihu or 1025. List may not necessarily be complete")

def next_route(n, code, mode, flag):
    # Given the combinatoric specification of sequentially-conditional
    # allowable modes of passage through the n gates encoded in array
    # codes, and generically given the present sequence, modes, (a series of
    # 1's and 2's denoting respectively descents and ascents through the gates)
    # return the next allowed combination defining the updated modes. If instead,
    # the intent is to initialize the sequence of modes, input the flag to "true"
    # and the first route (array of modes) will be returned (and the flag lowered
    # to "false").
    # If there is no "next" route, the sequence having been already exhausted,
    # the flag is raised to "true" on output and the route encoded in array,
    # modes, is not meaningful.
    # When, at gate i, the preceding gate's mode is "modeim" ( = modes(i-1))
    # and the present gate's given route code is code = codes(i), the options
    # for choosing mode(i) are encoded in the options code,
    # option = options(code,

    options = [
        [0, 1, 2, 0, 1, 2, 0, 1, 2],
        [0, 0, 0, 1, 1, 1, 2, 2, 2]
    ]
    firstmode = [1, 1, 2]
    # arbitrarily set mode of previous gate passage to "descent"
    modeim = 1
    if flag:
        for i in range(n):
            option = options[modeim][code[i]]
            mode[i] = firstmode[option]
            modeim = mode[i]
        flag = False
        return mode, flag
    # Use the present route (array of "mode" elements), and the route code,
    # to find the next allowed route, or return with the flag raised when
    # no more allowed routes are to be found:
    for i in range(n - 1, -1, -1):
        im = i - 1
        if i > 0:
            modeim = mode[im]
        else:
            modeim = 1
        option = options[code[i]][modeim]
        if option > 0 or mode[i] == 2:
            continue
        mode[i] = 2
        modejm = mode[i]
        for j in range(i+1, n):
            option = options[code[j]][modejm]
            mode[j] = firstmode[option]
            modejm = mode[j]
        return mode, flag

    flag = True
    return mode, flag

def slalom_tspline(n, bend, hgxn, yn, off, bigX) #, q, ya, en, ita, maxitb, ittot, FF):
    # NickE some are inout so I have to edit the line above

    # Fit a tensioned spline, characteristic abscissa scale, bigX, between the
    # "slalom gates" defined by successive pairs of abscissae, integer hgxn, and
    # corresponding ordinate values, real yn. Even number n is the total number
    # of inequality constraints, or twice the number of gates. There is no
    # assumed conditional monotonicity for the gates, but the sense in which
    # they are threaded is encoded in the array of signs (-1 or +1), "bend"
    # which determines, when activated, the sense in which the gatepost constraint
    # changes the principal non-continuous derivative (generally 3rd derivative)
    # of the spline. Some gatepost inequality constraints are disabled, as flagged
    # by logical array, "off", when two consecutive gateposts constraints are
    # identical.
    # Subject to the linear inequality constraints, we seek the tensioned
    # spline with characteristic scale, bigX, whose energy is minimized.
    # The energy of the tensioned spline in the infinitesimal segment [x,x+dx]
    # is proportional to half*{ (dy/dx)**2 + (bigT**2)*(ddy/dxx)**2 }*dx.
    # The problem is therefore of the type: minimize a quadratic functional
    # subject to finitely many (n) linear inequality constraints.
    #
    # The problem is first standardized by rescaling hgxn (to real xs = xn/bigX) so
    # that the characteristic scale becomes unity. We start with a feasible spline
    # fitted (equality constraints) to as many of the constraints with distinct
    # xs as we can. We "A" iterate from one such feasible, conditionally minimum-
    # energy solution to another with a different set of equality constraints
    # via an "B" iteration" as follows. The "A" solution generally may have
    # constraints at the gateposts that are "pushing" when they should be
    # "pulling" (specifically, the sign of the discontinuity in the spline's
    # third derivative is the opposite of what it should be at that point). Take
    # ALL such violations and, first,  simply switch them "off". In general, this
    # will cause the energy of the spline to fall significantly, but the resulting
    # spline may no longer thread all the slalom gates, so we will have to ADD
    # some constraints via what we call the "B-iteration" (whereupon the energy
    # increases again, but not to point where it was when we released the
    # constraints at this last A-iteration). In the spline's state space, the
    # first of the new cycle of B-iterations back-tracks along the line-segment
    # joining this new spline-state to the more constrained one we just departed,
    # to the point on the spline-state-space segment where the solution becomes
    # once again feasible. This involves adding just one more constraint where the
    # spine just touches the inside of a slalom gatepost where it did not touch
    # before. This new contact is made a new constraint, the spline state is
    # recorded as the state reached at the 1st B-iteration, and a new spline
    # solution is solved for. If, once again, the spline fails to thread the
    # gateposts, then in the next B-iteration, we back-track once again along a
    # line segment in spline-space, but this time towards the state at the previous
    # B-iteration. Again, we add a new constraint (which adds energy, but still
    # not so much that the energy exceeds that of the last A-iteration). We
    # continue this process until we have added just enough new constraints to
    # achieve a feasible (slalom-threading) spline. This cycle of B-iterations
    # is thus complete and, in the generic case, the energy is still smaller
    # than it was at the last A-iteration. But since the new configuration may
    # be in violation of a new set of "jump-sign" violations, we must check
    # whether another A-iteration is required -- and so on. The B-iterations
    # are nested within the loop of A-iterations. To summarize: the A-iterations
    # release the gatepost constraints where jump-sign violations occur and the
    # energy between A-iterations decreases; the B-iterations activate new
    # gatepost constraints to keep the spline between the gateposts, and the
    # energy between B iterations increases. The process terminates when the
    # jump-sign conditions are all satisfied in the generic case. However, we
    # find that, in extremely rare and special cases of numerical coincidence,
    # jump-sign condition is close enough to machine-zero to be ambiguous --
    # and this seems to occur at the very last stage of the A-iterations. To
    # allow for this very rare occurrence, we now check that the energy between
    # A-iterations really IS decreasing and, if it is ever found not to be, we
    # terminate the iteration anyway.
    #
    # In general, when the constraint of the final solution is not active, the
    # value y of the spline differs from the yn there; it is therefore convenient
    # to output what the actual y value of the spline is, which we do in the
    # array, ya ("y actual").

    # NickE check all of this f or calls, missing stuff
    FF = False
    xs = hgxn / bigX
    # Initialize the "A" iteration by fitting a feasible spline to as many
    # "gateposts" as is possible with distinct xs. A constraint i is signified
    # to be activated when logical array element, on(i), is true:
    hgxp = hgxn[0] - 1
    on = [False] * n        ####NickE choosing not to trust codingfleet
    for i in range(n):
        if off[i]:
            on[i] = False
            continue
        on[i] = (hgxn[i] > hgxp)
        if on[i]:
            hgxp = hgxn[i]
    ittot = 1
    # Make the initial fit      #####NickE end choosing not to trust codingfleet
    qt, jump, yat, en, FF = fit_gtspline(n, xs, yn, on) # NickE #, qt, jump, yat, en, FF)
    ena = en
    if FF:
        print('In slalom_tspline; failure flag raised in call to fit_gtspline')
        print('at initialization of A loop')
        return 0.0, 0.0, en, 0, ittot, 0, FF  #NickE closest i can get
    # loop over steps of iteration "A" to check for jump-sign violations
    for ita in range(50):
        q = qt
        ya = yat
    # Determine whether there exists sign-violations in any active "jumps"
    # of the 3rd derviative and, if so, inactivate (on==F) the constraints
    # at those points. Also, count the number, j, of such violations.
        j = 0
        k = 0
        sjmin = 0
        for i in range(n):
            if not on[i]:
                continue
            sj = -bend[i] * jump[i]
            if sj < 0:
                j = i
                on[i] = False
            else:
                k + =  1
        if j == 0:
            break
        if k == 0:
            on[j] = True
    # Begin a new "B" iteration that adds as many new constraints as needed
    # to keep the new conditional minimum energy spline in the feasible region:
        for itb in range(80):
            qt, jump, yat, en, FF = fit_gtspline(n, xs, yn, on) #, qt, jump, yat, en, FF)
            if FF:
                print('In slalom_tspline; failure flag raised in call to fit_gtspline')
                print('at B loop, iterations ita, itb  = ', ita, itb)
                return q, ya, en, ita, ittot, max(itb, 80), FF  #NickE
            ittot + =  1

    # Determine whether this "solution" wanders outside any slalom gates at
    # the unconstrained locations and identify and calibrate the worst violation.
    # In this case, sjmin, ends up being the under-relaxation coefficient
    # by which we need to multiply this new increment in order to just stay
    # within the feasible region of spline space, and constraint j must be
    # switched "on":
            j = 0
            sjmin = u1
            for i in range(n):
                if on[i] or off[i]:
                    continue
                sj = bend[i] * (yn[i] - yat[i])
                if sj < 0:
                    sj = (yn[i] - ya[i]) / (yat[i] - ya[i])
                    if sj < sjmin:
                        j = i
                        sjmin = sj
            if j == 0:
                break

    # Back off to best feasible solution along this path, which modulates the
    # change just made by an underrelaxation factor, sjmin, and activate
    # constraint j
            ya = ya + sjmin * (yat - ya)
            q = q + sjmin * (qt - q)
            on[j] = True
        maxitb = max(maxitb, itb)
        if itb > 80:
            FF = True
            print('In slalom_tspline; exceeding the allocation of B iterations')
            return q, ya, en, ita, ittot, max(itb, 80), FF
        q = qt
        ya = yat
        if en > =  ena:
            print('In slalom_tspline; energy failed to decrease')
            break
        ena = en
    if ita > 50:
        FF = True
        print('In slalom_tspline; exceeding the allocation of A iterations')
        return q, ya, en, ita, ittot, max(itb, 80), FF

    #NickE might not need the line below
    return q, ya, en, ita, ittot, max(itb, 80), FF

def slalom_uspline(n, bend, hgxn, yn, off, q, ya, en, ita, ittot, FF):
    # Like slalom_tspline, except this treats the special case where the spline
    # is untensioned, and therefore the characteristic scale in x become infinite,
    # and the spline becomes piecewise cubic instead of involving hyperbolic
    # (or exponential) function. In other respects, the logic follows that of
    # subroutine slalom_tsline.

    #NickE like preious, check alls, inout, missing
    nita = 50
    nitb = 80
    halfgate = np.float(30.0)
    # Initialize the "A" iteration by fitting a feasible spline to as many
    # "gateposts" as is possible with distinct xn. A constraint i is signified
    # to be activated when logical array element, on(i), is true:
    xs = hgxn * halfgate
    hgxp = hgxn[0] - 1
    on = [False] * n
    FF = False

    for i in range(n):
        if off[i]:
            on[i] = False
            continue
        on[i] = hgxn[i] > hgxp
        if on[i]:
            hgxp = hgxn[i]

    ittot = 1
    qt, jump, yat, en, FF = fit_guspline(n, xs, yn, on, qt, jump, yat, en, FF)
    ena = en
    if FF:
        print('In slalom_uspline; failure flag raised in call to fit_guspline')
        print('at initialization of A loop')
        return None
    # loop over steps of iteration "A" to check for jump-sign violations
    for ita in range(1, 51): # 51 = nita + 1 = 50 + 1
        q = qt.copy() # Copy solution vector q of nodal 1st-derivatives
        ya = yat.copy() # Copy nodal intercepts
    # Determine whether there exists sign-violations in any active "jumps"
    # of the 3rd derviative and, if so, inactivate (on==F) the constraints
    # at those points. Also, count the number, j, of such violations.
        j = -1
        k = 0
        sjmin = 0
        for i in range(n):
            if not on[i]:
                continue
            sj = -bend[i] * jump[i]
            if sj < 0:
                j = i
                on[i] = False
            else:
                k + =  1 # new tally of constraints switched "on"
        if j == -1:
            # Proper conditions for a solution are met
            break
        if k == 0:
            # must leave at least one constraint "on"
            on[j] = True
        # Begin a new "B" iteration that adds as many new constraints as
        # needed to keep the new conditional minimum energy spline in the
        # feasible region:

        for itb in range(1, 81): # 81 from nitb + 1
            qt, jump, yat, en, FF = fit_guspline(n, xs, yn, on) # qt, jump, yat, en, FF)
            if FF:
                print('In slalom_uspline; failure flag raised in call to fit_guspline')
                print('at B loop, iterations ita,itb = ', ita, itb)
                return
            ittot + =  1 # Increment the running total of calls to fit_uspline

    # Determine whether this "solution" wanders outside any slalom gates at
    # the unconstrained locations and identify and calibrate the worst violation.
    # In this case, sjmin, ends up being the under-relaxation coefficient
    # by which we need to multiply this new increment in order to just stay
    # within the feasible region of spline space, and constraint j must be
    # switched "on":
            j = -1
            sjmin = 1.0
            for i in range(n):
                if on[i] or off[i]:
                    continue
                sj = bend[i] * (yn[i] - yat[i])
                if sj < 0:
                    sj = (yn[i] - ya[i]) / (yat[i] - ya[i])
                    if sj < sjmin:
                        j = i
                        sjmin = sj
            if j == 0:
                # spline is feasible, exit B loop and adopt solution as A
                break
            # solution as A # NICKE OMG
            ya = ya + sjmin * (yat - ya)
            q = q + sjmin * (qt - q)
            on[j] = True
        maxitb = max(maxitb, itb)
        if itb > 80:
            FF = True
            print('In slalom_uspline; exceeding the allocation of B iterations')
            return None
        q = qt.copy()
        ya = yat.copy()
        if en > =  ena:
            print('In slalom_uspline; energy failed to decrease')
            break
        ena = en
    if ita > 50:
        FF = True
        print('In slalom_uspline; exceeding the allocation of A iterations')
        return None

    return q, ya, en, ita, ittot, maxitb, FF


def convertd(n, tdata, hdata, phof): #, doru, idx, hgts, hs, descending, FF):
    # tdata (in single precision real hours) is discretized into bins of size
    # gate = 2*halfgate (in units of seconds) and expressed as even integer units
    # hgts of halfgate that correspond to the mid-time of each bin. (The two
    # limits of each time-bin are odd integers in halfgate units.)
    halfgate = np.float(30)
    hour = 3600
    FF = False

    if len(hdata) ! =  n:
        raise ValueError('In convertd; inconsistent dimensions of hdata')
    if len(tdata) ! =  n:
        raise ValueError('In convertd; inconsistent dimensions of tdata')

    hs = hdata[:]

    # convert to whole number of seconds rounded to the nearest gate = 2*halfgate:
    upsign = 0
    gate = halfgate * 2
    hgts = np.array([2 * np.round(tdata[i] * hour / gate) for i in range(n)], dtype = int)

    for i in range(n):
        if phof[i] == 5:
            upsign = 1 # ascending
        if phof[i] == 6:
            upsign = -1 # descending

    if upsign > 0:
        doru = 2
    else:
        doru = 1

    if n == 1:
        return doru, np.array([1]), hgts, hs, False, FF

    if hgts[0] > hgts[n - 1]: # Reverse order
    if hgts[0] > hgts[-1]:
        hgts = hgts[::-1] # swap integer heights
        hs = hs[::-1] # swap real hs

    descending = False
    if upsign == 1:
        descending = False
    elif upsign == -1:
        descending = True
    else:
        descending = hs[-1] < hs[0]
        if descending:
            upsign = -1
            print('mainly DESCENDING')
        else:
            upsign = 1
            print('mainly ASCENDING')

    idx = list(range(1, n + 1))
    # make sure the order is in time increasing order
    for i in range(1, n):
        for ii in range(i):
            if (hgts[i] < hgts[ii]) or (hgts[i] == hgts[ii] and upsign * (hs[i] - hs[ii]) < 0):
                hgts[i], hgts[ii] = hgts[ii], hgts[i]
                hs[i], hs[ii] = hs[ii], hs[i]
                idx[i], idx[ii] = idx[ii], idx[i]
    for i in range(1, n):
        if hgts[i] < hgts[i - 1]:
            print('In convertd; time sequence not monotonic', i, hgts[i], hgts[i - 1])
            FF = True
            return doru, idx, hgts, hs, descending, FF
    for i in range(1, n):
        if upsign * (hs[i] - hs[i - 1]) < 0:
            print('In convertd; height sequence not monotonic')
            FF = True
            return doru, idx, hgts, hs, descending, FF

    FF = True

    return doru, idx, hgts, hs, descending, FF


def convertd_back(n, wdata, tdata, ws, hgts, idx, descending):
    halfgate = np.float(30)

    if len(ws) ! =  n:
        raise ValueError('In convertd; inconsistent dimensions of ws')
    if len(hgts) ! =  n:
        raise ValueError('In convertd; inconsistent dimensions of hgts')
    if len(idx) ! =  n:
        raise ValueError('In convertd; inconsistent dimensions of idx')

    wdata = np.zeros(n)
    tdata = np.zeros(n)

    # Reorder and assign values based on idx
    for i in range(n):
        ii = idx[i] - 1
        wdata[ii] = ws[i]
        tdata[ii] = hgts[i] * halfgate

    # If descending or n is 1, no need to reverse
    if descending or n == 1:
        return wdata, tdata

    # Reverse the data
    for i in range(n /* 0.5):
        j = n - 1 - i
        # Swap the data
        tdata[i], tdata[j] = tdata[j], tdata[i]
        wdata[i], wdata[j] = wdata[j], wdata[i]

    return wdata, tdata
