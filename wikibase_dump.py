#!/usr/bin/env python

#
#   Clair Kronk
#   15 August 2024
#   wikibase_dump.py
#

import argparse
import internetarchive
import os
import pathlib
import re
import subprocess
import time
import yaml
import zstandard as zstd

from os import getcwd, path, chdir
from pathlib import Path
from urllib.parse import urlparse

wd = os.getcwd()

def main():

    # Parse arguments.
    parser=argparse.ArgumentParser()
    parser.add_argument('-install', default=False, action='store_true')
    parser.add_argument('-create', default=False, action='store_true')
    parser.add_argument('-resume', default=False, action='store_true')
    parser.add_argument('-upload', default=False, action='store_true')
    parser.add_argument('-download', default=False, action='store_true')
    args=parser.parse_args()

    # Read in YAML file.
    yaml_dict=yaml.safe_load(Path("project.yaml").read_text())
    print(yaml_dict)
    repo=yaml_dict['repo']
    
    # Create dump directories if necessary.
    if "external_host" in yaml_dict["wikibase"]:
        # Make dumps dir if it doesn't exist.
        dump_dir = './target/%s/src/ontology/tmp/dumps/' % (yaml_dict["repo"])
        os.makedirs(dump_dir, exist_ok=True)

        # Make dumpRdf.php if it doesn't exist.
        dump_rdf_dir = dump_dir+'wikiteam3/'
        os.makedirs(dump_rdf_dir, exist_ok=True)

    if args.install:
        install_wikiteam3()
    elif args.create and args.upload:
        dump_folder = create(yaml_dict["wikibase"]["external_host"], dump_rdf_dir, force=True, exclude_namespaces=[146,640])
        upload(dump_rdf_dir + dump_folder)
    elif args.create:
        dump_folder = create(yaml_dict["wikibase"]["external_host"], dump_rdf_dir)
        print(dump_folder)
    elif args.download:
        rdf_dump_file_name = download(yaml_dict)

# Installs wikiteam3.
def install_wikiteam3():
    subprocess.run("pip install wikiteam3 --upgrade", shell=True)

# Create XML dump.
    # Add namespaces option.
def create(domain, dump_folder, with_images=False, force=False, resume=False, exclude_namespaces=[]):

    cmd = ["wikiteam3dumpgenerator", domain, "--xml"]

    if with_images:
        cmd.append("--images")

    if force:
        cmd.append("--force")

    if len(exclude_namespaces) > 0:
        exclude_namespaces = ",".join(map(str, exclude_namespaces))
        cmd.append("--exnamespaces")
        cmd.append(exclude_namespaces)
        
    chdir(dump_folder)
    output = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    dump_path = get_dump_path(domain, output, dump_folder, resume=resume)
    chdir(wd)

    if path.exists(dump_folder + dump_path):
        return dump_path
    else:
        print("WikiTeam3 XML dump path could not be located after creating. Exiting...")
        exit()

# Resume XML dump.
def resume(domain, dump_folder):
    chdir(dump_folder)
    subprocess.run("wikiteam3dumpgenerator "+domain+" --xml --resume", shell=True)
    chdir(wd)

# Uploads an XML dump into the Wikibase.
def upload(dump_folder, yaml_dict=None, reindex=True):
    if yaml_dict:
        if "dumps" in yaml_dict["wikibase"]:
            for dump in yaml_dict["wikibase"]["dumps"]:
                output_file ="/var/tmp/"+str(os.path.basename(dump))
                subprocess.run('docker cp %s wbs-deploy-wikibase-1:%s' % (dump, output_file), shell=True)
                subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/importDump.php < %s"' % (output_file), shell=True)

        elif "external_host" in yaml_dict["wikibase"]:
            # If not indicated in YAML, download using the WikiTeam 3 dumpgenerator.
            create(yaml_dict["wikibase"]["external_host"], "")

            # Upload created dump.
                # TODO: Not sure how to pick up a new XML dump created with WikiTeam3?
    
    elif dump_folder:
        top_level_xml_list = list(pathlib.Path(dump_folder).glob('*-history.xml'))

        if len(top_level_xml_list) > 0:
            for xml_dump in top_level_xml_list:
                xml_dump_str = str(xml_dump)
                output_file ="/var/tmp/"+str(os.path.basename(xml_dump_str))
                subprocess.run('docker cp %s wbs-deploy-wikibase-1:%s' % (xml_dump_str, output_file), shell=True)
                subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/importDump.php < %s"' % (output_file), shell=True)
            if reindex:
                run_rebuild()
        else:
            second_level_xml_list = list(pathlib.Path(dump_folder).rglob('*-history.xml'))
            if len(second_level_xml_list) > 0:
                for xml_dump in top_level_xml_list:
                    xml_dump_str = str(xml_dump)
                    output_file ="/var/tmp/"+str(os.path.basename(xml_dump_str))
                    subprocess.run('docker cp %s wbs-deploy-wikibase-1:/var/tmp/%s' % (xml_dump_str, output_file), shell=True)
                    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/importDump.php < %s"' % (output_file), shell=True)
                if reindex:
                    run_rebuild()
            else:
                third_level_xml_list = list(pathlib.Path(dump_folder).rglob('*-history.xml.zst'))
                if len(third_level_xml_list) > 0:
                    dctx = zstd.ZstdDecompressor()
                    for zst_dump in third_level_xml_list:
                        zst_dump_str = str(zst_dump)
                        zst_dump_str_wo_zst = zst_dump_str.replace('.zst', '')
                        with open(zst_dump_str, 'rb') as ifh, open(zst_dump_str_wo_zst, 'wb') as ofh:
                            dctx.copy_stream(ifh, ofh, write_size=65536)
                        output_file ="/var/tmp/"+str(os.path.basename(zst_dump_str_wo_zst))
                        subprocess.run('docker cp %s wbs-deploy-wikibase-1:%s' % (zst_dump_str_wo_zst, output_file), shell=True)
                        subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/maintenance/importDump.php < %s"' % (output_file), shell=True)
                        if os.path.isfile(zst_dump_str_wo_zst):
                            os.remove(zst_dump_str_wo_zst)

    # Upload all dumps by default.
    else:
        print("Not yet implemented.")

