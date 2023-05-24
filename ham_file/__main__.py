from __init__ import *
from exceptions import *

def unit_test():
    try:
        file = HamFile('test.ham')

        for scene in file.scenes:
            print(scene)
            for line in scene.lines:
                print(line)
        
    except HamFileError as e:
        print(e)
        exit(1)

if __name__ == '__main__':
    unit_test()