import itertools
import pickle
import copy

import jax.numpy as np
import numpy as onp
np.random = onp.random
np.matrix = onp.matrix
from sklearn.utils._testing import assert_allclose

import pytest

import scipy.sparse as sp
from scipy.spatial.distance import cdist
from sklearn.metrics import DistanceMetric

from sklearn.metrics._dist_metrics import (
    BOOL_METRICS,
    # Unexposed private DistanceMetric for 32 bit
    DistanceMetric32,
)

from sklearn.utils import check_random_state
from sklearn.utils._testing import create_memmap_backed_data
from sklearn.utils.fixes import sp_version, parse_version


def dist_func(x1, x2, p):
    return np.sum((x1 - x2) ** p) ** (1.0 / p)


rng = check_random_state(0)
d = 4
n1 = 20
n2 = 25
X64 = rng.random_sample((n1, d))
Y64 = rng.random_sample((n2, d))
X32 = X64.astype("float32")
Y32 = Y64.astype("float32")

[X_mmap, Y_mmap] = create_memmap_backed_data([X64, Y64])

# make boolean arrays: ones and zeros
X_bool = X64.round(0)
Y_bool = Y64.round(0)

[X_bool_mmap, Y_bool_mmap] = create_memmap_backed_data([X_bool, Y_bool])


V = rng.random_sample((d, d))
VI = np.dot(V, V.T)


METRICS_DEFAULT_PARAMS = [
    ("euclidean", {}),
    ("cityblock", {}),
    ("minkowski", dict(p=(1, 1.5, 2, 3))),
    ("chebyshev", {}),
    ("seuclidean", dict(V=(rng.random_sample(d),))),
    ("mahalanobis", dict(VI=(VI,))),
    ("hamming", {}),
    ("canberra", {}),
    ("braycurtis", {}),
]
if sp_version >= parse_version("1.8.0.dev0"):
    # Starting from scipy 1.8.0.dev0, minkowski now accepts w, the weighting
    # parameter directly and using it is preferred over using wminkowski.
    METRICS_DEFAULT_PARAMS.append(
        ("minkowski", dict(p=(1, 1.5, 3), w=(rng.random_sample(d),))),
    )
else:
    # For previous versions of scipy, this was possible through a dedicated
    # metric (deprecated in 1.6 and removed in 1.8).
    METRICS_DEFAULT_PARAMS.append(
        ("wminkowski", dict(p=(1, 1.5, 3), w=(rng.random_sample(d),))),
    )


# TODO: Remove filterwarnings in 1.3 when wminkowski is removed
@pytest.mark.filterwarnings("ignore:WMinkowskiDistance:FutureWarning:sklearn")
@pytest.mark.parametrize("metric_param_grid", METRICS_DEFAULT_PARAMS)
@pytest.mark.parametrize("X, Y", [(X64, Y64), (X32, Y32), (X_mmap, Y_mmap)])
def test_cdist(metric_param_grid, X, Y):
    DistanceMetricInterface = (
        DistanceMetric if X.dtype == Y.dtype == np.float64 else DistanceMetric32
    )
    metric, param_grid = metric_param_grid
    keys = param_grid.keys()
    for vals in itertools.product(*param_grid.values()):
        kwargs = dict(zip(keys, vals))
        if metric == "mahalanobis":
            # See: https://github.com/scipy/scipy/issues/13861
            # Possibly caused by: https://github.com/joblib/joblib/issues/563
            pytest.xfail(
                "scipy#13861: cdist with 'mahalanobis' fails on joblib memmap data"
            )

        if metric == "wminkowski":
            # wminkoski is deprecated in SciPy 1.6.0 and removed in 1.8.0
            WarningToExpect = None
            if sp_version >= parse_version("1.6.0"):
                WarningToExpect = DeprecationWarning
            with pytest.warns(WarningToExpect):
                D_scipy_cdist = cdist(X, Y, metric, **kwargs)
        else:
            D_scipy_cdist = cdist(X, Y, metric, **kwargs)

        dm = DistanceMetricInterface.get_metric(metric, **kwargs)
        D_sklearn = dm.pairwise(X, Y)
        assert_allclose(D_sklearn, D_scipy_cdist)


@pytest.mark.parametrize("metric", BOOL_METRICS)
@pytest.mark.parametrize(
    "X_bool, Y_bool", [(X_bool, Y_bool), (X_bool_mmap, Y_bool_mmap)]
)
def test_cdist_bool_metric(metric, X_bool, Y_bool):
    D_true = cdist(X_bool, Y_bool, metric)
    dm = DistanceMetric.get_metric(metric)
    D12 = dm.pairwise(X_bool, Y_bool)
    assert_allclose(D12, D_true)


