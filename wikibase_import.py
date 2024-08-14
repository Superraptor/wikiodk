#!/usr/bin/env python

#
#   Clair Kronk
#   9 August 2024
#   wikibase_import.py
#

import os.path
import rdflib
import subprocess
import sys
import wbsync.triplestore.wikibase_adapter
import wikibase_config
import yaml

from os import getcwd, path
from pathlib import Path
from rdflib.namespace import OWL, RDF, RDFS

from wbsync.triplestore import WikibaseAdapter
from wbsync.synchronization import GraphDiffSyncAlgorithm, OntologySynchronizer
from wikidataintegrator.wdi_config import config as wikidata_integrator_config

def main():
    
    # Read in YAML file.
    yaml_dict=yaml.safe_load(Path("project.yaml").read_text())
    print(yaml_dict)

    init_factory(yaml_dict)
    import_from_file(yaml_dict)
    # Parse files
    #if "import" in yaml_dict["wikibase"]:
    #    for file_path in yaml_dict["wikibase"]["import"]:
    #        g = parse_file(file_path)

    #install_hercules_sync(yaml_dict)
    #install_wikibase_sync(yaml_dict)

    # Set up module paths for imports.
    #module_path = os.path.abspath("./target/"+yaml_dict['repo']+"/src/scripts")
    #hercules_sync_path = os.path.abspath("./target/"+yaml_dict['repo']+"/src/scripts/hercules-sync")
    #sys.path.append(module_path)
    #sys.path.append(hercules_sync_path)

def parse_file(file_path):
    if os.path.isfile(file_path):
        g = rdflib.Graph()
        g.parse(file_path)
        return g
    else:
        exit()

def return_properties(g):
    properties = []
    for s, p, o in g.triples((None,  RDF.type, None)):
        if o == OWL.DatatypeProperty:
            properties.append(s)
        elif o == OWL.ObjectProperty:
            properties.append(s)
        elif o == OWL.AnnotationProperty:
            properties.append(s)
        elif o == RDF.Property:
            properties.append(s)
        else:
            pass
    properties = list(set(properties))
    return properties

def return_classes(g):
    classes = []
    for s, p, o in g.triples((None,  RDF.type, None)):
        if ((o == OWL.DatatypeProperty) or 
            (o == OWL.ObjectProperty) or 
            (o == OWL.AnnotationProperty) or 
            (o == RDF.Property)):
            pass
        elif o == RDFS.Class:
            classes.append(s)
        else:
            classes.append(o)
    classes = list(set(classes))
    return classes

def return_instances(g):
    instances = []
    for s, p, o in g.triples((None,  RDF.type, None)):
        if ((o == OWL.DatatypeProperty) or 
            (o == OWL.ObjectProperty) or 
            (o == OWL.AnnotationProperty) or 
            (o == RDF.Property) or 
            (o == RDFS.Class)):
            pass
        else:
            instances.append(s)
    instances = list(set(instances))
    return instances

def import_from_file(yaml_dict, local_settings_dict=None):
    set_default_lang(yaml_dict)
    adapter = set_up_wikibase_adapter(yaml_dict)
    synchronizer = init_synchronizer()
    if local_settings_dict:
        set_wikidata_integrator_config(local_settings_dict)
    add_from_file(yaml_dict, synchronizer, adapter)

def execute_synchronization(source_content, target_content, synchronizer, adapter):
    ops = synchronizer.synchronize(source_content, target_content)
    for op in ops:
        print(op)
        try:
            res = op.execute(adapter)
            if not res.successful:
                print(f"Error synchronizing triple: {res.message}")
        except ValueError:
            pass # TODO: Come back and fix this!!!

# TODO: Fix so can take a single file and to deal with target_content/source_content
    # Currently only functions from blank Wikibase to file; need to make able to
    # function with changes to file.
    #
    # Also need to add an export feature.
def add_from_file(yaml_dict, synchronizer, adapter):
    if "import" in yaml_dict["wikibase"]:
        for file_path in yaml_dict["wikibase"]["import"]:
            target_content = None
            with open(file_path, 'r') as f:
                target_content = f.read()
            if target_content:
                print(target_content)
                add_content(synchronizer, adapter, target_content, source_content=None)

