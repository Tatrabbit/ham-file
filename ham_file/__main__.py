from __init__ import *
from exceptions import *
from ham_file import *

def unit_test():
    try:
        # file = ham_file.from_file('test.ham')

        # for scene in file.scenes:
        #     print(scene)
        #     for line in scene.lines:
        #         print(line)

        ham = HamFile("Reindeer Games")
        scene = HamFileScene('1')
        print(scene)

        line = TextLine("chalmers", "Well, Seymore, I made it.")
        line.line_comment("Fuck this job.")
        print(line.raw())

    except HamFileError as e:
        print(e)
        exit(1)

if __name__ == '__main__':
    unit_test()