# TODO: Remove filterwarnings in 1.3 when wminkowski is removed
@pytest.mark.filterwarnings("ignore:WMinkowskiDistance:FutureWarning:sklearn")
@pytest.mark.parametrize("metric_param_grid", METRICS_DEFAULT_PARAMS)
@pytest.mark.parametrize("X, Y", [(X64, Y64), (X32, Y32), (X_mmap, Y_mmap)])
def test_pdist(metric_param_grid, X, Y):
    DistanceMetricInterface = (
        DistanceMetric if X.dtype == Y.dtype == np.float64 else DistanceMetric32
    )
    metric, param_grid = metric_param_grid
    keys = param_grid.keys()
    for vals in itertools.product(*param_grid.values()):
        kwargs = dict(zip(keys, vals))
        if metric == "mahalanobis":
            # See: https://github.com/scipy/scipy/issues/13861
            pytest.xfail("scipy#13861: pdist with 'mahalanobis' fails onmemmap data")
        elif metric == "wminkowski":
            if sp_version >= parse_version("1.8.0"):
                pytest.skip("wminkowski will be removed in SciPy 1.8.0")

            # wminkoski is deprecated in SciPy 1.6.0 and removed in 1.8.0
            ExceptionToAssert = None
            if sp_version >= parse_version("1.6.0"):
                ExceptionToAssert = DeprecationWarning
            with pytest.warns(ExceptionToAssert):
                D_true = cdist(X, X, metric, **kwargs)
        else:
            D_true = cdist(X, X, metric, **kwargs)

        dm = DistanceMetricInterface.get_metric(metric, **kwargs)
        D12 = dm.pairwise(X)
        assert_allclose(D12, D_true)


# TODO: Remove filterwarnings in 1.3 when wminkowski is removed
@pytest.mark.filterwarnings("ignore:WMinkowskiDistance:FutureWarning:sklearn")
@pytest.mark.parametrize("metric_param_grid", METRICS_DEFAULT_PARAMS)
def test_distance_metrics_dtype_consistency(metric_param_grid):
    # DistanceMetric must return similar distances for
    # both 64bit and 32bit data.
    metric, param_grid = metric_param_grid
    keys = param_grid.keys()
    for vals in itertools.product(*param_grid.values()):
        kwargs = dict(zip(keys, vals))
        dm64 = DistanceMetric.get_metric(metric, **kwargs)
        dm32 = DistanceMetric32.get_metric(metric, **kwargs)

        D64 = dm64.pairwise(X64)
        D32 = dm32.pairwise(X32)
        assert_allclose(D64, D32)

        D64 = dm64.pairwise(X64, Y64)
        D32 = dm32.pairwise(X32, Y32)
        assert_allclose(D64, D32)


@pytest.mark.parametrize("metric", BOOL_METRICS)
@pytest.mark.parametrize("X_bool", [X_bool, X_bool_mmap])
def test_pdist_bool_metrics(metric, X_bool):
    D_true = cdist(X_bool, X_bool, metric)
    dm = DistanceMetric.get_metric(metric)
    D12 = dm.pairwise(X_bool)
    # Based on https://github.com/scipy/scipy/pull/7373
    # When comparing two all-zero vectors, scipy>=1.2.0 jaccard metric
    # was changed to return 0, instead of nan.
    if metric == "jaccard" and sp_version < parse_version("1.2.0"):
        D_true[np.isnan(D_true)] = 0
    assert_allclose(D12, D_true)


# TODO: Remove filterwarnings in 1.3 when wminkowski is removed
@pytest.mark.filterwarnings("ignore:WMinkowskiDistance:FutureWarning:sklearn")
@pytest.mark.parametrize("writable_kwargs", [True, False])
@pytest.mark.parametrize("metric_param_grid", METRICS_DEFAULT_PARAMS)
@pytest.mark.parametrize("X", [X64, X32])
def test_pickle(writable_kwargs, metric_param_grid, X):
    DistanceMetricInterface = (
        DistanceMetric if X.dtype == np.float64 else DistanceMetric32
    )
    metric, param_grid = metric_param_grid
    keys = param_grid.keys()
    for vals in itertools.product(*param_grid.values()):
        if any(isinstance(val, np.ndarray) for val in vals):
            vals = copy.deepcopy(vals)
            for val in vals:
                if isinstance(val, np.ndarray):
                    val.setflags(write=writable_kwargs)
        kwargs = dict(zip(keys, vals))
        dm = DistanceMetricInterface.get_metric(metric, **kwargs)
        D1 = dm.pairwise(X)
        dm2 = pickle.loads(pickle.dumps(dm))
        D2 = dm2.pairwise(X)
        assert_allclose(D1, D2)


# TODO: Remove filterwarnings in 1.3 when wminkowski is removed
@pytest.mark.filterwarnings("ignore:WMinkowskiDistance:FutureWarning:sklearn")
@pytest.mark.parametrize("metric", BOOL_METRICS)
@pytest.mark.parametrize("X_bool", [X_bool, X_bool_mmap])
def test_pickle_bool_metrics(metric, X_bool):
    dm = DistanceMetric.get_metric(metric)
    D1 = dm.pairwise(X_bool)
    dm2 = pickle.loads(pickle.dumps(dm))
    D2 = dm2.pairwise(X_bool)
    assert_allclose(D1, D2)


