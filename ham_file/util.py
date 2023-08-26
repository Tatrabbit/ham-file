import sys
import argparse
import regex as re


def add_ham_inputs(parser:argparse.ArgumentParser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help="a .ham file to read")
    group.add_argument('--stdin', action='store_true', help="read .ham from stdin")

    return group


def add_ham_outputs(parser:argparse.ArgumentParser, required:bool=False):
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument('-o', '--out-file', help="file to write output ham to")
    group.add_argument('--stdout', action='store_true', help="write output ham to stdout")

    return group


def get_ham_file(args:argparse.Namespace):
    if args.file:
        return args.file, None
    else:
        return sys.stdin, "stdin"


def get_hamfile_base(ham_filename:str) -> 'tuple[str,int]':
    match = re.match(r'(.+?)(?:\.([0-9]+))?\.ham$', ham_filename, re.IGNORECASE)
    if match:
        try:
            index = int(match.group(2))
        except TypeError:
            index = None
        return match.group(1), index
    else:
        return ham_filename, None


def write_out(args:argparse.Namespace, ham):
    if args.out_file:
        with open(args.out_file, 'w') as out_file:
            out_file.write(str(ham))
        return True
    elif args.stdout:
        sys.stdout.write(str(ham))
        return True

    return False