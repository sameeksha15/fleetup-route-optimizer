"""Fleet route optimization engine.

Pure domain logic: package generation, clustering, truck allocation,
travel-time providers, and multi-trip route planning. No web-framework
or database dependencies.
"""

import os

# Cap native BLAS/OpenMP threads before numpy/scikit-learn load their runtimes.
# The optimization workload is many small matrices, where oversubscribed thread
# pools waste memory and have crashed OpenBLAS on Windows. Callers can override.
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "2")
