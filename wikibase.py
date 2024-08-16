#!/usr/bin/env python

#
#   Clair Kronk
#   9 August 2024
#   wikibase.py
#

import argparse
import fileinput
import os
import shutil
import subprocess
import time
import wikibase_config
import wikibase_import
import yaml

from os import getcwd, path, chdir
from pathlib import Path

wd = os.getcwd()

def main():

    # Parse arguments.
    parser=argparse.ArgumentParser()
    parser.add_argument('-startover', default=False, action='store_true')
    parser.add_argument('-up', default=False, action='store_true')
    parser.add_argument('-stop', default=False, action='store_true')
    parser.add_argument('-down', default=False, action='store_true')
    parser.add_argument('-reset', default=False, action='store_true')
    parser.add_argument('-install_composer', default=False, action='store_true')
    parser.add_argument('-load_extensions', default=False, action='store_true')
    parser.add_argument('-import_files', default=False, action='store_true')
    parser.add_argument('-test', default=False, action='store_true')
    args=parser.parse_args()

    # Read in YAML file.
    yaml_dict=yaml.safe_load(Path("project.yaml").read_text())
    print(yaml_dict)
    repo=yaml_dict['repo']
    wikibase_release_pipeline_dir="./target/"+str(repo)+"/src/scripts/wikibase-release-pipeline"
    deploy_dir=wikibase_release_pipeline_dir+"/deploy"

    if args.test:
        print("All packages correctly installed. Exiting...")
        exit()
    elif args.startover:
        # Stop Docker containers.
        run_docker_compose_stop(deploy_dir)

        # Put down Docker containers.
        run_docker_compose_down(deploy_dir)

        # Delete configuration.
        delete_configuration(deploy_dir)

        # Download Wikibase release pipeline.
        download_wikibase_release_pipeline(repo)

        # Set up configuration template.
        set_up_configuration_template(deploy_dir, yaml_dict)

        # Put up Docker containers.
        run_docker_compose_up(deploy_dir)

        # Install packages (note that zip must be installed for the Composer install to function).
        install_packages(yaml_dict)

        # Load extensions.
        load_extensions(yaml_dict)

        # Install Composer.
        install_composer()

    elif args.up:
        # Download Wikibase release pipeline.
        download_wikibase_release_pipeline(repo)

        # Set up configuration template.
        set_up_configuration_template(deploy_dir, yaml_dict)

        # Put up Docker containers.
        run_docker_compose_up(deploy_dir)

    elif args.stop and args.down:
        # Stop Docker containers.
        run_docker_compose_stop(deploy_dir)

        # Put down Docker containers.
        run_docker_compose_down(deploy_dir)

    elif args.stop:
        # Stop Docker containers.
        run_docker_compose_stop(deploy_dir)

    elif args.down:
        # Put down Docker containers.
        run_docker_compose_down(deploy_dir)

    elif args.reset:
        # Reset Docker containers.
        reset_configuration(deploy_dir, yaml_dict)

    elif args.install_composer:
        # Install packages (note that zip must be installed for the Composer install to function).
        install_packages(yaml_dict)

        # Install Composer.
        install_composer()

    elif args.load_extensions:
        # Load Wikibase extensions.
        load_extensions(yaml_dict)

    elif args.import_files:
        # Import from RDF files.
        import_files(yaml_dict)
    
    else:
        run_docker_compose_stop(deploy_dir)
        run_docker_compose_down(deploy_dir)
        download_wikibase_release_pipeline(repo)
        delete_configuration(deploy_dir)
        set_up_configuration_template(deploy_dir, yaml_dict)
        run_docker_compose_up(deploy_dir)
        exit()
        install_packages(yaml_dict)
        load_extensions(yaml_dict)
        install_composer()
        set_up_wikibase_quality_constraints(yaml_dict)
        wikibase_config.set_string_limits(yaml_dict)
        import_files(yaml_dict, reset_internal_state=True)
        run_rebuild()

