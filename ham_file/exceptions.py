class HamFileError(Exception):
    def __init__(self, msg:str, line:int, file_name:str):
        self.msg = msg
        self.line = line
        self.file = file_name

    def __str__(self) -> str:
        return "Syntax error: %s on line %s (%s)\n" % (self.msg, self.line, self.file)