def add_content(synchronizer, adapter, target_content, source_content=None):
    if source_content == None:
        source_content = ""
    ops = synchronizer.synchronize(source_content, target_content)
    print(ops)
    execute_synchronization(source_content, target_content, synchronizer, adapter)

def set_up_wikibase_adapter(yaml_dict):
    mediawiki_api_url='http://localhost:8880/w/api.php' # TODO: Pull value from somewhere?
    sparql_endpoint_url='http://localhost:8834/proxy/wdqs/bigdata/namespace/wdq/sparql' # TODO: Pull value from somewhere?
    USERNAME=wikibase_config.get_mw_admin_name(yaml_dict)
    PASSWORD=wikibase_config.get_mw_admin_password(yaml_dict)
    adapter = WikibaseAdapter(mediawiki_api_url, sparql_endpoint_url, USERNAME, PASSWORD)
    return adapter

def init_synchronizer():
    algorithm = GraphDiffSyncAlgorithm()
    synchronizer = OntologySynchronizer(algorithm)
    return synchronizer

def install_hercules_sync(yaml_dict):
    pass
    # Check if hercules-sync has been downloaded; if not begin downloading.
    #hercules_sync_dir="./target/"+yaml_dict['repo']+"/src/scripts/hercules-sync"
    #if not path.exists(hercules_sync_dir):
    #    subprocess.run("git clone https://github.com/weso/hercules-sync "+hercules_sync_dir, shell=True) 

    # Install hercules-sync.
    #chdir(hercules_sync_dir)
    #subprocess.run("pip install -r requirements.txt", shell=True)
    #chdir(wd)

def install_wikibase_sync(yaml_dict):
    pass
    # Check if wikibase-sync has been downloaded; if not begin downloading.
    #wikibase_sync_dir="./target/"+yaml_dict['repo']+"/src/scripts/wikibase-sync"
    #if not path.exists(wikibase_sync_dir):
    #    subprocess.run("git clone https://github.com/weso/wikibase-sync "+wikibase_sync_dir, shell=True) 
        
    # Install wikibase-sync. # May not be necessary?
    #chdir(wikibase_sync_dir)
    #subprocess.run("python setup.py install", shell=True)
    #chdir(wd)

def set_default_lang(yaml_dict, local_settings_dict=None, use_lang=None):
    if "adapter" in yaml_dict["wikibase"]:
        if "default_lang" in yaml_dict["wikibase"]["adapter"]:
            wbsync.triplestore.wikibase_adapter.DEFAULT_LANG = yaml_dict["wikibase"]["adapter"]["default_lang"]
    elif use_lang:
        wbsync.triplestore.wikibase_adapter.DEFAULT_LANG = use_lang
    else: # Use wgLanguageCode from LocalSettings.php.
        if local_settings_dict:
            wbsync.triplestore.wikibase_adapter.DEFAULT_LANG = local_settings_dict["wgLanguageCode"]
        else:
            local_settings_dict = wikibase_config.get_local_settings()
            wbsync.triplestore.wikibase_adapter.DEFAULT_LANG = local_settings_dict["wgLanguageCode"]

# TODO: This doesn't seem to function?
def set_wikidata_integrator_config(local_settings_dict):
    # See: https://github.com/SuLab/WikidataIntegrator/blob/505d58d7c1d530c79f00bb1ad6b4500fd303efc4/wikidataintegrator/wdi_config.py#L27
    wikidata_integrator_config["PROPERTY_CONSTRAINT_PID"] = local_settings_dict["wgWBQualityConstraintsPropertyConstraintId"]
    wikidata_integrator_config["DISTINCT_VALUES_CONSTRAINT_QID"] = local_settings_dict["wgWBQualityConstraintsDistinctValuesConstraintId"]
    #print(wikidata_integrator_config)

def init_factory(yaml_dict):
    #module_path = os.path.abspath("./target/"+yaml_dict['repo']+"/src/scripts")
    #hercules_sync_path = os.path.abspath("./target/"+yaml_dict['repo']+"/src/scripts/hercules-sync")
    #sys.path.append(module_path)
    #sys.path.append(hercules_sync_path)

    from wbsync.external.uri_factory import URIFactoryMock

    factory = URIFactoryMock()
    factory.reset_factory()

if __name__ == '__main__':
    main()