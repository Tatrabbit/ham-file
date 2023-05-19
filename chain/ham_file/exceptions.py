class HamFileError(Exception):
    def __init__(self, msg:str, line:int):
        self.msg = msg
        self.line = line

    def __str__(self) -> str:
        return "Syntax error: %s on line %s\n" % (self.msg, self.line)