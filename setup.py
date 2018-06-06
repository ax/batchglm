from setuptools import setup, find_packages

setup(
    name='rsa',
    packages=find_packages(),
    install_requires=[
        'tensorflow',
        'numpy',
        'pandas',
        'xarray',
        'dask',
        # HDF5 / NetCDF support
        'h5netcdf',
        'toolz',
        # design matrix generation
        'patsy'
    ],
    extras_require={
        'plotting': [
            "matplotlib",
            "plotnine",
            "plotly",
            # ECDF, etc.
            "mlxtend",
            # tSNE, etc.
            "scanpy",
            "MulticoreTSNE"
        ]
    }

)
