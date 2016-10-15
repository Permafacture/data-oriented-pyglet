from setuptools import setup

setup(
    name = "Numpy-ECS",
    version = "0.01",
    author = "Elliot Hallmark",
    author_email = "permafacture@gmail.com",
    description = ("An Entity Component System framework built on numpy arrays"),
    license = "GPLv2",
    keywords = "data oriented programming, ECS",
    url = "https://github.com/Permafacture/data-oriented-pyglet",
    install_requires = ['numpy','pyglet'],
    packages=['numpy_ecs',],
    classifiers=["Programming Language :: Python :: 3"]
)
