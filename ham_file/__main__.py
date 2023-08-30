import sys

from __init__ import *
from exceptions import *
from ham_file import *
from ham_file.exceptions import *

def _unit_test():
    try:
        file = from_file(sys.argv[1])

        for scene in file.scenes:
            print(scene)
            for line in scene.lines:
                print(line)

        # ham = HamFile("Reindeer Games")
        # scene = HamFileScene('1')
        # print(scene)

        # line = TextLine("chalmers", "Well, Seymore, I made it.")
        # line.line_comment("Fuck this job.")
        # print(line.raw())

    except HamFileError as e:
        print(e)
        exit(1)

if __name__ == '__main__':
    _unit_test()