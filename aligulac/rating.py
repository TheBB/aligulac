'''
This is where the rating magic happens. Imported by period.py.
'''

from numpy import *

from aligulac.settings import (
    INIT_DEV,
    MIN_DEV,
    PRF_INF,
    PRF_MININF,
    PRF_NA,
)
from ratings.tools import (
    pdf,
    cdf,
)

LOG_CAP = 1e-10
TOL = 1e-3 / 2

def maximize(L, DL, D2L, x, disp=False):
    """Main function to perform numerical optimization. L, DL and D2L are the objective function and its
    derivative and Hessian, and x is the initial guess (current rating)."""
    mL = lambda x: -L(x)
    mDL = lambda x: -DL(x)
    mD2L = lambda x: -D2L(x)

    for i in range(100):
        y = linalg.solve(mD2L(x), mDL(x))
        if linalg.norm(y, ord=inf) < TOL:
            break
        x = x - y

    if i == 100:
        print('Returning None!')
        return None
    return x


def maximize_1d(L, DL, D2L, x, disp=False):
    mL = lambda x: -L(x)
    mDL = lambda x: -DL(x)
    mD2L = lambda x: -D2L(x)

    for i in range(100):
        y = mDL(x) / mD2L(x)
        if abs(y) < TOL:
            break
        x = x - y

    if i == 100:
        print('Returning None! (perf)')
        return None
    return x


def fix_ww(myr, mys, oppr, opps, oppc, W, L):
    """This function adds fake games to the oppr, opps, oppc, W and L arrays if the player has 0-N or N-0
    records against any category."""
    played_cats = sorted(unique(oppc))
    wins = zeros(len(played_cats))
    losses = zeros(len(played_cats))
    M = len(W)

    # Count wins and losses against each category
    for j in range(0,M):
        wins[played_cats.index(oppc[j])] += W[j]
        losses[played_cats.index(oppc[j])] += L[j]

    # Find the categories where the record is 0-N or N-0 with N>0
    pi = nonzero(wins*losses == 0)[0]

    # Add fake games for each of the relevant categories
    for c in pi:
        W = append(W, 1)
        L = append(L, 1)
        oppr = append(oppr, myr[0] + myr[1+played_cats[c]])
        opps = append(opps, sqrt(mys[0]**2 + mys[1+played_cats[c]]**2))
        oppc = append(oppc, played_cats[c])

    # Return the new arrays
    return (oppr, opps, oppc, W, L)


def performance(oppr, opps, oppc, W, L):
    opp = zip(oppr, opps, oppc, W, L)

    ret = [0.0, 0.0, 0.0, 0.0]
    meanok = True

    for cat in range(0,3):
        spopp = [o for o in opp if o[2] == cat]
        sW = sum([o[3] for o in spopp])
        sL = sum([o[4] for o in spopp])

        if sW == 0 and sL == 0:
            ret[cat+1] = PRF_NA
            meanok = False
        elif sW == 0:
            ret[cat+1] = PRF_MININF
            meanok = False
        elif sL == 0:
            ret[cat+1] = PRF_INF
            meanok = False
        else:
            gen_phi = lambda p, x: pdf(x, loc=p[0], scale=sqrt(1+p[1]**2))
            gen_Phi = lambda p, x: max(min(cdf(x, loc=p[0], scale=sqrt(1+p[1]**2)), 1-LOG_CAP), LOG_CAP)

            def logL(x):
                ret = 0.0
                for p in spopp:
                    gP = gen_Phi(p,x)
                    ret += p[3] * log(gP) + p[4] * log(1-gP)
                return ret

            def DlogL(x):
                ret = 0.0
                for p in spopp:
                    gp = gen_phi(p,x)
                    gP = gen_Phi(p,x)
                    ret += (float(p[3])/gP - float(p[4])/(1-gP)) * gp
                return ret

            def D2logL(x):
                ret = 0.0
                for p in spopp:
                    gp = gen_phi(p,x)
                    gP = gen_Phi(p,x)
                    alpha = gp/gP
                    beta = gp/(1-gP)
                    sb = sqrt(1+p[1]**2)
                    Mv = pi/sqrt(3)/sb * tanh(pi/2/sqrt(3)*(x-p[0])/sb)
                    ret -= p[3]*alpha*(alpha+Mv) + p[4]*beta*(beta-Mv)
                return ret

            perf = maximize_1d(logL, DlogL, D2logL, 0.0)
            ret[cat+1] = perf

    if meanok:
        ret[0] = sum(ret[1:]) / 3
    else:
        ret[0] = PRF_NA

    return ret

