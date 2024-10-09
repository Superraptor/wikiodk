#!/usr/bin/env python

#
#   Clair Kronk
#   10 August 2024
#   wikibase_extensions.py
#

import os
import re
import requests
import subprocess
import yaml

from os import getcwd, path, chdir
from pathlib import Path

def main():

    # Read in YAML file.
    yaml_dict=yaml.safe_load(Path("project.yaml").read_text())
    print(yaml_dict)
    repo=yaml_dict['repo']
    wikibase_release_pipeline_dir="./target/"+str(repo)+"/src/scripts/wikibase-release-pipeline"
    deploy_dir=wikibase_release_pipeline_dir+"/deploy"

    modify_build_sh(yaml_dict)

def modify_variables_env(yaml_dict):
    wikibase_release_pipeline_path = "./target/"+str(yaml_dict["repo"])+"/src/scripts/wikibase-release-pipeline"
    variables_env_path = wikibase_release_pipeline_path + "/variables.env"

    all_extensions_list = []
    all_extensions_dict = {}

    variables_env_str = None
    new_variables_env_str = None
    last_variable_line_str = None

    # Open variable.env and read in current contents.
    with open(variables_env_path, "r") as f:
        variables_env_str = f.read()
        new_variables_env_str = variables_env_str

    # Open Dockerfile and determine which new contents to add.
    with open(variables_env_path, "r") as f:
        variables_env_lines = f.readlines()

        for count, line in enumerate(variables_env_lines):
            if line.startswith("# https://gerrit.wikimedia.org/r/plugins/gitiles/mediawiki/extensions/"):
                
                # Get extension name.
                pre_extension_name = line.split("# https://gerrit.wikimedia.org/r/plugins/gitiles/mediawiki/extensions/")[1]
                extension_name = pre_extension_name.split("/")[0]

                # Get commit name.
                commit_name = ((variables_env_lines[count+1]).split("=")[1]).strip()

                all_extensions_list.append(extension_name)
                all_extensions_dict[extension_name] = commit_name

                # Get last line in this section so we know where to insert after.
                last_variable_line_str = variables_env_lines[count+1]

    extensions_to_add = []
    for extension in yaml_dict['wikibase']['extensions']:
        if extension not in all_extensions_list:
            extensions_to_add.append(extension)

    # Construct Gerrit link and commit name lines to add to variables.env.
    extensions_to_add_dict = {}
    for extension in extensions_to_add:
        gerrit_link = "https://gerrit.wikimedia.org/r/plugins/gitiles/mediawiki/extensions/" + extension + "/+/refs/heads/REL1_42"
        gerrit_link_line = "# " + gerrit_link
        
        # <th class="Metadata-title">commit</th><td>996bb21eff34c1e05148f36dbdb38c7934bae4e5</td><td>
        gerrit_page_content = requests.get(gerrit_link).text
        commit_lines_text_1 = gerrit_page_content.split('<th class="Metadata-title">commit</th><td>')[1]
        commit_name = (commit_lines_text_1.split('</td><td>')[0]).strip()
        commit_line = extension.upper() + "_COMMIT=" + commit_name

        extensions_to_add_dict[extension] = {
            'gerrit': gerrit_link,
            'gerrit_line': gerrit_link_line,
            'commit': commit_name,
            'commit_line': commit_line
        }

    new_last_variable_line_str = last_variable_line_str
    for extension, extension_sub_dict in extensions_to_add_dict.items():
        new_last_variable_line_str += extension_sub_dict['gerrit_line'] + "\n" + commit_line + "\n"

    # Write new lines to variables.env.
    new_variables_env_str = variables_env_str.replace(last_variable_line_str, new_last_variable_line_str)

    # Add writing to the file.
    with open(variables_env_path, "w") as f:
        f.write(new_variables_env_str)

