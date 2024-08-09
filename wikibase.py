#!/usr/bin/env python

#
#   Clair Kronk
#   9 August 2024
#   wikibase.py
#

import argparse
import fileinput
import subprocess
import yaml

from contextlib import chdir
from os import getcwd, path
from pathlib import Path

def main():

    # Parse arguments.
    parser=argparse.ArgumentParser()
    parser.add_argument('-up', default=False, action='store_true')
    parser.add_argument('-stop', default=False, action='store_true')
    parser.add_argument('-down', default=False, action='store_true')
    parser.add_argument('-reset', default=False, action='store_true')
    parser.add_argument('-upload', default=False, action='store_true')
    parser.add_argument('-download', default=False, action='store_true')
    args=parser.parse_args()

    # Read in YAML file.
    yaml_dict=yaml.safe_load(Path("project.yaml").read_text())
    print(yaml_dict)
    repo=yaml_dict['repo']
    wikibase_release_pipeline_dir="./target/"+str(repo)+"/src/scripts/wikibase-release-pipeline"
    deploy_dir=wikibase_release_pipeline_dir+"/deploy"

    if args.up:
        # Download Wikibase release pipeline.
        download_wikibase_release_pipeline(repo)

        # Set up configuration template.
        set_up_configuration_template(deploy_dir, yaml_dict)

        # Put up Docker containers.
        run_docker_compose_up(deploy_dir)

    elif args.stop:
        # Stop Docker containers.
        run_docker_compose_stop(deploy_dir)

    elif args.down:
        # Put down Docker containers.
        run_docker_compose_down(deploy_dir)

    elif args.reset:
        # Reset Docker containers.
        reset_configuration(deploy_dir, yaml_dict)

    else:
        download_wikibase_release_pipeline(repo)
        set_up_configuration_template(deploy_dir, yaml_dict)
        run_docker_compose_up(deploy_dir)

# Makes modifications to .env based on a YAML file.
def make_modifications(yaml_dict, deploy_dir):
    if "wikibase_public_host" in yaml_dict:
        replace_in_file(deploy_dir+"/.env", "WIKIBASE_PUBLIC_HOST=wikibase.example.com", "WIKIBASE_PUBLIC_HOST="+yaml_dict["wikibase_public_host"])

# Downloads the Wikibase Release Pipeline from GitHub.
def download_wikibase_release_pipeline(repo):

    wikibase_release_pipeline_dir="./target/"+str(repo)+"/src/scripts/wikibase-release-pipeline"

    # Clone wikibase-release-pipeline.
    if not path.exists(wikibase_release_pipeline_dir):
        subprocess.run("git clone https://github.com/wmde/wikibase-release-pipeline "+wikibase_release_pipeline_dir, shell=True) 
    
    # Change branch.
    deploy_dir=wikibase_release_pipeline_dir+"/deploy"
    with chdir(deploy_dir):
        subprocess.run("git checkout deploy-3", shell=True)

    return deploy_dir

# Sets up the configruation template for the Wikibase instance.
def set_up_configuration_template(deploy_dir, yaml_dict=None):

    # Create .env file.
    with chdir(deploy_dir):
        subprocess.run("copy template.env .env", shell=True)

    # TODO: Modify .env file.
        # Note: Using defaults for now.
        # This is where you would change
        # database user names, passwords, keys, etc.
    if yaml_dict:
        make_modifications(yaml_dict, deploy_dir)

# Runs Docker compose up.
def run_docker_compose_up(deploy_dir):
    with chdir(deploy_dir):
        subprocess.run("docker compose up --wait", shell=True)

# Runs Docker compose stop.
def run_docker_compose_stop(deploy_dir):
    with chdir(deploy_dir):
        subprocess.run("docker compose stop", shell=True)

# Runs Docker compose down.
def run_docker_compose_down(deploy_dir):
    with chdir(deploy_dir):
        subprocess.run("docker compose down --volumes", shell=True)

# Resets the Docker configuration.
def reset_configuration(deploy_dir, yaml_dict=None):
    with chdir(deploy_dir):
        subprocess.run("del /f /q .\config\LocalSettings.php", shell=True)
    run_docker_compose_down(deploy_dir)
    if yaml_dict:
        make_modifications(deploy_dir, yaml_dict)
    run_docker_compose_up(deploy_dir)

# Installs wikiteam3.
def install_wikiteam3():
    subprocess.run("pip install wikiteam3 --upgrade", shell=True)

# Installs a Wikibase extension.
def install_wikibase_extension():
    print()

# Create XML dump.
def create_xml_dump(domain, dump_folder, with_images=False):
    if with_images:
        with chdir(dump_folder):
            subprocess.run("wikiteam3dumpgenerator "+domain+" --xml --images", shell=True)
    else:
        with chdir(dump_folder):
            subprocess.run("wikiteam3dumpgenerator "+domain+" --xml", shell=True)

# Resume XML dump.
def resume_xml_dump(domain, dump_folder):
    with chdir(dump_folder):
        subprocess.run("wikiteam3dumpgenerator "+domain+" --xml --resume", shell=True)

# Uploads an XML dump into the Wikibase.
def upload():
    print()

# Downloads RDF dump from existing Wikibase.
def download():
    print()

# Replaces a line in a file with another line.
def replace_in_file(file_path, search_text, new_text):
    with fileinput.input(file_path, inplace=True) as file:
        for line in file:
            new_line = line.replace(search_text, new_text)
            print(new_line, end='')

if __name__ == '__main__':
    main()