def test_haversine_metric():
    def haversine_slow(x1, x2):
        return 2 * np.arcsin(
            np.sqrt(
                np.sin(0.5 * (x1[0] - x2[0])) ** 2
                + np.cos(x1[0]) * np.cos(x2[0]) * np.sin(0.5 * (x1[1] - x2[1])) ** 2
            )
        )

    X = np.random.random((10, 2))

    haversine = DistanceMetric.get_metric("haversine")

    D1 = haversine.pairwise(X)
    D2 = np.zeros_like(D1)
    for i, x1 in enumerate(X):
        for j, x2 in enumerate(X):
            D2[i, j] = haversine_slow(x1, x2)

    assert_allclose(D1, D2)
    assert_allclose(haversine.dist_to_rdist(D1), np.sin(0.5 * D2) ** 2)


def test_pyfunc_metric():
    X = np.random.random((10, 3))

    euclidean = DistanceMetric.get_metric("euclidean")
    pyfunc = DistanceMetric.get_metric("pyfunc", func=dist_func, p=2)

    # Check if both callable metric and predefined metric initialized
    # DistanceMetric object is picklable
    euclidean_pkl = pickle.loads(pickle.dumps(euclidean))
    pyfunc_pkl = pickle.loads(pickle.dumps(pyfunc))

    D1 = euclidean.pairwise(X)
    D2 = pyfunc.pairwise(X)

    D1_pkl = euclidean_pkl.pairwise(X)
    D2_pkl = pyfunc_pkl.pairwise(X)

    assert_allclose(D1, D2)
    assert_allclose(D1_pkl, D2_pkl)


def test_input_data_size():
    # Regression test for #6288
    # Previously, a metric requiring a particular input dimension would fail
    def custom_metric(x, y):
        assert x.shape[0] == 3
        return np.sum((x - y) ** 2)

    rng = check_random_state(0)
    X = rng.rand(10, 3)

    pyfunc = DistanceMetric.get_metric("pyfunc", func=custom_metric)
    eucl = DistanceMetric.get_metric("euclidean")
    assert_allclose(pyfunc.pairwise(X), eucl.pairwise(X) ** 2)


# TODO: Remove filterwarnings in 1.3 when wminkowski is removed
@pytest.mark.filterwarnings("ignore:WMinkowskiDistance:FutureWarning:sklearn")
def test_readonly_kwargs():
    # Non-regression test for:
    # https://github.com/scikit-learn/scikit-learn/issues/21685

    rng = check_random_state(0)

    weights = rng.rand(100)
    VI = rng.rand(10, 10)
    weights.setflags(write=False)
    VI.setflags(write=False)

    # Those distances metrics have to support readonly buffers.
    DistanceMetric.get_metric("seuclidean", V=weights)
    DistanceMetric.get_metric("wminkowski", p=1, w=weights)
    DistanceMetric.get_metric("mahalanobis", VI=VI)


@pytest.mark.parametrize(
    "w, err_type, err_msg",
    [
        (np.array([1, 1.5, -13]), ValueError, "w cannot contain negative weights"),
        (np.array([1, 1.5, np.nan]), ValueError, "w contains NaN"),
        (
            sp.csr_matrix([1, 1.5, 1]),
            TypeError,
            "A sparse matrix was passed, but dense data is required",
        ),
        (np.array(["a", "b", "c"]), ValueError, "could not convert string to float"),
        (np.array([]), ValueError, "a minimum of 1 is required"),
    ],
)
def test_minkowski_metric_validate_weights_values(w, err_type, err_msg):
    with pytest.raises(err_type, match=err_msg):
        DistanceMetric.get_metric("minkowski", p=3, w=w)


def test_minkowski_metric_validate_weights_size():
    w2 = rng.random_sample(d + 1)
    dm = DistanceMetric.get_metric("minkowski", p=3, w=w2)
    msg = (
        "MinkowskiDistance: the size of w must match "
        f"the number of features \\({X64.shape[1]}\\). "
        f"Currently len\\(w\\)={w2.shape[0]}."
    )
    with pytest.raises(ValueError, match=msg):
        dm.pairwise(X64, Y64)


# TODO: Remove in 1.3 when wminkowski is removed
def test_wminkowski_deprecated():
    w = rng.random_sample(d)
    msg = "WMinkowskiDistance is deprecated in version 1.1"
    with pytest.warns(FutureWarning, match=msg):
        DistanceMetric.get_metric("wminkowski", p=3, w=w)


# TODO: Remove in 1.3 when wminkowski is removed
@pytest.mark.filterwarnings("ignore:WMinkowskiDistance:FutureWarning:sklearn")
@pytest.mark.parametrize("p", [1, 1.5, 3])
def test_wminkowski_minkowski_equivalence(p):
    w = rng.random_sample(d)
    # Weights are rescaled for consistency w.r.t scipy 1.8 refactoring of 'minkowski'
    dm_wmks = DistanceMetric.get_metric("wminkowski", p=p, w=(w) ** (1 / p))
    dm_mks = DistanceMetric.get_metric("minkowski", p=p, w=w)
    D_wmks = dm_wmks.pairwise(X64, Y64)
    D_mks = dm_mks.pairwise(X64, Y64)
    assert_allclose(D_wmks, D_mks)
