import regex as re
from .exceptions import *
from .scene import *

class HamFile:
    re_instruction = re.compile(r'^\s*!\s*([a-z][a-z0-9]*)(?:\s+([^#]+).*)?$', flags=re.IGNORECASE)
    re_assignment = re.compile(r'\s*([a-zA-Z]\w*)\s*=\s*(.+)\s*$')
    re_line_action = re.compile(r'\s*\[([^\]]*)\]\s*')
    re_speaker_change = re.compile(r'^(.+?)\s*:\s*(.*?)\s*$')
    re_variable = re.compile(r'\$([a-zA-Z]\w*)')
    re_comment = re.compile(r'^\s*#(.*)$')


    def __init__(self, file_name = ''):
        self.file_name = file_name
        self.scenes = [HamFileScene()]


    def append_scene_line(self, name:str) -> HamFileScene:
        scene = HamFileScene(name)
        line = InstructionLine('scene', name)
        self.scenes[-1].lines.append(line)
        return scene

    def get_variable(self, name:str):
        line = self.find_variable_line(name)
        if not line:
            return None

        return line.value()


    def set_variable(self, name:str, value:str):
        line = self.find_variable_line(name)
        if not line:
            line = VariableLine(name, value)
            self.scenes[0].lines.append(line)

        line.value(value)


    def find_variable_line(self, name:str) -> VariableLine:
        for scene in self.scenes:
            for line in scene.lines:
                try:
                    if line.name() == name:
                        return line
                except AttributeError:
                    pass
        return None

    def fill_variables(self, text:str) -> str:
        def sub(match: re.Match[str]) -> str:
            var_name = match.group(1).upper()
            return self.variables[var_name]

        return HamFile.re_variable.sub(sub, str(text))


    def _read_scenes(self, file) -> 'list[HamFileScene]':
        line_number = 0
        file.seek(0)

        current_scene = self.scenes[0]
        del self.scenes[:]

        current_speaker = None
        current_flags = ()

        def add_line(raw_line:str, text: str):
            if not current_speaker:
                raise HamFileError("No speaker", line_number, self.file_name)
            if not current_scene:
                raise HamFileError("No scene", line_number, self.file_name)

            text = text.strip()

            match = HamFile.re_line_action.match(text)
            if match:
                text = text[match.end():]
                action = match.group(1)
            else:
                action = ''

            line = TextLine(current_speaker, text.strip(), current_flags, raw_line)    
            current_scene.lines.append(line)

            if match:
                line.action(action)
        
        for line in file:
            raw_line = line
            line_number += 1

            # Skip comments/blanks
            line = HamFile.re_comment.sub('', line).strip()
            if len(line) == 0:
                continue

            # Variable assignments
            match = HamFile.re_assignment.match(line)
            if match:
                var_name = match.group(1).upper()
                value = match.group(2)
                variable_line = self.find_variable_line(var_name)
                if variable_line:
                    raise HamFileError("Variable already exists", line_number, self.file_name)
                variable_line = VariableLine(var_name, value, raw_line=raw_line)
                current_scene.lines.append(variable_line)
                continue

            # Instructions
            match = HamFile.re_instruction.match(line)
            if match:
                instruction = InstructionLine(match.group(1), match.group(2).strip())
                instruction_name = instruction.instruction()

                if instruction_name == 'FLAG':
                    flag = instruction.text().lower()
                    flag = re.sub( r'\s+', ' ', flag)
                    current_flags += (flag,)

                elif instruction_name == 'UNFLAG':
                    current_flags = ()

                elif instruction_name == 'SCENE':
                    current_speaker = None

                    if current_scene:
                        self.scenes.append(current_scene)
                    current_scene = HamFileScene(match.group(1))
                    current_flags = ()

                current_scene.lines.append(instruction)
                continue

            # Speaker Change
            match = HamFile.re_speaker_change.match(line)
            if match:
                speaker_var = 'VOICE_' + match.group(1).upper()
                current_speaker = self.get_variable(speaker_var)
                if not  current_speaker:
                    current_speaker = match.group(1).lower()

                line = match.group(2)

            add_line(raw_line, line)

        self.scenes.append(current_scene)


def from_file(file_or_name, name:str='') -> 'HamFile':
    if type(file_or_name) == str:
        name = file_or_name

        ham = HamFile(name)
        with open(name, 'r') as file_or_name:
            # ham._read_variables(file_or_name)
            ham._read_scenes(file_or_name)
    else:
        if len(name) == 0:
            raise ValueError("name is required when reading an existing file")

        ham = HamFile(name)
        # ham._read_variables(file_or_name)
        ham._read_scenes(file_or_name)

    return ham