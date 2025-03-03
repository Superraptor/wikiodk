::BATCH file to seed new ontology repo via docker
docker run -v "%userprofile%/.gitconfig" -v "%cd%:/work" -w /work --rm -ti obolibrary/odkfull /tools/odk.py seed %*

::Upgrade pip.
pip install --upgrade pip

::Install wbsync.
::pip install wbsync
pip install -r requirements.txt
::This has to be done manually in the wikibase-sync directory
::python wikibase-sync\setup.py install

::Run Wikibase script.
python wikibase.py