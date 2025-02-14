from setuptools import setup, find_packages
 
with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in website_visitors/__init__.py
from website_visitors import __version__ as version

setup(
	name="website_visitors",
	version=version,
	description="This app tracks live visitors on website",
	author="OneHash",
	author_email="support@onehash.ai",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
