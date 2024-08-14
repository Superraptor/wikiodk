::BATCH file to seed new ontology repo via docker
docker run -v "%userprofile%/.gitconfig:/root/.gitconfig" -v "%cd%:/work" -w /work --rm -ti obolibrary/odkfull /tools/odk.py seed %*

::Upgrade pip.
pip install --upgrade pip

::Install setuptools (to avoid breaking use_2to3 with keepalive; required, re: https://stackoverflow.com/questions/69100275/error-while-downloading-the-requirements-using-pip-install-setup-command-use-2).
pip install setuptools~=47.1.0

::Install wbsync.
pip install wbsync

::Install wikidataintegrator; this version is required, see: https://github.com/weso/wikibase-sync/blob/da17aa1e691cde4c1c66bd87bc3ca3d7b899c261/requirements.txt
pip install wikidataintegrator==0.6.0

::Install PyYAML.
pip install PyYAML

::Install pandas. This version is required, see: https://github.com/weso/wikibase-sync/blob/da17aa1e691cde4c1c66bd87bc3ca3d7b899c261/requirements.txt
pip install pandas==1.0.1

::Install rdflib. The "no-deps" is necessary because of wbsync. This version is necessary (despite "conflicting" with wbsync) due to: https://github.com/RDFLib/rdflib/issues/1488
pip install rdflib==6.0.2 --no-deps

::Install tqdm. This version is required, see:  https://github.com/weso/wikibase-sync/blob/da17aa1e691cde4c1c66bd87bc3ca3d7b899c261/requirements.txt
pip install tqdm==4.42.1

::Run Wikibase script.
python wikibase.py