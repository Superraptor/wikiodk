#!/usr/bin/env python

#
#   Clair Kronk
#   9 August 2024
#   wikibase_import.py
#

import argparse
import contextlib
import os.path
import rdflib
import requests
import sys
import warnings
import wbsync.triplestore.wikibase_adapter
import wikibase_config
import yaml

from os import getcwd, path
from pathlib import Path
from rdflib.namespace import OWL, RDF, RDFS
from urllib3.exceptions import InsecureRequestWarning

from wikibase_config import get_api_endpoint, get_sparql_endpoint
from wikidataintegrator.wdi_config import config as wikidata_integrator_config
sys.path.append('wikibase-sync/wbsync')
from wbsync.external.uri_factory import URIFactoryMock
from wbsync.triplestore import WikibaseAdapter
from wbsync.synchronization import GraphDiffSyncAlgorithm, OntologySynchronizer

old_merge_environment_settings = requests.Session.merge_environment_settings

def main():

    parser=argparse.ArgumentParser()
    parser.add_argument('--source', type=str, required=False, help='The source file name.')
    parser.add_argument('--target', type=str, required=False, help='The target file name.')
    args=parser.parse_args()

    # Read in YAML file.
    yaml_dict=yaml.safe_load(Path("project.yaml").read_text())
    print(yaml_dict)

    init_factory(yaml_dict)

    if args.source and args.target:
        update_from_file(yaml_dict, args.target, args.source)
    else:
        import_from_file(yaml_dict)

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
    if local_settings_dict:
        set_wikidata_integrator_config(adapter._local_item_engine, local_settings_dict)
    synchronizer = init_synchronizer()
    add_from_file(yaml_dict, synchronizer, adapter)

def update_from_file(yaml_dict, target_file, source_file, local_settings_dict=None):
    with open(source_file, 'r') as f:
        source_content = f.read()
    with open(target_file, 'r') as f:
        target_content = f.read()
    set_default_lang(yaml_dict)
    adapter = set_up_wikibase_adapter(yaml_dict)
    if local_settings_dict:
        set_wikidata_integrator_config(adapter._local_item_engine, local_settings_dict)
    synchronizer = init_synchronizer()
    add_content(synchronizer, adapter, target_content, source_content, yaml_dict=yaml_dict)

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
        except NotImplementedError:
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
                add_content(synchronizer, adapter, target_content, source_content=None, yaml_dict=yaml_dict)

def add_content(synchronizer, adapter, target_content, source_content=None, yaml_dict=None):
    if source_content == None:
        source_content = ""
    ops = synchronizer.synchronize(source_content, target_content)
    print(ops)
    executed=False
    if yaml_dict:
        if "wikibase_public_host" in yaml_dict["wikibase"]:
            if yaml_dict["wikibase"]["wikibase_public_host"] == 'wikibase.example.com':
                with no_ssl_verification():
                    execute_synchronization(source_content, target_content, synchronizer, adapter)
                    executed=True
    if executed==False:
        execute_synchronization(source_content, target_content, synchronizer, adapter)

def set_up_wikibase_adapter(yaml_dict):
    mediawiki_api_url=get_api_endpoint(yaml_dict)
    sparql_endpoint_url=get_sparql_endpoint(yaml_dict)
    # 'http://localhost:8834/proxy/wdqs/bigdata/namespace/wdq/sparql' # TODO: Pull value from somewhere?
    USERNAME=wikibase_config.get_mw_admin_name(yaml_dict)
    PASSWORD=wikibase_config.get_mw_admin_password(yaml_dict)
    # Note: WikibaseAdapter (and cascading packages) will not trust a self-signed certificate;
    # this section will bypass that restriction, but it opens up your machine to man-in-the-
    # middle attacks. Use with EXTREME caution.
    if mediawiki_api_url == 'http://wikibase.example.com/w/api.php':
        with no_ssl_verification():
            adapter = WikibaseAdapter(mediawiki_api_url, sparql_endpoint_url, USERNAME, PASSWORD)
    else:
        adapter = WikibaseAdapter(mediawiki_api_url, sparql_endpoint_url, USERNAME, PASSWORD)
    return adapter

def init_synchronizer():
    algorithm = GraphDiffSyncAlgorithm()
    synchronizer = OntologySynchronizer(algorithm)
    return synchronizer

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
def set_wikidata_integrator_config(item_engine, local_settings_dict):
    # See: https://github.com/SuLab/WikidataIntegrator/blob/505d58d7c1d530c79f00bb1ad6b4500fd303efc4/wikidataintegrator/wdi_config.py#L27
    if "wgWBQualityConstraintsPropertyConstraintId" in local_settings_dict:
        item_engine.property_constraint_pid = local_settings_dict["wgWBQualityConstraintsPropertyConstraintId"]
    if "wgWBQualityConstraintsDistinctValuesConstraintId" in local_settings_dict:
        item_engine.distinct_values_constraint_qid = local_settings_dict["wgWBQualityConstraintsDistinctValuesConstraintId"]

def init_factory(yaml_dict):
    factory = URIFactoryMock()
    factory.reset_factory()

# Adapted from: https://stackoverflow.com/questions/15445981/how-do-i-disable-the-security-certificate-check-in-python-requests
@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()
    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))
        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False
        return settings
    requests.Session.merge_environment_settings = merge_environment_settings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings
        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass

if __name__ == '__main__':
    main()