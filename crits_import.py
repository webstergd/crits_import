#!/usr/bin/env python3

import argparse
import configparser
import logging
import requests
import time
import sys

def setup_cli(args, cfg):
    """ Configure command-line arguements """

    description ="""
    CRITs_import helps with importing sets of information into a CRITs instance."""

    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-d', '--domain', action='store', dest='domain', type=str, help='Domain to import.')
    parser.add_argument('-s', '--sample', action='store', dest='sample', type=str, help='Sample to import.')
    parser.add_argument('-l', '--list', action='store_true', dest='list', default=False, help='Treat arguements as a file of CSVs.')
    #parser.add_argument('-f', '--folder', action='store_true', dest='folder', default=False, help='Treat arguements as a folder.')

    return parser.parse_args(args)


def validate_configuration(args, cfg):
    """ Validate configuration options """
    if not args.domain and not args.sample:
        print("Must supply a domain (-d) or sample (-f) arguement.")
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


def submit_domain(domain, cfg):
    """ Submit domain to CRITs """
    url_tag = urlparse(domain)
    headers = {'User-agent': 'crits_import'}
    url = "{0}/api/v1/domains/".format(cfg['crits'].get('url')) 
    params = {
        'api_key': cfg['crits'].get('key'),
        'username': cfg['crits'].get('user'),
        'source': cfg['crits'].get('source'),
        'domain': url_tag.netloc
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


def submit_sample(sample, cfg):
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
        # Note that this request does NOT go through proxies
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
    result = []
    with open(file_name) as infile:
        for line in infile:
            result.extend([x.strip() for x in line.split(',')])

    return result


def main():
    """ Main logic for program """
    print("Starting up CRITs_import parsing script!!!")

    # Read configuration file
    cfg = configparser.ConfigParser()
    cfg.read('crits_import.cfg')

    # Set up CLI interface
    args = setup_cli(sys.argv[1:], cfg)

    # Set up logging functionality
    logfile = cfg['logging'].get('filename', fallback='crits_import.log')
    level = cfg['logging'].get('level', fallback='INFO').upper()
    logformat = '%(asctime)s %(message)s'
    logging.basicConfig(filename=logfile, level=level, format=logformat)
    print("Writing to log file {0} at level {1}.".format(logfile, level))

    ### Validate configuration
    validate_configuration(args, cfg)
    logging.info("Configuration successfully validated")
    print("Configuration successfully validated")

    ### Attempt to submit domain(s)
    if args.domain:
        domain = []
        if args.list:
            logging.info("Importing single domain")
            domain = read_file(args.domain)
        else:
            logging.info("Importing multiple domains")
            domain.extend(args.domain)

        for d in domain:
            submit_domain(domain, cfg)

    ### Attempt to submit sample(s)
    if args.sample:
        sample = []
        if args.list:
            logging.info("Importing single sample")
            sample = read_file(args.sample)
        else:
            logging.info("Importing multiple samples")
            sample.extend(args.sample)

        for s in sample:
            submit_sample(s, cfg)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
