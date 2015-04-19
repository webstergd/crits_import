#!/usr/bin/env python3

import argparse
import configparser
import logging
import os
import requests
import time
import sys
import zipfile

from tempfile import TemporaryDirectory
from fnmatch import fnmatch

def setup_cli(args):
    """ Configure command-line arguements """

    description ="""
    CRITs_import helps with importing sets of information into a CRITs instance."""

    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)

    #parser.add_argument('-d', '--domain', action='store_true', dest='domain', default=False, help='Submit domain')
    #parser.add_argument('-s', '--sample', action='store_true', dest='sample', default=False, help='Submit sample')
    parser.add_argument('-l', '--list', action='store_true', dest='list', default=False, help='Treat arguements as a file containing a newline seperated list')
    parser.add_argument('-f', '--folder', action='store_true', dest='folder', default=False, help='Treat arguements as a folder')


    parser.add_argument('type', type=str, choices=('domain', 'sample'), help='Type of element to submit')
    parser.add_argument('input', help='File or directory name')

    return parser.parse_args(args)


def validate_configuration(args):
    """ Validate configuration options """
    if args.list and args.folder:
        print("Must select a list (-l), a folder (-f), or nothing.")
        sys.exit()

    if args.type == 'domain' and args.folder:
        print("Must select a list (-l) or nothing for domain. I haven't figured out this use case yet.")
        sys.exit()

    if not cfg['crits'].get('url', '') or cfg['crits'].get('url', '') == '<https://127.0.0.1>':
        print("Must supply CRIT's URL in the configutation file")
        sys.exit()

    if not cfg['crits'].get('user', '') or cfg['crits'].get('user', '') == '<user>':
        print("Must supply CRIT's user in the configutation file")
        sys.exit()

    if not cfg['crits'].get('key', '') or cfg['crits'].get('key', '') == '<api_key>':
        print("Must supply CRIT's API Key in the configutation file")
        sys.exit()

    if not cfg['crits'].get('source', '') or cfg['crits'].get('source', '') == '<source>':
        print("Must supply CRIT's source in the configutation file")
        sys.exit()


def submit_domain(domain):
    """ Submit domain to CRITs """
    headers = {'User-agent': 'crits_import'}
    url = "{0}/api/v1/domains/".format(cfg['crits'].get('url')) 
    params = {
        'api_key': cfg['crits'].get('key'),
        'username': cfg['crits'].get('user'),
        'source': cfg['crits'].get('source'),
        'domain': domain
    }

    try:
        response = requests.post(url, headers=headers, data=params, verify=False)
        if response.status_code == requests.codes.ok:
            response_json = response.json()
            logging.info("Submitted domain info {0} to CRITs, response was {1}".format(params['domain'], response_json))
        else:
            logging.info("Submission of {0} failed: {1}".format(url, response.status_code))
    except requests.exceptions.ConnectionError:
        logging.info("Could not connect to CRITs when submitting domain {0}".format(params['domain']))
    except requests.exceptions.HTTPError:
        logging.info("HTTP error when submitting domain {0} to CRITs".format(params['domain']))


def submit_sample(sample):
    """ Submit sample to CRITs """
    headers = {'User-agent': 'crits_import'}
    url = "{0}/api/v1/samples/".format(cfg['crits'].get('url'))
    zip_files = ['application/zip', 'application/gzip', 'application/x-7z-compressed']
    rar_files = ['application/x-rar-compressed']

    # Hash
    md5 = hashlib.md5(sample).hexdigest()
    files = {'filedata': (md5, sample)}

    mime_type = magic.from_buffer(sample, mime=True)
    if mime_type in zip_files:
        file_type = 'zip'
    elif mime_type in rar_files:
        file_type = 'rar'
    else:
        file_type = 'raw'

    params = {
        'api_key': cfg['crits'].get('key'),
        'username': cfg['crits'].get('user'),
        'source': cfg['crits'].get('source'),
        'upload_type': 'file',
        'md5': md5,
        'file_format': file_type  # must be type zip, rar, or raw
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=params, verify=False)
        if response.status_code == requests.codes.ok:
            response_json = response.json()
            logging.info("Submitted sample info {0} to CRITs, response was {1}".format(params['md5'], response_json))
        else:
            logging.info("Submission of {0} failed: {1}".format(url, response.status_code))
    except requests.exceptions.ConnectionError:
        logging.info("Could not connect to CRITs when submitting domain {0}".format(params['md5']))
    except requests.exceptions.HTTPError:
        logging.info("HTTP error when submitting domain {0} to CRITs".format(params['md5']))


def read_file(file_name):
    """ Reads the contents of a newline seperated listing and return a list """
    result = []
    with open(file_name) as infile:
        for line in infile:
            result.append(line.strip())

    return result


def read_folder(folder_name):
    """ Reads the contents of a folder and returns the file names """
    result = []
    for (dirpath, dirnames, filenames) in os.walk(folder_name):
        for name in filenames:
            result.append(os.path.join(dirpath, name))

    return result


def unzip_submit(zip_file, pwd):
    """ Unzips a zipfile to a temporary directory """
    with TemporaryDirectory() as dirname:
        print('dirname is:', dirname)
        with zipfile.ZipFile(zip_file) as zf:
            logging.info("Extracting zip file to: {0}".format(dirname))
            zf.extractall(path=dirname, pwd=pwd)
            
            files = read_folder(dirname)
            for item in files:
                submit_sample(item)
                time.sleep(float(cfg['importer'].get('delay')))


def process_sample(sample, listing=False, folder=False):
    """ Figure out how to submit a sample """
    sample = []
    if listing:
        logging.info("Importing multiple samples from a list")
        samples = read_file(sample)
        for s in samples:        
            submit_sample(s)
            time.sleep(float(cfg['importer'].get('delay')))
    elif folder:
        logging.info("Importing multiple samples from a folder")
        file_list = read_folder(sample)

        for name in file_list:
            if fnmatch(name, '*.zip'):
                print("Found zip file: {0}".format(name))
                unzip_submit(name, pwd=b'infected')
            else:
                print("Found file: {0}".format(name))
                submit_sample(name)
                time.sleep(float(cfg['importer'].get('delay')))
    else:
        logging.info("Importing a single sample")
        submit_sample(sample) 


def process_domain(domain, listing=False):
    """ Figure out how to submit a domain """
    sample = []
    if listing:
        logging.info("Importing multiple domains from a list")
        samples = read_file(sample)
        for s in samples:        
            submit_domain(s)
            time.sleep(float(cfg['importer'].get('delay')))
    else:
        logging.info("Importing a single domain")
        submit_domain(sample) 


def main():
    """ Main logic for program """
    print("Starting up CRITs_import parsing script!!!")

    # Read configuration file
    global cfg
    cfg = configparser.ConfigParser()
    cfg.read('crits_import.cfg')

    # Set up CLI interface
    args = setup_cli(sys.argv[1:])

    # Set up logging functionality
    logfile = cfg['logging'].get('filename', fallback='crits_import.log')
    level = cfg['logging'].get('level', fallback='INFO').upper()
    logformat = '%(asctime)s %(message)s'
    logging.basicConfig(filename=logfile, level=level, format=logformat)
    print("Writing to log file {0} at level {1}.".format(logfile, level))

    ### Validate configuration
    validate_configuration(args)
    logging.info("Configuration successfully validated")
    print("Configuration successfully validated")

    if arg.type == 'sample':
        process_sample(arg.input, listing=arg.list, folder=arg.folder)
    elif arg.type == 'domain':
        process_domain(arg.input, listing=arg.list)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