def modify_dockerfile(yaml_dict):
    wikibase_release_pipeline_path = "./target/"+str(yaml_dict["repo"])+"/src/scripts/wikibase-release-pipeline"
    dockerfile_path = wikibase_release_pipeline_path + "/build/Wikibase/Dockerfile"

    all_extensions_line = None
    all_extensions_list = []

    dockerfile_str = None
    new_dockerfile_str = None
    
    # Open Dockerfile and read in current contents.
    with open(dockerfile_path, "r") as f:
        dockerfile_str = f.read()
        new_dockerfile_str = dockerfile_str

    # Open Dockerfile and determine which new contents to add.
    with open(dockerfile_path, "r") as f:
        dockerfile_lines = f.readlines()

        # Get current extensions list.
        for line in dockerfile_lines:
            if line.startswith('ARG ALL_EXTENSIONS='):
                all_extensions_line = line
        all_extensions_list = ((all_extensions_line.split('=')[1])[1:-2]).split(',')

        # Get list of extensions to add.
        extensions_to_add = []
        for extension in yaml_dict['wikibase']['extensions']:
            if extension not in all_extensions_list:
                extensions_to_add.append(extension)
        extensions_to_add_str = ','.join(extensions_to_add)
        if len(extensions_to_add) > 0:
            new_all_extensions_line = all_extensions_line[:-2] + ',' + extensions_to_add_str + '"' + "\n"
            new_dockerfile_str = dockerfile_str.replace(all_extensions_line, new_all_extensions_line)

            # Format new extension additions.
            new_arg_lines = []
            for extension in extensions_to_add:
                uppercase_extension = extension.upper()
                extension_arg = "ARG " + uppercase_extension + "_COMMIT"
                new_arg_lines.append(extension_arg)
            new_arg_lines_str = "\n".join(new_arg_lines)

            final_extension_arg = "ARG " + (all_extensions_list[-1]).upper() + "_COMMIT"
            new_dockerfile_lines = new_dockerfile_str.split('\n')
            for counter, line in enumerate(new_dockerfile_lines):
                if line == final_extension_arg:
                    new_dockerfile_lines[counter] += "\n" + new_arg_lines_str

            new_dockerfile_str = "\n".join(new_dockerfile_lines)

    # Write Dockerfile with added extensions.
    with open(dockerfile_path, 'w') as f:
        f.write(new_dockerfile_str)

def modify_build_sh(yaml_dict):
    wikibase_release_pipeline_path = "./target/"+str(yaml_dict["repo"])+"/src/scripts/wikibase-release-pipeline"
    build_sh_path = wikibase_release_pipeline_path + "/build.sh"

    all_extensions_list_upper = []
    final_extension_line = None

    build_sh_str = None
    new_build_sh_str = None
    
    # Open build.sh and read in current contents.
    with open(build_sh_path, "r", encoding="utf8") as f:
        build_sh_str = f.read()
        new_build_sh_str = build_sh_str

    # Open build.sh and determine which new contents to add.
    with open(build_sh_path, "r", encoding="utf8") as f:
        build_sh_lines = f.readlines()

        all_extensions_list_upper = []
        in_wikibase_build = False
        for count, line in enumerate(build_sh_lines):
            if line.startswith("function build_wikibase {"):
                in_wikibase_build = True
            if line.startswith("function build_elasticseach {"):
                in_wikibase_build = False

            if line.startswith("        --build-arg ") and in_wikibase_build:
                extension_name_1 = line.split("--build-arg ")
                extension_name_2 = extension_name_1[1].split(" \\\n")
                extension_name_3 = extension_name_2[0].split("=")
                commit_param_portion = extension_name_3[0]
                commit_var_portion = extension_name_3[1]
                extension_name_upper = commit_param_portion.split("_COMMIT")[0]
                all_extensions_list_upper.append(extension_name_upper)
                final_extension_line = line

    extensions_to_add = []
    for extension in yaml_dict['wikibase']['extensions']:
        if extension.upper() not in all_extensions_list_upper:
            extensions_to_add.append(extension)

    lines_to_add = []
    for extension in extensions_to_add:
        # --build-arg WIKIBASELOCALMEDIA_COMMIT="$WIKIBASELOCALMEDIA_COMMIT" \
        extension_line = '        --build-arg ' + extension.upper() + '_COMMIT="$' + extension.upper() + '_COMMIT" \\\n'
        lines_to_add.append(extension_line)

    if len(lines_to_add) > 0:
        lines_to_add_str = "".join(lines_to_add)
        final_extension_line_with_lines_to_add = final_extension_line + lines_to_add_str

        new_build_sh_str = build_sh_str.replace(final_extension_line, final_extension_line_with_lines_to_add)

    # Write build.sh with added extensions.
    with open(build_sh_path, 'w', encoding="utf8") as f:
        f.write(new_build_sh_str)

