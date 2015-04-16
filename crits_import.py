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
    parser.add_argument('-f', '--folder', action='store_true', dest='folder', default=False, help='Treat arguements as a folder.')

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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