# Downloads RDF dump from existing Wikibase.
def download(yaml_dict):
    time_now=str(int(time.time()))
    wikibase_dump_file=yaml_dict["repo"]+"_"+time_now+".ttl"
    wikibase_dump_path="/var/tmp/"+wikibase_dump_file
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "php /var/www/html/extensions/Wikibase/repo/maintenance/dumpRdf.php > %s"' % wikibase_dump_path, shell=True)
    
    # Make dumps dir if it doesn't exist.
    dump_dir = './target/%s/src/ontology/tmp/dumps/' % yaml_dict["repo"] + '/'
    os.makedirs(dump_dir, exist_ok=True)

    # Make dumpRdf.php if it doesn't exist.
    dump_rdf_dir = dump_dir+'dumpRdf.php/'
    os.makedirs(dump_rdf_dir, exist_ok=True)

    subprocess.run('docker cp wbs-deploy-wikibase-1:%s ./target/%s/src/ontology/tmp/dumps/dumpRdf.php/%s' % (wikibase_dump_path, yaml_dict["repo"], wikibase_dump_file), shell=True)
    return wikibase_dump_file

# Rebuild Wikibase instance.
def run_rebuild():
    # Send over rebuild script.
    subprocess.run("docker cp wikibase_rebuild.sh wbs-deploy-wikibase-1:/var/tmp/wikibase_rebuild.sh", shell=True)

    # Run rebuild script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "/var/tmp/wikibase_rebuild.sh"', shell=True)

    # Remove rebuild script.
    subprocess.run('docker exec wbs-deploy-wikibase-1 //bin//bash -c "rm /var/tmp/wikibase_rebuild.sh"', shell=True)

def get_dump_path(domain, output, dump_folder, resume=False):
    url = urlparse(domain)
    host_name = str(url.hostname)
    host_name_with_escaped_dots = host_name.replace('.', '\.')
    today = time.strftime("%Y%m%d")

    try:
        if resume:
            output2 = output.communicate(input='y')[0]
        else:
            output2 = output.communicate(input='n')[0]
        output = output.communicate()[0]
    except AttributeError:
        output2 = None
    
    regex = "(https:\/\/archive\.org\/details\/wiki-)(%s)(_w-[0-9]{8})" % host_name_with_escaped_dots
    internet_archive_link_result = re.search(regex, str(output))
    
    if internet_archive_link_result:
        internet_archive_link = internet_archive_link_result.group()
        folder_name = internet_archive_link.rsplit('/details/wiki-')[1]

        # File name if created directly by wikiteam3dumpgenerator locally.
        possible_folder = dump_folder + folder_name + "-wikidump"

        # File name if downloaded from Internet Archive.
        possible_folder_2 = dump_folder + "wiki-" + folder_name

        # Check if folder already exists.
        chdir(wd)
        if path.exists(possible_folder):
            return folder_name + "-wikidump"
        elif path.exists(possible_folder_2):
            return "wiki-" + folder_name
        else:
            chdir(dump_folder)
            internetarchive.download('wiki-'+folder_name, verbose=True)
            return "wiki-" + folder_name
    else:
        regex2 = "(\.\/)(%s)(_w-)(%s)(-wikidump)" % (host_name, today)
        local_link_result = re.search(regex2, str(output))
        local_link = local_link_result.group()
        folder_name = local_link.rsplit('./')[1]
        return folder_name
        
if __name__ == '__main__':
    main()