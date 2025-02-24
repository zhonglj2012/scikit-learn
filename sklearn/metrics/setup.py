import os
import jax.numpy as np
import numpy as onp
np.random = onp.random
np.matrix = onp.matrix

from numpy.distutils.misc_util import Configuration

from sklearn._build_utils import gen_from_templates


def configuration(parent_package="", top_path=None):
    config = Configuration("metrics", parent_package, top_path)

    libraries = []
    if os.name == "posix":
        libraries.append("m")

    config.add_subpackage("_plot")
    config.add_subpackage("_plot.tests")
    config.add_subpackage("cluster")

    config.add_extension(
        "_pairwise_fast", sources=["_pairwise_fast.pyx"], libraries=libraries
    )

    templates = [
        "sklearn/metrics/_dist_metrics.pyx.tp",
        "sklearn/metrics/_dist_metrics.pxd.tp",
    ]

    gen_from_templates(templates)

    config.add_extension(
        "_dist_metrics",
        sources=["_dist_metrics.pyx"],
        include_dirs=[np.get_include(), os.path.join(np.get_include(), "numpy")],
        libraries=libraries,
    )

    config.add_extension(
        "_pairwise_distances_reduction",
        sources=["_pairwise_distances_reduction.pyx"],
        include_dirs=[np.get_include(), os.path.join(np.get_include(), "numpy")],
        language="c++",
        libraries=libraries,
        extra_compile_args=["-std=c++11"],
    )

    config.add_subpackage("tests")

    return config


if __name__ == "__main__":
    from numpy.distutils.core import setup

    setup(**configuration().todict())
