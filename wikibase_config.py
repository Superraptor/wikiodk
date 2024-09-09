#!/usr/bin/env python

#
#   Clair Kronk
#   13 August 2024
#   wikibase_config.py
#

import ast
import json
import os
import subprocess
import yaml

from pathlib import Path

def main():
    #local_settings_dict = get_local_settings()

    # Read in YAML file.
    yaml_dict=yaml.safe_load(Path("project.yaml").read_text())
    print(yaml_dict)

    get_sparql_endpoint(yaml_dict)

def get_local_settings():
    local_settings_path=os.path.join(os.environ['TEMP'], "LocalSettings.php")
    subprocess.run("docker cp wbs-deploy-wikibase-1:/var/www/html/LocalSettings.php %s" % local_settings_path, shell=True)
    local_settings_lines = []
    with open(local_settings_path, 'r') as f:
        local_settings_lines = f.readlines()
    local_settings_dict = {}
    for line in local_settings_lines:
        if (' = ' in line) and (not line.startswith('#')):
            if (('[' in line and ']' not in line) or ('array(' in line and ')' not in line)):
                pass # Not yet implemented.
            else:
                stripped_line = line.strip()
                if '; #' in stripped_line:
                    stripped_line = stripped_line.split(' #')[0]
                stripped_line = stripped_line[1:-1]
                split_line = stripped_line.split(' = ')
                var_name = split_line[0]
                if '$' in split_line[1]:
                    if split_line[1] in local_settings_dict:
                        var_value = local_settings_dict[split_line[0]]
                else:
                    if split_line[1] == "true" or split_line[1] == "false":
                        var_value = bool(split_line[1])
                    elif (split_line[1] == "") or (split_line[1] == '') or (split_line[1] == '""') or (split_line[1] == "''"):
                        var_value = None
                    elif check_integer(split_line[1]):
                        var_value = int(split_line[1])
                    elif ('[' in split_line[1]) and (']' in split_line[1]):
                        var_value = ast.literal_eval(split_line[1])
                    elif ("'" in split_line[1]) or ('"' in split_line[1]):
                        var_value = ast.literal_eval(split_line[1])
                    else:
                        pass
                local_settings_dict[var_name] = var_value
    return local_settings_dict

def get_mw_admin_name(yaml_dict):
    if 'mw_admin_name' in yaml_dict['wikibase']:
        return yaml_dict['wikibase']['mw_admin_name']
    else:
        with open("./target/"+yaml_dict['repo']+"/src/scripts/wikibase-release-pipeline/deploy/.env") as env_file:
            for line in env_file:
                if line.startswith("MW_ADMIN_NAME="):
                    return (line.split("=")[1]).strip()

def get_mw_admin_password(yaml_dict):
    if 'mw_admin_password' in yaml_dict['wikibase']:
        PASSWORD = yaml_dict['wikibase']['mw_admin_password']
    else:
        with open("./target/"+yaml_dict['repo']+"/src/scripts/wikibase-release-pipeline/deploy/.env") as env_file:
            for line in env_file:
                if line.startswith("MW_ADMIN_PASS="):
                    return (line.split("=")[1]).strip()

def get_api_endpoint(yaml_dict):
    mediawiki_api_url=None
    if 'wikibase_public_host' in yaml_dict['wikibase']:
        docker_yaml_dict=yaml.safe_load(Path("./target/"+yaml_dict['repo']+"/src/scripts/wikibase-release-pipeline/deploy/docker-compose.yml").read_text())
        port_no=None
        if "ports" in docker_yaml_dict["services"]["wikibase"]:
            port_no=docker_yaml_dict["services"]["wikibase"]["ports"][0]
            if ':' in port_no:
                port_no=port_no.split(':')[0]
        try:
            mediawiki_api_url=yaml_dict['wikibase']['wikibase_public_host'] + ':' + port_no + "/w/api.php"
            if mediawiki_api_url.startswith('localhost'):
                mediawiki_api_url="http://"+mediawiki_api_url
            else:
                mediawiki_api_url="http://"+yaml_dict['wikibase']['wikibase_public_host']+"/w/api.php"  
        except TypeError:
            mediawiki_api_url="http://"+yaml_dict['wikibase']['wikibase_public_host']+"/w/api.php"
        except AttributeError:
            mediawiki_api_url="http://"+yaml_dict['wikibase']['wikibase_public_host']+"/w/api.php"
    elif 'external_host' in yaml_dict['wikibase']:
        mediawiki_api_url=str(yaml_dict['wikibase']['external_host'])+"/w/api.php"
    else:
        mediawiki_api_url='http://localhost:8880/w/api.php'
    return mediawiki_api_url

