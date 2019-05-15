import numpy as np
from numpy import mod, outer, mean, argsort, std
from numpy import pi, linspace, newaxis, roll, zeros, angle
from numpy.linalg import norm, eig
from scipy.signal import detrend


def match_ends(Z):
    n = Z.shape[1]  # No of columns
    return Z - outer(Z[:, n - 1] - Z[:, 0], linspace(0, 1, n))


def mean_center(Z):
    return Z - mean(Z, axis=1)[:, newaxis]


def total_variation(Z, axis=0):
    dZ = Z - roll(Z, 1, axis=axis)
    return norm(dZ, axis=axis).squeeze()


# Normalize vector(s) Z so that the quadratic sum equals to 1.
def quad_norm(Z):
    norms = norm(Z, axis=1)
    normed_z = Z / norms[:, newaxis]
    return normed_z


# Normalize vector(s) Z so that the quadratic variation is 1. 
def tv_norm(Z):
    norms = total_variation(Z, axis=1)
    if norms.shape == ():
        normed_z = Z / norms
    else:
        normed_z = Z / norms[:, newaxis]
    return normed_z


# Normalize vector(s) Z so that standard deviation is 1
def std_norm(Z):
    norms = std(Z, axis=1)
    normed_z = Z / norms[:, newaxis]
    return normed_z


def remove_linear(Z):
    return detrend(Z)


def cyc_diff(x):
    return np.diff(np.concatenate(([x[-1]], x)))


def create_lead_matrix(data):
    N, time_steps = data.shape
    lead_matrix = zeros((N, N))

    # Create index list of upper_trinagle (lower part is anti-symmetric)
    # This is good for small values of N.
    # For larger values, just do a double "for" loop
    upper_triangle = [(i, j) for i in range(N) for j in range(i + 1, N)]

    for (i, j) in upper_triangle:
        x, y = data[i], data[j]
        d = x.dot(cyc_diff(y)) - y.dot(cyc_diff(x))
        lead_matrix[i, j] = d
        lead_matrix[j, i] = -d

    return lead_matrix * 10


# LM: lead matrix (square matrix to be sorted)
# p: eigenvector index to use (0...)
def sort_lead_matrix(LM, p=1):
    # The first input should be the matrix to be sorted, the second is the
    # phase or eigenvector to use (default 1).
    evals, phases = eig(LM)
    phases = phases[:, 2 * p - 2]
    sorted_ang = np.sort(mod(angle(phases), 2 * pi))
    dang = np.diff(np.hstack((sorted_ang, sorted_ang[0] + 2 * pi)))
    shift = np.argmax(np.abs(dang))
    shift = (shift + 1) % phases.size

    shift = sorted_ang[shift]
    perm = argsort(mod(mod(angle(phases), 2 * pi) - shift, 2 * pi))
    # print(perm)
    sortedLM = LM[perm].T[perm].T

    return LM, phases, perm, sortedLM, evals


# def cyclic_analysis(data, p, normalize, trend_removal):
#     (_, detrender) = trend_removals[trend_removal]
#     (_, normalization) = norms[normalize]
#     normed_data = normalization(detrender(mean_center(match_ends(data))))
#     lead_matrix = create_lead_matrix(normed_data)
#     return sort_lead_matrix(lead_matrix, p), normed_data

def cyclic_analysis(data, p):
    lead_matrix = create_lead_matrix(match_ends(data))
    return sort_lead_matrix(lead_matrix, p) 

def wilks_lambda(data, classes):
    n_classes = set(classes)
    classes, data, val = np.asarray(classes), np.asarray(data), list()
    for X_var in data.T:
        C, W = np.cov(X_var), 0
        for k in n_classes:
            Xin = X_var[classes==k]
            Cg = np.cov(Xin)
            W = W + Cg * (len(Xin) -1)
        C = C*(len(X_var) -1)
        val.append(W/C)
    return sorted(val), np.argsort(val)


def gs_regression(data):
    N, M = data.shape
    g = 1.0/M * data @ np.ones((M,1))
    bg = np.linalg.pinv(g) @ data

    return (data - g @ bg).T


norms = {None: ('Leave Intact', lambda t: t),
         'sqr': ('Unit Squares', quad_norm),
         'tv': ('Unit Quadratic Variation', tv_norm), 
         'std': ('Unit Standard Deviation', std_norm)}

trend_removals = {None: ('None', lambda t: t),
                  'linear': ('Remove Linear Trend', remove_linear)}
