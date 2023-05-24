class HamFileScene:
    def __init__(self, name):
        self.name = name
        self.lines = []

    def __str__(self) -> str:
        return "Scene " + self.name

class HamFileLine:
    def __init__(self, speaker:str, text:str, flags:tuple[str]):
        self.speaker = speaker
        self.text = text
        self.flags = flags

    def __str__(self) -> str:
        return self.text