def get_sparql_endpoint(yaml_dict):
    sparql_endpoint_url=None
    if 'wikibase_public_host' in yaml_dict['wikibase']:
        with open('./target/'+yaml_dict['repo']+'/src/scripts/wikibase-release-pipeline/build/WDQS-frontend/custom-config.json', 'r') as f:
            json_data=json.load(f)
            sparql_endpoint=json_data['api']['sparql']['uri']
        docker_yaml_dict=yaml.safe_load(Path("./target/"+yaml_dict['repo']+"/src/scripts/wikibase-release-pipeline/deploy/docker-compose.yml").read_text())
        port_no=None
        if "ports" in docker_yaml_dict["services"]["wdqs-frontend"]:
            port_no=docker_yaml_dict["services"]["wdqs-frontend"]["ports"][0]
            if ':' in port_no:
                port_no=port_no.split(':')[0]
        sparql_endpoint_url=yaml_dict['wikibase']['wikibase_public_host'] + ':' + port_no + sparql_endpoint
        if sparql_endpoint_url.startswith('localhost'):
            sparql_endpoint_url="http://"+sparql_endpoint_url
        else:
            sparql_endpoint_url="http://"+sparql_endpoint_url
    elif 'external_host' in yaml_dict['wikibase']:
        sparql_endpoint_url=yaml_dict['wikibase']['external_host'] + '/query/sparql'
    else:
        sparql_endpoint_url='http://localhost:8834/proxy/wdqs/bigdata/namespace/wdq/sparql'
    return sparql_endpoint_url

# TODO: Only works when initializing, will not overwrite.
def set_string_limits(yaml_dict):
    local_settings_dict=get_local_settings()
    local_settings_path=os.path.join(os.environ['TEMP'], "LocalSettings.php")
    
    if "string_limits" in yaml_dict["wikibase"]:
        if "wgWBRepoSettings['string-limits']['VT:string']['length']" in local_settings_dict:
            pass
        else:
            if "string" in yaml_dict["wikibase"]["string_limits"]:
                with open(local_settings_path, 'a') as f:
                    f.write("$wgWBRepoSettings['string-limits']['VT:string']['length'] = "+str(yaml_dict["wikibase"]["string_limits"]["string"]))
        
        if "wgWBRepoSettings['string-limits']['VT:monolingualtext']['length']" in local_settings_dict:
            pass
        else:
            if "monolingual_text" in yaml_dict["wikibase"]["string_limits"]:
                with open(local_settings_path, 'a') as f:
                    f.write("$wgWBRepoSettings['string-limits']['VT:monolingualtext']['length'] = "+str(yaml_dict["wikibase"]["string_limits"]["monolingual_text"]))
        
        if "wgWBRepoSettings['string-limits']['multilang']['length']" in local_settings_dict:
            pass
        else:
            if "multilang" in yaml_dict["wikibase"]["string_limits"]:
                with open(local_settings_path, 'a') as f:
                    f.write("$wgWBRepoSettings['string-limits']['multilang']['length'] = "+str(yaml_dict["wikibase"]["string_limits"]["multilang"]))
            
def check_integer(s):
    if s[0] in ["+", "-"]:
        if s[1:].isdigit():
            return True
        return False

    if s.isdigit():
        return True
    return False

if __name__ == '__main__':
    main()