def modify_localsettings(yaml_dict):
    wikibase_release_pipeline_path = "./target/"+str(yaml_dict["repo"])+"/src/scripts/wikibase-release-pipeline"
    localsettings_dir_path = wikibase_release_pipeline_path + "/build/Wikibase/LocalSettings.d"

    # Get list of files in the directory; extract existing extensions.
    included_extension_names = []
    file_names = [f for f in os.listdir(localsettings_dir_path) if os.path.isfile(os.path.join(localsettings_dir_path, f))]
    for file_name in file_names:
        pre_extension_name_1 = file_name.split("_")[1]
        extension_name = pre_extension_name_1.split(".php")[0]
        included_extension_names.append(extension_name)

    # Get list of extensions from YAML that are not in the directory.
    extensions_to_add = []
    extensions_to_add_dict = {}
    for extension in yaml_dict['wikibase']['extensions']:
        if extension not in included_extension_names:
            extensions_to_add.append(extension)
            if extension == "Kartographer":
                extension_order_prefix = "60_"
                extension_file_content = ("<?php\n\n# " + "".join(camel_case_split(extension)) + "\n" + "wfLoadExtension( '" + extension + "' );" + "\n" +
                    "$wgKartographerMapServer = 'http://localhost:8080';" + "\n" + "$wgKartographerDfltStyle = '';" + "\n" +
                    "$wgKartographerSrcsetScales = [1];" + "\n" + "$wgKartographerStyles = [];" + "\n" +
                    "$wgKartographerUseMarkerStyle = true;" + "\n" + "$wgWBRepoSettings['useKartographerGlobeCoordinateFormatter'] = true;")
            else:
                extension_order_prefix = "50_"
                extension_file_content = "<?php\n\n# " + "".join(camel_case_split(extension)) + "\n" + "wfLoadExtension( '" + extension + "' );"
            extensions_to_add_dict[extension] = {
                "file_name": extension_order_prefix + extension + ".php",
                "file_content": extension_file_content
            }

    # Make additional files and add content.
    for extension, extension_sub_dict in extensions_to_add_dict.items():
        with open(localsettings_dir_path + "/" + extension_sub_dict["file_name"], "w") as f:
            f.write(extension_sub_dict["file_content"])

def rebuild_wikibase_container(yaml_dict):
    wikibase_release_pipeline_path = "./target/"+str(yaml_dict["repo"])+"/src/scripts/wikibase-release-pipeline"
    chdir(wikibase_release_pipeline_path)
    subprocess.run("build.sh wikibase", shell=True)

def modify_docker_compose_yml(yaml_dict):
    wikibase_release_pipeline_path = "./target/"+str(yaml_dict["repo"])+"/src/scripts/wikibase-release-pipeline"
    docker_compose_yml_path = wikibase_release_pipeline_path + "/deploy/docker-compose.yml"

    current_image = "image: wikibase/wikibase:3"
    new_image = "image: wikibase/wikibase:latest"

    docker_compose_yml_str = None
    new_docker_compose_yml_str = None
    
    # Open docker-compose.yml and read in current contents.
    with open(docker_compose_yml_path, "r") as f:
        docker_compose_yml_str = f.read()
        new_docker_compose_yml_str = docker_compose_yml_str

    original_image_str_line = "  wikibase:\n    " + current_image
    new_image_str_line = "  wikibase:\n    " + new_image

    # Open docker-compose.yml and determine which new contents to add.
    new_docker_compose_yml_str = docker_compose_yml_str.replace(original_image_str_line, new_image_str_line)

    with open(docker_compose_yml_path, "w") as f:
        f.write(new_docker_compose_yml_str)

def camel_case_split(identifier):
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return [m.group(0) for m in matches]

if __name__ == '__main__':
    main()