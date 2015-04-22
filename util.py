import os
import argparse

def read_file(file_name):
    result = set()
    with open(file_name) as infile:
        for line in infile:
            result.add(line.split()[-1])

    return result


def write_file(file_name, elements):
    with open(file_name, 'w', newline='') as f:
        for element in elements:
            print(element, file=f)


def main():
    """ Main logic for program """
    print("Starting up CRITs_import utility script!!!")

    parser = argparse.ArgumentParser()
    parse.add_argument('filename')
    args = parser.parse_args()

    result = read_file(filename)
    write_file(os.path.join(filename, '.parsed'), result)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
