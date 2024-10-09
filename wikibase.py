#!/usr/bin/env python

#
#   Clair Kronk
#   9 August 2024
#   wikibase.py
#

import argparse
import convert_crlf_to_lf
import fileinput
import os
import shutil
import subprocess
import time
import wikibase_config
import wikibase_extensions
import wikibase_import
import yaml

from os import getcwd, path, chdir
from pathlib import Path

wd = os.getcwd()

container_list = [
    "wbs-deploy-elasticsearch-1",
    "wbs-deploy-mysql-1",
    "wbs-deploy-traefik-1",
    "wbs-deploy-wikibase-1",
    "wbs-deploy-quickstatements-1",
    "wbs-deploy-wdqs-1",
    "wbs-deploy-wikibase-jobrunner-1",
    "wbs-deploy-wdqs-updater-1",
    "wbs-deploy-wdqs-proxy-1",
    "wbs-deploy-wdqs-frontend-1"
]

def main():

    # Parse arguments.
    parser=argparse.ArgumentParser()
    parser.add_argument('-startover', default=False, action='store_true')
    parser.add_argument('-up', default=False, action='store_true')
    parser.add_argument('-stop', default=False, action='store_true')
    parser.add_argument('-down', default=False, action='store_true')
    parser.add_argument('-reset', default=False, action='store_true')
    parser.add_argument('-install_composer', default=False, action='store_true')
    parser.add_argument('-install_rdfsync', default=False, action='store_true')
    parser.add_argument('-load_extensions', default=False, action='store_true')
    parser.add_argument('-import_files', default=False, action='store_true')
    parser.add_argument('-test', default=False, action='store_true')
    parser.add_argument('-tileserver', default=False, action='store_true')
    parser.add_argument('-visualize', default=False, action='store_true')
    parser.add_argument('-rebuild', default=False, action='store_true')
    parser.add_argument('-wqs', default=False, action='store_true')
    parser.add_argument('-zotwb', default=False, action='store_true')
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
        download_wikibase_release_pipeline(repo, yaml_dict=yaml_dict, load_extensions_at_build=True)

        # Set up configuration template.
        set_up_configuration_template(deploy_dir, yaml_dict)

        # Put up Docker containers.
        run_docker_compose_up(deploy_dir)

        # Install packages (note that zip must be installed for the Composer install to function).
        #install_packages(yaml_dict)

        # Load extensions.
        #load_extensions(yaml_dict)

        # Install Composer.
        #install_composer()

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

    elif args.rebuild:
        # Run rebuild.
        run_rebuild()

    elif args.reset:
        # Reset Docker containers.
        reset_configuration(deploy_dir, yaml_dict)

    elif args.install_composer:
        # Install packages (note that zip must be installed for the Composer install to function).
        install_packages(yaml_dict)

        # Install Composer.
        install_composer()

    elif args.install_rdfsync:
        install_rdfsync(yaml_dict)

    elif args.load_extensions:
        # Load Wikibase extensions.
        load_extensions(yaml_dict)

    elif args.import_files:
        # Install packages if necessary.
        #install_packages(yaml_dict)

        # Install Composer.
        #install_composer()

        # Add extensions if not done so already.
        #load_extensions(yaml_dict)

        # Set up quality constraints if not already done.
        #set_up_wikibase_quality_constraints(yaml_dict)

        # Set string limits.
        wikibase_config.set_string_limits(yaml_dict)

        # Import from RDF files.
        import_files(yaml_dict)

        # Run rebuild.
        run_rebuild()

        # Export RDF from Wikibase instance.
        export_rdf()

        # Massage data in correct format for query service.
        munge(yaml_dict)

        # Import data into the query service.
        load_data()

    elif args.tileserver:

        # Set up tileserver.
        set_up_tileserver(yaml_dict['repo'])

    elif args.visualize:

        # Set up visualizer.
        set_up_visualizer()

    elif args.wqs:

        # Export RDF from Wikibase instance.
        export_rdf()

        # Massage data in correct format for query service.
        munge(yaml_dict)

        # Import data into the query service.
        load_data()

    elif args.zotwb:

        install_zotwb(yaml_dict)
    
    else:
        run_docker_compose_stop(deploy_dir)
        run_docker_compose_down(deploy_dir)
        delete_configuration(deploy_dir)
        download_wikibase_release_pipeline(repo, yaml_dict=yaml_dict, load_extensions_at_build=True)
        delete_configuration(deploy_dir)
        set_up_configuration_template(deploy_dir, yaml_dict)
        run_docker_compose_up(deploy_dir, wait=True)
        #install_packages(yaml_dict)
        set_up_wikibase_quality_constraints(yaml_dict)
        wikibase_config.set_string_limits(yaml_dict)
        import_files(yaml_dict, reset_internal_state=True)
        run_rebuild()
        export_rdf()
        munge(yaml_dict)
        load_data()

