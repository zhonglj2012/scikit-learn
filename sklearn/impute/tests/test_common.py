import pytest

import jax.numpy as np
import numpy as onp
np.random = onp.random
np.matrix = onp.matrix
from scipy import sparse

from sklearn.utils._testing import assert_allclose
from sklearn.utils._testing import assert_allclose_dense_sparse
from sklearn.utils._testing import assert_array_equal

from sklearn.experimental import enable_iterative_imputer  # noqa

from sklearn.impute import IterativeImputer
from sklearn.impute import KNNImputer
from sklearn.impute import SimpleImputer


IMPUTERS = [IterativeImputer(tol=0.1), KNNImputer(), SimpleImputer()]
SPARSE_IMPUTERS = [SimpleImputer()]


# ConvergenceWarning will be raised by the IterativeImputer
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
@pytest.mark.parametrize("imputer", IMPUTERS)
def test_imputation_missing_value_in_test_array(imputer):
    # [Non Regression Test for issue #13968] Missing value in test set should
    # not throw an error and return a finite dataset
    train = [[1], [2]]
    test = [[3], [np.nan]]
    imputer.set_params(add_indicator=True)
    imputer.fit(train).transform(test)


# ConvergenceWarning will be raised by the IterativeImputer
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
@pytest.mark.parametrize("marker", [np.nan, -1, 0])
@pytest.mark.parametrize("imputer", IMPUTERS)
def test_imputers_add_indicator(marker, imputer):
    X = np.array(
        [
            [marker, 1, 5, marker, 1],
            [2, marker, 1, marker, 2],
            [6, 3, marker, marker, 3],
            [1, 2, 9, marker, 4],
        ]
    )
    X_true_indicator = np.array(
        [
            [1.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    imputer.set_params(missing_values=marker, add_indicator=True)

    X_trans = imputer.fit_transform(X)
    assert_allclose(X_trans[:, -4:], X_true_indicator)
    assert_array_equal(imputer.indicator_.features_, np.array([0, 1, 2, 3]))

    imputer.set_params(add_indicator=False)
    X_trans_no_indicator = imputer.fit_transform(X)
    assert_allclose(X_trans[:, :-4], X_trans_no_indicator)


# ConvergenceWarning will be raised by the IterativeImputer
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
@pytest.mark.parametrize("marker", [np.nan, -1])
@pytest.mark.parametrize("imputer", SPARSE_IMPUTERS)
def test_imputers_add_indicator_sparse(imputer, marker):
    X = sparse.csr_matrix(
        [
            [marker, 1, 5, marker, 1],
            [2, marker, 1, marker, 2],
            [6, 3, marker, marker, 3],
            [1, 2, 9, marker, 4],
        ]
    )
    X_true_indicator = sparse.csr_matrix(
        [
            [1.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    imputer.set_params(missing_values=marker, add_indicator=True)

    X_trans = imputer.fit_transform(X)
    assert_allclose_dense_sparse(X_trans[:, -4:], X_true_indicator)
    assert_array_equal(imputer.indicator_.features_, np.array([0, 1, 2, 3]))

    imputer.set_params(add_indicator=False)
    X_trans_no_indicator = imputer.fit_transform(X)
    assert_allclose_dense_sparse(X_trans[:, :-4], X_trans_no_indicator)


# ConvergenceWarning will be raised by the IterativeImputer
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
@pytest.mark.parametrize("imputer", IMPUTERS)
@pytest.mark.parametrize("add_indicator", [True, False])
def test_imputers_pandas_na_integer_array_support(imputer, add_indicator):
    # Test pandas IntegerArray with pd.NA
    pd = pytest.importorskip("pandas")
    marker = np.nan
    imputer = imputer.set_params(add_indicator=add_indicator, missing_values=marker)

    X = np.array(
        [
            [marker, 1, 5, marker, 1],
            [2, marker, 1, marker, 2],
            [6, 3, marker, marker, 3],
            [1, 2, 9, marker, 4],
        ]
    )
    # fit on numpy array
    X_trans_expected = imputer.fit_transform(X)

    # Creates dataframe with IntegerArrays with pd.NA
    X_df = pd.DataFrame(X, dtype="Int16", columns=["a", "b", "c", "d", "e"])

    # fit on pandas dataframe with IntegerArrays
    X_trans = imputer.fit_transform(X_df)

    assert_allclose(X_trans_expected, X_trans)


@pytest.mark.parametrize("imputer", IMPUTERS, ids=lambda x: x.__class__.__name__)
@pytest.mark.parametrize("add_indicator", [True, False])
def test_imputers_feature_names_out_pandas(imputer, add_indicator):
    """Check feature names out for imputers."""
    pd = pytest.importorskip("pandas")
    marker = np.nan
    imputer = imputer.set_params(add_indicator=add_indicator, missing_values=marker)

    X = np.array(
        [
            [marker, 1, 5, 3, marker, 1],
            [2, marker, 1, 4, marker, 2],
            [6, 3, 7, marker, marker, 3],
            [1, 2, 9, 8, marker, 4],
        ]
    )
    X_df = pd.DataFrame(X, columns=["a", "b", "c", "d", "e", "f"])
    imputer.fit(X_df)

    names = imputer.get_feature_names_out()

    if add_indicator:
        expected_names = [
            "a",
            "b",
            "c",
            "d",
            "f",
            "missingindicator_a",
            "missingindicator_b",
            "missingindicator_d",
            "missingindicator_e",
        ]
        assert_array_equal(expected_names, names)
    else:
        expected_names = ["a", "b", "c", "d", "f"]
        assert_array_equal(expected_names, names)
