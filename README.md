# crits_import
Tool to import elements into CRITs

Currently supports adding domains and samples via CLI input, newline seperated list, and samples in a folder*. 

* If zip files are present, it will extract the top level zip files to a temporary directory and import them seperatly. This is to reduce server overhead with large sample sets. 

# Install
sudo apt-get install python3-pip
pip3 install python-magic

Then configure crits_import.cfg

# Usage
usage: crits_import.py [-h] [-l] [-f] {domain,sample} input

positional arguments:
  {domain,sample}  Type of element to submit
  input            File or directory name

optional arguments:
  -h, --help       show this help message and exit
  -l, --list       Treat arguements as a file containing a newline seperated
                   list
  -f, --folder     Treat arguements as a folder
