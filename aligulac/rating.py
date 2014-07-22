'''
This is where the rating magic happens. Imported by period.py.
'''

from numpy import *

from aligulac.settings import (
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

seterr(invalid='ignore')

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


def performance(oppr, opps, oppc, W, L, text='', pr=False):
    opp = list(zip(oppr, opps, oppc, W, L))

    ret = [0.0, 0.0, 0.0, 0.0]
    meanok = True

    if pr:
        print('Now performance for %s' % text)

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

            perf, init = nan, 1.0
            while isnan(perf):
                perf = maximize_1d(logL, DlogL, D2logL, init)
                init -= 0.1
            ret[cat+1] = perf

    if meanok:
        ret[0] = sum(ret[1:]) / 3
    else:
        ret[0] = PRF_NA

    return ret
    
def update(my_rating, my_stdev,
           opp_rating, opp_stdev, opp_category,
           nwins, nlosses,
           MIN_DEV, INIT_DEV,
           text='', output=False, ncategories=3):

    # If there are no games, the rating is unchanged.
    if sum(nwins) == 0 and sum(nlosses) == 0:
        return(my_rating, my_stdev)

    if output:
        print(text)
        print(opp_rating, len(opp_rating))
        print(opp_stdev, len(opp_stdev))
        print(opp_category, len(opp_category))
        
    # Get the categories against which the player played
    played_categories = sorted(unique(opp_category))
    played_categories_a = array(played_categories)
 
    M = len(nwins)                             # Number of opponents
    C = len(played_categories)                 # Number of categories

    # Modified opponent ratings used for calculating the integrals Ijk, see method.pdf.
    mbar = opp_rating
    sbar = sqrt(opp_stdev**2 + 1)
    
    # Evaluates modified phi (pdf) and Phi (cdf) for all opponents at a given x
    gen_phi = lambda j, x: pdf(x, loc=mbar[j], scale=sbar[j])
    gen_Phi = lambda j, x: max(min(cdf(x, loc=mbar[j], scale=sbar[j]), 1-LOG_CAP), LOG_CAP)
    
    # Converts global cateogry numbers to local ones
    def loc(cats):
        return array([played_categories.index(c) for c in cats])
        
    # Current ratings and stdevs against the played categories
    my_rating_current = my_rating[0] + my_rating[played_categories_a + 1]
    my_stdev_current = my_stdev[played_categories_a + 1]
    alpha = pi/2/sqrt(3)
    
    # Gradient of M_j, see method.pdf.
    DM = zeros((M,C))
    for j in range(0,M):
        lc = loc([opp_category[j]])[0]
        DM[j,lc] = 1
    
    # Objective function (performance in current period)
    def logL(x):
        # Get the rating against the opponents
        rating = x[loc(opp_category)]
        # Evaluate the CDF at that rating
        Phi = array([gen_Phi(i,rating[i]) for i in range(0,M)])
        if output:
            print(':::', x, Mv, Phi)
        return sum(nwins*log(Phi) + nlosses*log(1-Phi))

    # Objective function (current rating)
    def logE(x):
        return sum(log(1 - tanh(alpha*(x - my_rating_current)/my_stdev_current)**2))

    # Total objective function
    logF = lambda x: logL(x) + logE(x)
    
    # First derivative (performance in current period)
    def DlogL(x):
        # Get the rating against the opponents
        rating = x[loc(opp_category)]
        # Evaluate the PDF, CDF at that rating
        phi = array([gen_phi(i,rating[i]) for i in range(0,M)])
        Phi = array([gen_Phi(i,rating[i]) for i in range(0,M)])
        vec = (nwins/Phi - nlosses/(1-Phi)) * phi
        return array(vec * matrix(DM))[0]

    # First derivative (current rating)
    def DlogE(x):
        return -2*alpha*tanh(alpha*(x - my_rating_current)/my_stdev_current)/my_stdev_current

    # Total first derivative
    DlogF = lambda x: DlogL(x) + DlogE(x)
    
    # Second derivative (performance in current period)
    def D2logL(x):
        # Get the rating against the opponents
        rating = x[loc(opp_category)]
        # Evaluate the PDF, CDF at that rating
        phi = array([gen_phi(i,rating[i]) for i in range(0,M)])
        Phi = array([gen_Phi(i,rating[i]) for i in range(0,M)])
        alpha = phi/Phi
        beta = phi/(1-Phi)
        Mvbar = pi/sqrt(3)/sbar * tanh(pi/2/sqrt(3)*(rating-mbar)/sbar)
        coeff = - nwins*alpha*(alpha+Mvbar) - nlosses*beta*(beta-Mvbar)
        ret = zeros((C,C))
        for j in range(0,M):
            ret += coeff[j] * outer(DM[j,:], DM[j,:])
        return ret

    # Second derivative (current rating)
    def D2logE(x):
        diags = -2*alpha**2*(1 - tanh(alpha*(x - my_rating_current)/my_stdev_current)**2)/my_stdev_current**2
        return diag(diags)

    # Total second derivative
    D2logF = lambda x: D2logL(x) + D2logE(x)
           
    # Prepare initial guess and maximize
    x = my_rating[0] + my_rating[played_categories_a + 1]
    x = maximize(logF, DlogF, D2logF, x, disp=output)
    
    if x is None:
        print('Failed to converge for %s' % text)
        return(my_rating, my_stdev)

    if x.ndim == 0:
        x = array([x])
        
    if output:
        print(played_categories)
        print(x)
 
    # Compute new deviation and rating for the indices that can change
    new_rating = zeros(len(my_rating))
    new_stdev = zeros(len(my_rating))
    new_rating[played_categories_a + 1] = x
    D2 = D2logL(x)
    new_stdev[played_categories_a + 1] = sqrt(-1/diag(D2))
    
    # Ratings against non-played categories should be kept as before
    indices = setdiff1d(range(1, len(my_rating)), played_categories_a+1)
    new_rating[indices] = my_rating[0] + my_rating[indices]
    new_stdev[indices] = my_stdev[indices]

    # Update mean rating
    new_rating[0] = mean(new_rating[1:])
    new_rating[1:] -= new_rating[0]

    # Keep new deviations between MIN_DEV and INIT_DEV
    new_stdev = minimum(new_stdev, INIT_DEV)
    new_stdev = maximum(new_stdev, MIN_DEV)

    return (new_rating, new_stdev)
