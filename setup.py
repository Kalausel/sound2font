from setuptools import setup, find_packages

setup(
    name="sound2font",  # Change to your module's name
    version="0.1.0.dev1",
    author="Klaus Kiendlhofer",
    author_email="89465202+Kalausel@users.noreply.github.com",
    description="Enter speech. Expect a vector file with text.",
    #long_description=open("README.md").read(),
    #long_description_content_type="text/markdown",
    #url="https://github.com/Kalausel/sound2font",  # Change to your repo
    packages=find_packages(where='src'),
    package_dir={"": "src"},
    install_requires=[
        "vosk",
        "pyaudio",
        "wave",
        "matplotlib",
        #"pynput",
        "recasepunc @ git+https://github.com/Kalausel/recasepunc.git"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)

