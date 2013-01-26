#!/usr/bin/python

from numpy import *
from scipy.stats import norm
import scipy.optimize as opt

_min_dev = 0.05

def ceilit(arr):
    for i in range(0,len(arr)):
        arr[i] = min(arr[i], 0.6)

def check_max(func, x, i, name, disp):
    try:
        ret = func(x)
        if ret[i] == 0:
            return ret[0]
        print 'OPT.' + name + ': did not converge'
    except:
        print 'OPT.' + name + ': error'
    return None

def maximize(L, DL, D2L, x, method=None, disp=False):
    mL = lambda x: -L(x)
    mDL = lambda x: -DL(x)
    mD2L = lambda x: -D2L(x)

    if method == None or method == 'ncg':
        func = lambda x0: opt.fmin_ncg(mL, x0, fprime=mDL, fhess=mD2L, disp=disp, full_output=True, avextol=1e-10)
        xm = check_max(func, x, 5, 'NCG', disp)
        if xm != None:
            return xm

    if method == None or method == 'bfgs':
        func = lambda x0: opt.fmin_bfgs(mL, x0, fprime=mDL, disp=disp, full_output=True, gtol=1e-10)
        xm = check_max(func, x, 6, 'BFGS', disp)
        if xm != None:
            return xm

    if method == None or method == 'powell':
        func = lambda x0: opt.fmin_powell(mL, x0, disp=disp, full_output=True, ftol=1e-10)
        xm = check_max(func, x, 5, 'POWELL', disp)
        if xm != None:
            return xm

    func = lambda x0: opt.fmin(mL, x0, disp=disp, full_output=True, ftol=1e-10)
    xm = check_max(func, x, 4, 'DOWNHILL_SIMPLEX', disp)
    return xm

def fix_ww(myr, mys, oppr, opps, oppc, W, L):
    played_cats = sorted(unique(oppc))
    wins = zeros(len(played_cats))
    losses = zeros(len(played_cats))
    M = len(W)

    for j in range(0,M):
        wins[played_cats.index(oppc[j])] += W[j]
        losses[played_cats.index(oppc[j])] += L[j]
    pi = nonzero(wins*losses == 0)[0]

    for c in pi:
        W = append(W, 1)
        L = append(L, 1)
        oppr = append(oppr, myr[0])
        opps = append(opps, mys[0])
        oppc = append(oppc, played_cats[c])

    return (oppr, opps, oppc, W, L)

def update(myr, mys, oppr, opps, oppc, W, L, text='', pr=False, Ncats=3):
    if len(W) == 0:
        return(myr, mys, [None] * (Ncats+1), [None] * (Ncats+1))

    (oppr, opps, oppc, W, L) = fix_ww(myr, mys, oppr, opps, oppc, W, L)

    if pr:
        print text
        print oppr
        print opps
        print oppc
        print W
        print L

    played_cats = sorted(unique(oppc))
    tot = sum(myr[array(played_cats)+1])
    M = len(W)
    C = len(played_cats)

    def loc(x):
        return array([played_cats.index(c) for c in x])

    def glob(x):
        return array([played_cats[c] for c in x])

    def extend(x):
        return hstack((x, tot-sum(x[1:])))

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
    gen_phi = lambda j, x: norm.pdf(x, loc=mbar[j], scale=sbar[j])
    gen_Phi = lambda j, x: norm.cdf(x, loc=mbar[j], scale=sbar[j])

    def logL(x):
        Mv = x[0] + extend(x)[loc(oppc)+1]
        Phi = array([gen_Phi(i,Mv[i]) for i in range(0,M)])
        return sum(W*log(Phi) + L*log(1-Phi))

    def DlogL(x):
        Mv = x[0] + extend(x)[loc(oppc)+1]
        phi = array([gen_phi(i,Mv[i]) for i in range(0,M)])
        Phi = array([gen_Phi(i,Mv[i]) for i in range(0,M)])
        vec = (W/Phi - L/(1-Phi)) * phi
        return array(vec * matrix(DM))[0]

    def D2logL(x, DM, C):
        Mv = x[0] + extend(x)[loc(oppc)+1]
        phi = array([gen_phi(i,Mv[i]) for i in range(0,M)])
        Phi = array([gen_Phi(i,Mv[i]) for i in range(0,M)])
        alpha = phi/Phi
        beta = phi/(1-Phi)
        Mvbar = (Mv-mbar)/sbar**2
        coeff = - W*alpha*(alpha+Mvbar) - L*beta*(beta-Mvbar)
        ret = zeros((C,C))
        for j in range(0,M):
            ret += coeff[j] * outer(DM[j,:], DM[j,:])
        return ret

    x = hstack((myr[0], myr[played_cats]))[0:-1]
    x = maximize(logL, DlogL, lambda x: D2logL(x,DM,C), x)

    if x == None:
        print 'Failed to converge for %s' % text
        return (myr, mys)

    devs = maximum(-1/diag(D2logL(x, DMex, C+1)), _min_dev)
    rats = extend(x)
    news = zeros(len(myr))
    newr = zeros(len(myr))

    ind = [0] + [f+1 for f in played_cats]
    news[ind] = 1./sqrt(1./devs**2 + 1./mys[ind]**2)
    newr[ind] = (rats/devs**2 + myr[ind]/mys[ind]**2) * news[ind]**2

    ind = ind[1:]
    m = (sum(newr[ind]) - tot)/len(ind)
    newr[ind] -= m
    newr[0] += m

    ind = setdiff1d(range(0,len(myr)), [0] + ind)
    news[ind] = mys[ind]
    newr[ind] = myr[ind]

    news = (abs(news-_min_dev)+news-_min_dev)/2 + _min_dev
    ceilit(news)

    m = mean(newr[1:])
    newr[1:] -= m
    newr[0] += m

    devsex = [None] * (Ncats + 1)
    ratsex = [None] * (Ncats + 1)
    devsex[0] = devs[0]
    ratsex[0] = rats[0]
    for c in played_cats:
        devsex[c+1] = devs[played_cats.index(c)+1]
        ratsex[c+1] = rats[played_cats.index(c)+1]
    
    return (newr, news, ratsex, devsex)
