# wikiODK

## Setup

Please note that this is a proof-of-concept and has only been tested under very specific circumstances. Currently it has been successfully run on a Microsoft Windows 11 OS (v10.0.22631) with Docker version 26.1.1 (build 4cf5afa) and Anaconda version 24.5.0. Please make sure Docker and Anaconda are installed correctly and functional before running the following steps. If you run into issues with package installs via `pip`, it is more than likely that you've accidentally installed packages to the `base` Anaconda environment (trust me, this has happened to me as well). Unfortunately the only way I know how to debug this is to uninstall and reinstall Anaconda from scratch (luckily this only took me about 10 minutes, but you should note that you will lose all your existing environments if you do this!).

Be patient when running `seed-via-docker.bat`. It took my machine anywhere from 10-15 minutes to run.

Please note that `hhear_properties.ttl` and `study-design-data.ttl` are sample files and are not meant to serve as full ontologies. As well, since this is a proof-of-concept, the upload feature has only be tested for the initial upload; another upload may not function as intended. There is no guarantee that other files will function or that changes to the `project.yaml` file will work as intended as they have not been tested. Make changes at your own risk!

Next steps are to get additional extensions fully functional; however, it should be noted that additional extensions are NOT currently supported (as of 14 August 2024) by the `wikibase-release-pipeline`. It is equally likely that I will implement a stopgap or that the developers of the `wikibase-release-pipeline` will implement one.

### Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- [Anaconda](https://www.anaconda.com/download)

### Installation

#### Wikibase Creation and Import

1. Create an Anaconda environment as follows: `conda create -n {ENVIRONMENT_NAME} python=3.7.16`.
2. Activate the environment: `conda activate {ENVIRONMENT_NAME}`.
3. Run `.\seed-via-docker.bat -C project.yaml` in this directory.
4. Open a web browser. Go to `localhost:8880`. Note that the browser will say the instance is unsafe but you can proceed without issue (see [here](https://github.com/wmde/wikibase-release-pipeline/tree/main/deploy#can-i-host-wikibase-suite-locally) for more details as to why this happens).

#### Wikibase XML Download and Upload

Note that this section is experimental and may change significantly in the near future.

1. Run the scripts above to create the Wikibase.
2. Create an Anaconda environment as follows: `conda create -n {ENVIRONMENT_NAME} python=3.11.9`.
3. Activate the environment: `conda activate {ENVIRONMENT_NAME}`.
4. Run `pip install PyYAML`.
5. Run `pip install internetarchive`.
6. Run `pip install zstandard`.
7. Run `python wikibase_dump.py -install` to install WikiTeams3. Test the install by seeing the output of `wikiteam3dumpgenerator` on the command-line.
8. To create a dump, run `python wikibase_dump.py -create`. To upload, run `python wikibase_dump.py -upload`; to download run `python wikibase_dump.py -download`. Note that, because extensions are not currently functional, that it is necessary to exclude schema and lexeme namespaces for this to function. 