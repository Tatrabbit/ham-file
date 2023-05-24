import regex as re
from .exceptions import *
from .scene import *

class HamFile:
    re_assignment = re.compile(r'([a-zA-Z]\w*)\s*=\s*(.+)\s*$')
    re_scene_change = re.compile(r'scene\s+(.+)$', flags=re.IGNORECASE)
    re_speaker_change = re.compile(r'^(.+?)\s*:\s*(.*?)\s*$')
    re_variable = re.compile(r'\$([a-zA-Z]\w*)')
    re_flag = re.compile(r'^flag\s+(.+)\s*', flags=re.IGNORECASE)
    re_unflag = re.compile(r'^unflag\s+', flags=re.IGNORECASE)
    re_comment = re.compile(r'#(.*)$')

    def __init__(self, file, file_name = ''):
        if type(file) == str:
            self.file_name = file

            with open(file, 'r') as in_file:
                self._read_from(in_file)
        else:
            self.file_name = file_name
            self._read_from(file)

    def fill_variables(self, text:str) -> str:
        def sub(match: re.Match[str]) -> str:
            var_name = match.group(1).upper()
            return self.variables[var_name]

        return HamFile.re_variable.sub(sub, str(text))

    def _read_from(self, file):        
        self.variables = self._read_variables(file)
        self.scenes = self._read_scenes(file)

    def _read_variables(self, file) -> 'dict[str:str]':
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
                    raise HamFileError("Variable already exists", line_number, self.file_name)
                variables[var_name] = value

        return variables
    
    def _read_scenes(self, file) -> 'list[HamFileScene]':
        scenes = []

        line_number = 0
        file.seek(0)

        current_scene = None
        current_speaker = None
        current_flags = ()

        text = ""

        def add_line(text: str):
            if not current_speaker:
                raise HamFileError("No speaker", line_number, self.file_name)
            if not current_scene:
                raise HamFileError("No scene", line_number, self.file_name)

            line = HamFileLine(current_speaker, text.strip(), current_flags)
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

            # Set Flag
            match = HamFile.re_flag.match(line)
            if match:
                flag = match.groups(1)[0]
                current_flags += (flag,)
                continue

            # Clear flags
            if HamFile.re_unflag.match(line):
                current_flags = ()
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
                current_flags = ()
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

        if current_scene:
            scenes.append(current_scene)

        return scenes