# Makes modifications to .env based on a YAML file.
def make_modifications(yaml_dict, deploy_dir):
    if "wikibase_public_host" in yaml_dict["wikibase"]:
        replace_in_file(deploy_dir+"/.env", "WIKIBASE_PUBLIC_HOST=wikibase.example.com", "WIKIBASE_PUBLIC_HOST="+yaml_dict["wikibase"]["wikibase_public_host"])

# Downloads the Wikibase Release Pipeline from GitHub.
def download_wikibase_release_pipeline(repo):

    wikibase_release_pipeline_dir="./target/"+str(repo)+"/src/scripts/wikibase-release-pipeline"

    # Clone wikibase-release-pipeline.
    if not path.exists(wikibase_release_pipeline_dir):
        subprocess.run("git clone https://github.com/wmde/wikibase-release-pipeline "+wikibase_release_pipeline_dir, shell=True) 

    # Change branch.
    deploy_dir=wikibase_release_pipeline_dir+"/deploy"
    chdir(deploy_dir)
    subprocess.run("git checkout deploy-3", shell=True)
    chdir(wd)

    return deploy_dir

# Sets up the configruation template for the Wikibase instance.
def set_up_configuration_template(deploy_dir, yaml_dict=None):

    # Create .env file.
    chdir(deploy_dir)
    subprocess.run("copy template.env .env", shell=True)
    chdir(wd)

    # TODO: Modify .env file.
        # Note: Using defaults for now.
        # This is where you would change
        # database user names, passwords, keys, etc.
    if yaml_dict:
        make_modifications(yaml_dict, deploy_dir)

# Runs Docker compose up.
def run_docker_compose_up(deploy_dir):
    if path.exists(deploy_dir):
        chdir(deploy_dir)
        subprocess.run("docker compose up --wait", shell=True)
        chdir(wd)

# Runs Docker compose stop.
def run_docker_compose_stop(deploy_dir):
    if path.exists(deploy_dir):
        chdir(deploy_dir)
        subprocess.run("docker compose stop", shell=True)
        chdir(wd)

# Runs Docker compose down.
def run_docker_compose_down(deploy_dir):
    if path.exists(deploy_dir):
        chdir(deploy_dir)
        subprocess.run("docker compose down --volumes", shell=True)
        chdir(wd)

# Deletes the Docker configuration.
def delete_configuration(deploy_dir):
    try:
        os.remove(deploy_dir+'/config/LocalSettings.php')
    except FileNotFoundError:
        pass

# Resets the Docker configuration.
def reset_configuration(deploy_dir, yaml_dict=None):
    delete_configuration(deploy_dir, yaml_dict)
    run_docker_compose_down(deploy_dir)
    if yaml_dict:
        make_modifications(deploy_dir, yaml_dict)
    run_docker_compose_up(deploy_dir)

# Installs a Wikibase extension.
def install_wikibase_extension():
    print()

# Replaces a line in a file with another line."
def replace_in_file(file_path, search_text, new_text):
    with fileinput.input(file_path, inplace=True) as file:
        for line in file:
            new_line = line.replace(search_text, new_text)
            print(new_line, end='')

# Install packages (note that zip must be installed for the Composer install to function).
def install_packages(yaml_dict, install_at_build_time=True):
    # Run update.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "apt-get -y update"', shell=True)

    # Install packages.
    for package in yaml_dict['wikibase']['packages']:
        subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "apt-get -y install %s"' % str(package), shell=True)

# Install Composer in Docker container.
def install_composer():
    # Copy script into container.
    subprocess.run("docker cp install_composer.sh wbs-deploy-wikibase-1:/var/tmp/install_composer.sh", shell=True)

    # Run script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "/var/tmp/install_composer.sh"', shell=True)

    # Remove script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "rm /var/tmp/install_composer.sh"', shell=True)

    # Run update.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/update.php --force"', shell=True)

