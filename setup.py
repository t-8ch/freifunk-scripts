from setuptools import setup

setup(
    name='freifunk-scripts',
    version='0.1.0',
    author='Thomas Weißschuh',
    author_email='thomas@t-8ch.de',
    url='https://github.com/t-8ch/freifunk-scripts',
    package_dir={'freifunk': ''},
    packages=['freifunk'],
    license='MIT',
    entry_points={
        'console_scripts': [
            'freifunk-nodes2zone = freifunk.nodes2zone:main',
            'freifunk-generate-dashboard = freifunk.generate_dashboard:main',
        ],
    },
)