# Makes modifications to .env based on a YAML file.
def make_modifications(yaml_dict, deploy_dir):
    if "wikibase_public_host" in yaml_dict["wikibase"]:
        replace_in_file(deploy_dir+"/.env", "WIKIBASE_PUBLIC_HOST=wikibase.example.com", "WIKIBASE_PUBLIC_HOST="+yaml_dict["wikibase"]["wikibase_public_host"])

# Downloads the Wikibase Release Pipeline from GitHub.
def download_wikibase_release_pipeline(repo, yaml_dict=None, load_extensions_at_build=True):

    wikibase_release_pipeline_dir="./target/"+str(repo)+"/src/scripts/wikibase-release-pipeline"

    # Clone wikibase-release-pipeline.
    if not path.exists(wikibase_release_pipeline_dir):
        subprocess.run("git clone https://github.com/wmde/wikibase-release-pipeline "+wikibase_release_pipeline_dir, shell=True) 

    if path.exists(wikibase_release_pipeline_dir):
        # Change branch.
        deploy_dir=wikibase_release_pipeline_dir+"/deploy"
        chdir(deploy_dir)
        subprocess.run("git checkout deploy-3", shell=True)
        chdir(wd)

        # Copy .gitattributes file.
        shutil.copy("./.gitattributes", wikibase_release_pipeline_dir+"/build/Wikibase/")

        # Load extensions if indicated. Note that this process also rebuilds the container,
        # so you can skip the building step (hence the if-else)
        if load_extensions_at_build and yaml_dict:
            load_extensions(yaml_dict, install_at_build_time=True)
        else:
            # Convert strings to Unix.
            convert_crlf_to_lf.convert(str(wd))

            # Build Docker containers.
            chdir(wikibase_release_pipeline_dir)
            subprocess.run("build.sh wikibase", shell=True)
            chdir(wd)

        return deploy_dir
    
    else:
        print("Git repository wikibase-release-pipeline failed to clone successfully. Exiting...")
        exit()

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
def run_docker_compose_up(deploy_dir, wait=False):
    if path.exists(deploy_dir):
        chdir(deploy_dir)
        if wait:
            subprocess.run("docker compose up --wait", shell=True)
        else:
            subprocess.run("docker compose up", shell=True)
        chdir(wd)
        if False in list(check_all_containers(container_list).values()):
            print("At least one of the required containers is unhealthy or not running. Exiting...")
            exit()
    else:
        print("Deploy directory path does not exist. Exiting...")
        exit()

# Runs Docker compose stop.
def run_docker_compose_stop(deploy_dir):
    if path.exists(deploy_dir):
        chdir(deploy_dir)
        subprocess.run("docker compose stop", shell=True)
        chdir(wd)
    else:
        print("Deploy directory path does not exist. Skipping...")

# Runs Docker compose down.
def run_docker_compose_down(deploy_dir):
    if path.exists(deploy_dir):
        chdir(deploy_dir)
        subprocess.run("docker compose down --volumes", shell=True)
        chdir(wd)
    else:
        print("Deploy directory path does not exist. Skipping...")

# Check all containers.
def check_all_containers(container_list):
    container_dict = {}
    for container_name in container_list:
        container_dict[container_name] = check_container(container_name)
    return container_dict

# Check container is up.
def check_container(container_name):
    s = str(subprocess.check_output('docker ps', shell=True))
    if s.find(container_name) != -1:
        return True
    else:
        return False

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

    kartographer = False
    if "Kartographer" in yaml_dict['wikibase']['extensions']:
        set_up_tileserver(yaml_dict["repo"])
        kartographer = True

    # This process is based on the system suggested here for deploy-3:
    # https://phabricator.wikimedia.org/T372599
    #
    # The non-build time install does not currently function on the most
    # recent version of the wikibase-release-pipeline.
    if install_at_build_time:

        wikibase_release_pipeline_path = "./target/"+str(yaml_dict["repo"])+"/src/scripts/wikibase-release-pipeline"

        # Add extension(s) to build file (./variable.env)
            # Get Gerrit link, e.g.: https://gerrit.wikimedia.org/r/plugins/gitiles/mediawiki/extensions/WikibaseLexeme/+/refs/heads/REL1_42
            # Get commit, e.g.: 996bb21eff34c1e05148f36dbdb38c7934bae4e5
        wikibase_extensions.modify_variables_env(yaml_dict)

        # Write Dockerfile with added extensions.
        wikibase_extensions.modify_dockerfile(yaml_dict)

        # Write build.sh with added extensions.
        wikibase_extensions.modify_build_sh(yaml_dict)

        # Add LocalSettings.php fragment(s).
            # Make file of the form: /build/Wikibase/LocalSettings.d/50_WikibaseLexeme.php
                # Loaded in alphabetical order; can control via the prefix (so all added extensions can be 50 to be
                # in the correct load order unless there are other requirements).
        wikibase_extensions.modify_localsettings(yaml_dict)

        # Rebuild the Wikibase containers only.
        # Note: This will spawn a second process in another window; it will take
        # time to complete, but should be less than 10 minutes.
        wikibase_extensions.rebuild_wikibase_container(yaml_dict)
        chdir(wd)

        # Adjust docker-compose.yml.
        wikibase_extensions.modify_docker_compose_yml(yaml_dict)

    else:

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

