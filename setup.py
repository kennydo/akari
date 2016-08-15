from setuptools import setup, find_packages

setup(
    name='akari',

    version='0.0.1',

    description='Do something with Phillips Hue lights, not sure yet',
    long_description="""
    L O N G D E S C R I P T I O N
    O
    N
    G
    D
    E
    S
    C
    R
    I
    P
    T
    I
    O
    N
    """,

    url='https://github.com/kennydo/akari',

    author='Kenny Do',
    author_email='chinesedewey@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='phillips hue python proxy',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    entry_points={
        'console_scripts': [
            'emit-light-data = akari:main',
        ],
    },
)
