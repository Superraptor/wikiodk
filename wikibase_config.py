#!/usr/bin/env python

#
#   Clair Kronk
#   13 August 2024
#   wikibase_config.py
#

import ast
import os
import subprocess

def main():
    local_settings_dict = get_local_settings()

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