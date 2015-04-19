#!/usr/bin/env python3

import argparse
import configparser
import hashlib
import logging
import magic
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
    parser.add_argument('input', type=str, help='File or directory name')

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


def submit_sample(sample_path):
    """ Submit sample to CRITs """
    print("Submitting sample {0} to CRITs".format(sample_path))

    headers = {'User-agent': 'crits_import'}
    url = "{0}/api/v1/samples/".format(cfg['crits'].get('url'))
    zipfiles = ['application/zip', 'application/gzip', 'application/x-7z-compressed']
    rarfiles = ['application/x-rar-compressed']
    blacklist = cfg['importer'].get('blacklist', '').strip().split(',')

    # Read in file
    with open(sample_path, 'rb') as fp:
        sample = fp.read()

        # Hash and type
        md5 = hashlib.md5(sample).hexdigest()
        files = {'filedata': (md5, sample)}
        mimetype = magic.from_buffer(sample, mime=True)

        if not mimetype in blacklist:
            if mimetype in zipfiles:
                filetype = 'zip'
            elif mimetype in rarfiles:
                filetype = 'rar'
            else:
                filetype = 'raw'

            params = {
                'api_key': cfg['crits'].get('key'),
                'username': cfg['crits'].get('user'),
                'source': cfg['crits'].get('source'),
                'upload_type': 'file',
                'md5': md5,
                'file_format': filetype  # must be type zip, rar, or raw
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
    # could read the file compressed but I wanted to play it safe
    # you can also submit zips directly to CRITs but some of these zips are huge
    # so this is just to make it a little easier on the CRITs server. 
    with TemporaryDirectory() as dirname:
        print('Writing to temp directory:', dirname)
        with zipfile.ZipFile(zip_file) as zf:
            logging.info("Extracting zip file to: {0}".format(dirname))
            zf.extractall(path=dirname, pwd=pwd)
            
            files = read_folder(dirname)
            for item in files:
                submit_sample(item)
                time.sleep(float(cfg['importer'].get('delay')))


def process_sample(sample, listing=False, folder=False):
    """ Figure out how to submit a sample """
    samples = []
    print("Processing: {0}".format(sample))
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
    domains = []
    print("Processing: {0}".format(domain))
    if listing:
        logging.info("Importing multiple domains from a list")
        domains = read_file(domain)
        for s in domains:        
            submit_domain(s)
            time.sleep(float(cfg['importer'].get('delay')))
    else:
        logging.info("Importing a single domain")
        submit_domain(domain) 


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

    if args.type == 'sample':
        process_sample(args.input, listing=args.list, folder=args.folder)
    elif args.type == 'domain':
        process_domain(args.input, listing=args.list)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
