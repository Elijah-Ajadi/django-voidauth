import setuptools

setuptools.setup(
    name="django-voidauth",
    version="0.1.1",
    author="Ajadi Ademola Elijah",
    author_email="ajadiademola926@gmail.com",
    description="A zero-knowledge authentication system for Django using Ed25519.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ELijah-Ajadi/django-voidauth",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Django",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Django>=3.2",
        "cryptography>=3.4",
        "django-ratelimit>=4.0.0",
        "webauthn>=2.0.0",
    ],
)