def set_up_wikibase_quality_constraints(yaml_dict, load_extensions=False):
    if "quality_constraints_mappings" in yaml_dict["wikibase"]:
        print("Not yet implemented.")
    else:
        local_settings_dict = wikibase_config.get_local_settings()
        if "wgWBQualityConstraintsPropertyConstraintId" in local_settings_dict:
            pass
        else:

            # Check if WikibaseQualityConstraints exists in the Docker container,
            # and if not, copy it over.
            if load_extensions:
                new_quick_yaml = {
                    'wikibase': {
                        'extensions': ['WikibaseQualityConstraints']
                    }
                }
                load_extensions(new_quick_yaml, install_at_build_time=False)

                # TODO: Make sure this doesn't run if already run? This should work, but it's just a stop-gap measure.
                subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/update.php --quick"', shell=True)
                subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/run.php WikibaseQualityConstraints:ImportConstraintEntities.php | tee -a /var/www/html/LocalSettings.php"', shell=True)
                subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/runJobs.php"', shell=True)

        # TODO: Add to rebuild recent changes.

def import_files(yaml_dict, reset_internal_state=False):
    if "import" in yaml_dict["wikibase"]:
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
    
def install_rdfsync(yaml_dict):
    # Check if wikibase-sync has been downloaded; if not begin downloading.
    rdf_sync_dir="./target/"+yaml_dict['repo']+"/src/scripts/rdfsync"
    if not path.exists(rdf_sync_dir):
        subprocess.run("git clone https://github.com/weso/rdfsync "+rdf_sync_dir, shell=True)

    # Find rdfsync setup.py.
    rdfsync_setup_file = rdf_sync_dir + '/setup.py'
    print(rdfsync_setup_file)

    # Remove RDFlib portion.
    setup_py_str = ""
    with open(rdfsync_setup_file, 'r') as f:
        setup_py_str = f.read()
        new_setup_py_str = setup_py_str.replace("'rdflib==5.0.0', ", "")
    with open(rdfsync_setup_file, 'w') as f:
        f.write(new_setup_py_str)

    # Install
    chdir(rdf_sync_dir)
    subprocess.run("python setup.py install", shell=True)
    chdir(wd)

def set_up_tileserver(repo):
    tileserver_data = dockerfile_path = "./target/"+repo+"/src/scripts/tileserver-gl"
    os.makedirs(tileserver_data, exist_ok=True)
    subprocess.run("docker run --rm -it -v %s/data -p 8080:8080 maptiler/tileserver-gl" % tileserver_data, shell=True)

def set_up_visualizer(visualizer='KinGVisher'):
    if visualizer.lower() == 'kingvisher':
        subprocess.run("docker run -p 8501:8501 wseresearch/knowledge-graph-visualizer:latest", shell=True)
    elif visualizer.lower() == 'wikidata-graph-builder':
        subprocess.run()
    else:
        print("Visualizer not recognized. Exiting...")
        exit()

def export_rdf():
    # Adapted from: https://thisismattmiller.com/post/migrating-your-docker-wikibase/
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/extensions/Wikibase/repo/maintenance/dumpRdf.php > /tmp/backup.ttl"', shell=True)

def munge(yaml_dict):
    if "wikibase_public_host" in yaml_dict["wikibase"]:
        # Adapted from: https://thisismattmiller.com/post/migrating-your-docker-wikibase/
        host_rdf_path=os.path.join(os.environ['TEMP'], "%s" % str("backup.ttl"))
        subprocess.run("docker cp wbs-deploy-wikibase-1:/tmp/backup.ttl " + host_rdf_path, shell=True)
        subprocess.run("docker cp " + host_rdf_path + " wbs-deploy-wdqs-1:/tmp/backup.ttl", shell=True)

        # TODO: Fix to dynamically change.
        subprocess.run('docker exec wbs-deploy-wdqs-1 //bin//bash -c "./munge.sh -f /tmp/backup.ttl -- --conceptUri ' + 'https://' + yaml_dict["wikibase"]["wikibase_public_host"] + '"', shell=True)
    else:
        print("No public host declared. Exiting...")
        exit()

def load_data():
    # Adapted from: https://thisismattmiller.com/post/migrating-your-docker-wikibase/
    subprocess.run('docker exec wbs-deploy-wdqs-1 //bin//bash -c "./loadData.sh -n wdq -d /wdqs/"', shell=True)

def install_zotwb():
    print()
    # https://github.com/dlindem/zotwb
    
if __name__ == '__main__':
    main()