# Clone and load extensions.
def load_extensions(yaml_dict, persist_on_host=True, install_at_build_time=True):

    # Download, copy, and load each extension.
    for extension in yaml_dict['wikibase']['extensions']:
        # Check if the extension exists already in the container.
        try:
            path_exists_str=str(subprocess.check_output('docker exec wbs-deploy-wikibase-1 //bin//bash -c "test -d /var/www/html/extensions/%s" && echo True' % str(extension), shell=True).decode('utf8')).strip()
        except subprocess.CalledProcessError:
            path_exists_str=False
        path_exists=False
        if path_exists_str == "True":
            path_exists=True

        if not path_exists:

            # Make extension path.
            host_extension_path=os.path.join(os.environ['TEMP'], "%s" % str(extension))

            # Clone extension.
            if not path.exists(host_extension_path):
                subprocess.run("git clone -b REL1_41 https://gerrit.wikimedia.org/r/p/mediawiki/extensions/%s.git %s" % (str(extension), str(host_extension_path)), shell=True)

            # Copy extension to container.
            subprocess.run("docker cp %s wbs-deploy-wikibase-1:/var/www/html/extensions/%s" % (str(host_extension_path), str(extension)), shell=True)

            # Delete extension on host.
            if not persist_on_host:
                try:
                    shutil.rmtree(host_extension_path) # Permission error still happening?
                except FileNotFoundError:
                    pass

    # Send over script to check LocalSettings.php.
    subprocess.run("docker cp check_local_settings.sh wbs-deploy-wikibase-1:/var/tmp/check_local_settings.sh", shell=True)

    # Load extensions in LocalSettings.php (if they don't exist there already).
    extensions_to_check=" ".join(yaml_dict['wikibase']['extensions'])

    # Run script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "/var/tmp/check_local_settings.sh %s"' % (str(extensions_to_check)), shell=True)

    # Remove script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "rm /var/tmp/check_local_settings.sh"', shell=True)

def set_up_wikibase_quality_constraints(yaml_dict):
    if "quality_constraints_mappings" in yaml_dict["wikibase"]:
        print("Not yet implemented.")
    else:
        local_settings_dict = wikibase_config.get_local_settings()
        if "wgWBQualityConstraintsPropertyConstraintId" in local_settings_dict:
            pass
        else:
            # TODO: Make sure this doesn't run if already run? This should work, but it's just a stop-gap measure.
            subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/update.php --quick"', shell=True)
            subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/run.php WikibaseQualityConstraints:ImportConstraintEntities.php | tee -a /var/www/html/LocalSettings.php"', shell=True)
            subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/runJobs.php"', shell=True)

        # TODO: Add to rebuild recent changes.

def import_files(yaml_dict, reset_internal_state=False):
    if "import" in yaml_dict["wikibase"]:
        hercules_sync_dir = "./target/"+yaml_dict["repo"]+"/src/scripts/hercules-sync"
        if not path.exists(hercules_sync_dir):
            wikibase_import.install_hercules_sync(yaml_dict)
        
        wikibase_sync_dir = "./target/"+yaml_dict["repo"]+"/src/scripts/wikibase-sync"
        if not path.exists(wikibase_sync_dir):
            wikibase_import.install_wikibase_sync(yaml_dict)

        if reset_internal_state:
            wikibase_import.init_factory(yaml_dict)

        local_settings_dict = wikibase_config.get_local_settings()
        wikibase_import.import_from_file(yaml_dict, local_settings_dict)

    else:
        pass

def run_rebuild():
    # Send over rebuild script.
    subprocess.run("docker cp wikibase_rebuild.sh wbs-deploy-wikibase-1:/var/tmp/wikibase_rebuild.sh", shell=True)

    # Run rebuild script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "/var/tmp/wikibase_rebuild.sh"', shell=True)

    # Remove rebuild script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "rm /var/tmp/wikibase_rebuild.sh"', shell=True)
    
if __name__ == '__main__':
    main()