def update(myr, mys, oppr, opps, oppc, W, L, text='', pr=False, Ncats=3):
    """This function updates the rating of a player according to the ratings of the opponents and the games
    against them."""
    
    if len(W) == 0:
        return(myr, mys)

    if pr:
        print(text)
        print(oppr, len(oppr))
        print(opps, len(opps))
        print(oppc, len(oppc))
        print(W, len(W))
        print(L, len(L))

    played_cats = sorted(unique(oppc))          # The categories against which the player played
    played_cats_p1 = [p+1 for p in played_cats]
    tot = sum(myr[array(played_cats)+1])        # The sum relative rating against those categories
                                                # (will be kept constant)
    M = len(W)                                  # Number of opponents
    C = len(played_cats)                        # Number of different categories played

    # Convert global categories to local
    def loc(x):
        return array([played_cats.index(c) for c in x])

    # Convert local categories to global
    def glob(x):
        return array([played_cats[c] for c in x])

    # Extends a M-vector to an M+1-vector according to the restriction given
    # (that the sum of relative ratings against the played categories is constant)
    def extend(x):
        return hstack((x, tot-sum(x[1:])))

    # Ensure that arrays are 1-dimensional
    def dim(x):
        if x.ndim == 0:
            x = array([x])
        return x

    # Prepare some vectors and other numbers that are needed to form objective functions, derivatives and
    # Hessians
    DM = zeros((M,C))
    DMex = zeros((M,C+1))
    DM[:,0] = 1
    DMex[:,0] = 1
    for j in range(0,M):
        lc = loc([oppc[j]])[0]
        if lc < C-1:
            DM[j,lc+1] = 1
        else:
            DM[j,1:] = -1
        DMex[j,lc+1] = 1

    mbar = oppr
    sbar = sqrt(opps**2 + 1)
    gen_phi = lambda j, x: pdf(x, loc=mbar[j], scale=sbar[j])
    gen_Phi = lambda j, x: max(min(cdf(x, loc=mbar[j], scale=sbar[j]), 1-LOG_CAP), LOG_CAP)

    alpha = pi/2/sqrt(3)
    myrc = myr[[0]+played_cats_p1]
    mysc = mys[[0]+played_cats_p1]

    # {{{ Objective function
    def logL(x):
        Mv = x[0] + extend(x)[loc(oppc)+1]
        Phi = array([gen_Phi(i,Mv[i]) for i in range(0,M)])
        if pr:
            print(':::', x, Mv, Phi)
        return sum(W*log(Phi) + L*log(1-Phi))

    def logE(x):
        return sum(log(1 - tanh(alpha*(extend(x)-myrc)/mysc)**2))

    logF = lambda x: logL(x) + logE(x)
    # }}}

    # {{{ Derivative
    def DlogL(x):
        Mv = x[0] + extend(x)[loc(oppc)+1]
        phi = array([gen_phi(i,Mv[i]) for i in range(0,M)])
        Phi = array([gen_Phi(i,Mv[i]) for i in range(0,M)])
        vec = (W/Phi - L/(1-Phi)) * phi
        return array(vec * matrix(DM))[0]

    def DlogE(x):
        ret = -2*alpha*tanh(alpha*(extend(x)-myrc)/mysc)/mysc
        ret = ret[0:-1] - ret[-1]
        return ret

    DlogF = lambda x: DlogL(x) + DlogE(x)
    # }}}

    # {{{ Hessian
    def D2logL(x, DM, C):
        Mv = x[0] + extend(x)[loc(oppc)+1]
        phi = array([gen_phi(i,Mv[i]) for i in range(0,M)])
        Phi = array([gen_Phi(i,Mv[i]) for i in range(0,M)])
        alpha = phi/Phi
        beta = phi/(1-Phi)
        Mvbar = pi/sqrt(3)/sbar * tanh(pi/2/sqrt(3)*(Mv-mbar)/sbar)
        coeff = - W*alpha*(alpha+Mvbar) - L*beta*(beta-Mvbar)
        ret = zeros((C,C))
        for j in range(0,M):
            ret += coeff[j] * outer(DM[j,:], DM[j,:])
        return ret

    def D2logE(x):
        diags = -2*alpha**2*(1 - tanh(alpha*(extend(x)-myrc)/mysc)**2)/mysc**2
        diags, final = diags[0:-1], diags[-1]
        return diag(diags) + final

    def D2logEx(x):
        diags = -2*alpha**2*(1 - tanh(alpha*(extend(x)-myrc)/mysc)**2)/mysc**2
        return diag(diags)

    D2logF = lambda x: D2logL(x,DM,C) + D2logE(x)
    # }}}

    # Prepare initial guess in unrestricted format and maximize
    x = hstack((myr[0], myr[played_cats_p1]))[0:-1]
    x = maximize(logF, DlogF, D2logF, x, disp=pr)
    x = dim(x)

    # If maximization failed, return the current rating and print an error message
    if x == None:
        print('Failed to converge for %s' % text)
        return (myr, mys, [None]*(Ncats+1), [None]*(Ncats+1))

    # Extend to restricted format
    D2 = D2logL(x, DMex, C+1) + D2logEx(x)
    devs = sqrt(-1/diag(D2))
    rats = extend(x)

    if pr:
        print(devs)
        print(rats)

    # Compute new RD and rating for the indices that can change
    news = zeros(len(myr))
    newr = zeros(len(myr))

    ind = [0] + [f+1 for f in played_cats]
    news[ind] = devs
    newr[ind] = rats

    if pr:
        print(news)
        print(newr)

    # Enforce the restriction of sum relative rating against played categories should be constant
    ind = ind[1:]
    m = (sum(newr[ind]) - tot)/len(ind)
    newr[ind] -= m
    newr[0] += m

    if pr:
        print(newr)

    # Ratings against non-played categories should be kept as before.
    ind = setdiff1d(range(0,len(myr)), [0] + ind)
    news[ind] = mys[ind]
    newr[ind] = myr[ind]

    if pr:
        print(news)
        print(newr)

    # Keep new RDs between MIN_DEV and INIT_DEV
    news = minimum(news, INIT_DEV)
    news = maximum(news, MIN_DEV)

    if pr:
        print(news)

    # Ensure that mean relative rating is zero
    m = mean(newr[1:])
    newr[1:] -= m
    newr[0] += m

    if pr:
        print(newr)
        print('------------ Finished')

    return (newr, news)
