from time import time
import argparse
import jax.numpy as np
import numpy as onp
np.random = onp.random
np.matrix = onp.matrix

from sklearn.dummy import DummyClassifier

from sklearn.datasets import fetch_20newsgroups_vectorized
from sklearn.metrics import accuracy_score
from sklearn.utils.validation import check_array

from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

ESTIMATORS = {
    "dummy": DummyClassifier(),
    "random_forest": RandomForestClassifier(max_features="sqrt", min_samples_split=10),
    "extra_trees": ExtraTreesClassifier(max_features="sqrt", min_samples_split=10),
    "logistic_regression": LogisticRegression(),
    "naive_bayes": MultinomialNB(),
    "adaboost": AdaBoostClassifier(n_estimators=10),
}


###############################################################################
# Data

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e", "--estimators", nargs="+", required=True, choices=ESTIMATORS
    )
    args = vars(parser.parse_args())

    data_train = fetch_20newsgroups_vectorized(subset="train")
    data_test = fetch_20newsgroups_vectorized(subset="test")
    X_train = check_array(data_train.data, dtype=np.float32, accept_sparse="csc")
    X_test = check_array(data_test.data, dtype=np.float32, accept_sparse="csr")
    y_train = data_train.target
    y_test = data_test.target

    print("20 newsgroups")
    print("=============")
    print(f"X_train.shape = {X_train.shape}")
    print(f"X_train.format = {X_train.format}")
    print(f"X_train.dtype = {X_train.dtype}")
    print(f"X_train density = {X_train.nnz / np.product(X_train.shape)}")
    print(f"y_train {y_train.shape}")
    print(f"X_test {X_test.shape}")
    print(f"X_test.format = {X_test.format}")
    print(f"X_test.dtype = {X_test.dtype}")
    print(f"y_test {y_test.shape}")
    print()
    print("Classifier Training")
    print("===================")
    accuracy, train_time, test_time = {}, {}, {}
    for name in sorted(args["estimators"]):
        clf = ESTIMATORS[name]
        try:
            clf.set_params(random_state=0)
        except (TypeError, ValueError):
            pass

        print("Training %s ... " % name, end="")
        t0 = time()
        clf.fit(X_train, y_train)
        train_time[name] = time() - t0
        t0 = time()
        y_pred = clf.predict(X_test)
        test_time[name] = time() - t0
        accuracy[name] = accuracy_score(y_test, y_pred)
        print("done")

    print()
    print("Classification performance:")
    print("===========================")
    print()
    print("%s %s %s %s" % ("Classifier  ", "train-time", "test-time", "Accuracy"))
    print("-" * 44)
    for name in sorted(accuracy, key=accuracy.get):
        print(
            "%s %s %s %s"
            % (
                name.ljust(16),
                ("%.4fs" % train_time[name]).center(10),
                ("%.4fs" % test_time[name]).center(10),
                ("%.4f" % accuracy[name]).center(10),
            )
        )

    print()
