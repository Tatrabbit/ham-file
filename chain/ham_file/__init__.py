import regex as re
from .exceptions import *
from .scene import *

class HamFile:
    re_assignment = re.compile(r'([a-zA-Z]\w*)\s*=\s*(.+)\s*$')
    re_scene_change = re.compile(r'scene\s+(.+)$', flags=re.IGNORECASE)
    re_speaker_change = re.compile(r'^(.+?)\s*:\s*(.*?)\s*$')
    re_variable = re.compile(r'\$([a-zA-Z]\w*)')
    re_comment = re.compile(r'#(.*)$')

    def __init__(self, file):
        if type(file) == str:
            with open(file, 'r') as in_file:
                self._read_from(in_file)
        else:
            self._read_from(file)

    def fill_variables(self, text:str) -> str:
        def sub(match: re.Match[str]) -> str:
            var_name = match.group(1).upper()
            return self.variables[var_name]

        return HamFile.re_variable.sub(sub, str(text))

    def _read_from(self, file):        
        self.variables = HamFile._read_variables(file)
        self.scenes = self._read_scenes(file)

    @staticmethod
    def _read_variables(file) -> dict[str:str]:
        variables = {}

        line_number = 0
        file.seek(0)
        for line in file:
            line_number += 1

            # Ignore Comments
            line = HamFile.re_comment.sub('', line).strip()

            match = HamFile.re_assignment.match(line)
            if match:
                var_name = match.group(1).upper()
                value = match.group(2)
                if var_name in variables:
                    raise HamFileError("Variable already exists", line_number)
                variables[var_name] = value

        return variables
    
    def _read_scenes(self, file) -> list[HamFileScene]:
        scenes = []

        line_number = 0
        file.seek(0)

        current_scene = None
        current_speaker = None
        text = ""

        def add_line(text: str):
            if not current_speaker:
                raise HamFileError("No speaker", line_number)
            if not current_scene:
                raise HamFileError("No scene", line_number)

            line = HamFileLine(current_speaker, text.strip())
            current_scene.lines.append(line)
        
        for line in file:
            line_number += 1

            # Skip comments/blanks
            line = HamFile.re_comment.sub('', line).strip()
            if len(line) == 0:
                continue

            # Skip assignments
            if HamFile.re_assignment.match(line):
                continue

            # Scene Change
            match = HamFile.re_scene_change.match(line)
            if match:
                if text:
                    add_line(text)
                    text = ""

                current_speaker = None
            
                if current_scene:
                    scenes.append(current_scene)
                current_scene = HamFileScene(match.group(1))
                continue

            # Speaker Change
            match = HamFile.re_speaker_change.match(line)
            if match:
                speaker_var = 'VOICE_' + match.group(1).upper()
                try:
                    next_speaker = self.variables[speaker_var]
                except KeyError:
                    next_speaker = match.group(1).lower()

                line = match.group(2)

                if next_speaker == current_speaker:
                    text += " " + line
                elif current_speaker:
                    add_line(text)
                    text = ""

                current_speaker = next_speaker

            text += " " + line

        if text:
            add_line(text)

        return scenes