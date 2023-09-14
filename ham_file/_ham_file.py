import regex as re
from .exceptions import *
from ._scene import *

class HamFile:
    re_instruction = re.compile(r'^!\s*([a-z_][a-z_0-9]*)(?:\s+([^#]+).*)?$', flags=re.IGNORECASE)
    re_assignment = re.compile(r'\s*([a-zA-Z_]\w*)\s*=\s*(.+)\s*$')
    re_line_action = re.compile(r'\s*\[([^\]]*)\]\s*')
    re_speaker_change = re.compile(r'^(.+?)\s*:\s*(.*?)\s*$')
    re_variable = re.compile(r'\$([a-zA-Z]\w*)')
    re_comment = re.compile(r'^\s*#(.*)$')
    re_continuation = re.compile(r'^\+\s*(.*)$')


    def __init__(self, file_name = ''):
        self.file_name = file_name
        self.scenes = [HamFileScene()]

    
    def __str__(self) -> str:
        text = []

        for scene in self.scenes:
            for line in scene.lines:
                text.append(str(line))
        return '\n'.join(text)
    

    def variables(self):
        for scene in self.scenes:
            yield from scene.variables()


    def lines(self):
        for scene in self.scenes:
            for line in scene.lines:
                yield line


    def to_dict(self):
        obj = {}

        obj['scenes'] = []
        for scene in self.scenes:
            scene_dict = scene.to_dict(self)
            if len(scene_dict['lines']) == 0:
                continue
            obj['scenes'].append(scene_dict)

        obj['variables'] = [v.to_dict(self) for v in self.variables()]
        return obj


    def append_scene_line(self, name:str) -> HamFileScene:
        scene = HamFileScene(name)
        line = InstructionLine('scene', name)
        self.scenes[-1].lines.append(line)
        return scene


    def get_variable(self, name:str) -> str:
        line = self.find_variable_line(name)
        if not line:
            return None
        return line.value()


    def set_variable(self, name:str, value:str):
        line = self.find_variable_line(name)
        if not line:
            line = VariableLine(f'{name} = {value}', name, value)
            self.scenes[0].lines.append(line)
            return

        line.value(value)


    def get_scene(self, line:LineBase):
        for scene in self.scenes:
            if line in scene.lines:
                return scene
        return None


    def find_variable_line(self, name:str) -> VariableLine:
        name = name.upper()

        for scene in self.scenes:
            for line in scene.lines:
                if not type(line) is VariableLine:
                    continue
                if line.name() == name:
                    return line
        return None

    
    def fill_variables(self, text:str) -> str:
        def sub(match: re.Match[str]) -> str:
            var_name = match.group(1).upper()
            return self.get_variable(var_name)

    def parse_instruction_args(self, text: str) -> dict[str, str]:
        """
        Parse a foo="bar baz" style text.

        The format is comma separated, key = value, with optional quotes on value.
        Keys are stored casefolded in the dict. spaces to the left and right of a value
        are stripped, and if the optional quotes are present, they are removed. Leading
        or trailing whitespace, if desired, can be protected by the use of these quotes.

        Values have $constant replacement performed.

        Examples:
        lines = 1, only = $TOM, action = "to himself, in the kitchen"
        action=opening the front door, first=$TOM
        """

        def parse_name(start: int) -> tuple[str, int]:
            name = ""
            for i in range(start, len(text)):
                if text[i] == "=":
                    return name.casefold().strip(), i + 1
                name += text[i]

            raise ValueError(f"Unable to parse Key Values: ({text})")

        def parse_value(start: int) -> tuple[str, int]:
            value, idx = _read_string(text, start)
            value = self.fill_variables(value)
            return (value, idx)

        # Fill dictionary, check unique
        args: dict[str, str] = {}
        i = 0
        while i < len(text):
            name, i = parse_name(i)
            if not name:
                break
            value, i = parse_value(i)

            try:
                i = _advance_spaces(text, i)
                i = text.index(",", i)
            except ValueError:  # End of text
                i = len(text)

            i += 1

            if name in args:
                raise ValueError(f'Duplicate key "{name}" in Key Values: ({text})')
            args[name] = value

        return args

    def _read_scenes(self, file) -> "list[HamFileScene]":
        line_number = 0

        current_scene = self.scenes[0]
        del self.scenes[:]

        current_speaker = None
        current_flags = ()
        current_speech_time = None

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

            line = TextLine(raw_line, current_speaker, text.strip(), current_flags)
            line.time = current_speech_time

            current_scene.lines.append(line)

            if match:
                line.action(action)
        
        for line in file:
            raw_line = line
            line = line.strip()
            line_number += 1

            # Strip Comments
            match = HamFile.re_comment.match(line)
            if match:
                comment_line = CommentLine(raw_line, match.group(1))
                comment_line.time = current_speech_time
                current_scene.lines.append(comment_line)
                continue

            if len(line) == 0:
                blank_line = CommentLine('', None)
                blank_line.original_line_number = line_number
                current_scene.lines.append(blank_line)
                continue

            # Variable assignments
            match = HamFile.re_assignment.match(line)
            if match:
                var_name = match.group(1).upper()
                value = match.group(2)
                variable_line = self.find_variable_line(var_name)
                if variable_line:
                    raise HamFileError("Variable already exists", line_number, self.file_name)
                variable_line = VariableLine(raw_line, var_name, value)
                variable_line.original_line_number = line_number
                current_scene.lines.append(variable_line)
                continue

            # Instructions
            match = HamFile.re_instruction.match(line)
            if match:
                instruction_text = match.group(2)
                if not instruction_text:
                    instruction_text = ''

                instruction = InstructionLine(raw_line, match.group(1), instruction_text.strip())
                instruction.original_line_number = line_number
                instruction.time = current_speech_time

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
                    current_scene = HamFileScene(instruction.text())
                    current_flags = ()

                elif instruction_name == 'SPEECHTIME':
                    try:
                        current_speech_time = float(instruction.text())
                    except ValueError:
                        raise HamFileError("Expected float for SPEECHTIME, got '%s'" % instruction.text(), line_number, self.file_name)

                current_scene.lines.append(instruction)
                continue

            # Continuation
            match = HamFile.re_continuation.match(line)
            if match:
                try:
                    last_line = current_scene.lines[-1]
                except IndexError:
                    raise HamFileError("No line to continue")
                
                last_line.text(last_line.text() + '\n' + match.group(1))
                continue

            # Speaker Change
            match = HamFile.re_speaker_change.match(line)
            if match:
                speaker_var = 'VOICE_' + match.group(1).upper()
                current_speaker = self.get_variable(speaker_var)
                if not current_speaker:
                    current_speaker = match.group(1).lower()

                line = match.group(2)

            add_line(raw_line, line)

        self.scenes.append(current_scene)


def from_file(file_or_name, name:str='') -> 'HamFile':
    if type(file_or_name) == str:
        name = file_or_name

        ham = HamFile(name)
        with open(name, 'r') as file_or_name:
            ham._read_scenes(file_or_name)
    else:
        if len(name) == 0:
            raise ValueError("name is required when reading an existing file")

        ham = HamFile(name)
        ham._read_scenes(file_or_name)

    return ham


def _read_string(text: str, start: int = 0) -> tuple[str, int]:
    if start >= len(text):
        raise ValueError()

    idx = _advance_spaces(text, start)

    # Determine quote style
    quote_style = text[idx]
    if quote_style not in "\"'":
        quote_style = None

    if quote_style:
        return _read_quote_string(text, idx + 1, quote_style)
    else:
        return _read_easy_string(text, idx)


def _advance_spaces(text: str, start: int) -> int:
    match = re.search(r"\S", text, pos=start)
    if not match:
        raise ValueError()
    return match.start()


def _read_quote_string(text: str, start: int, quote_style: str) -> tuple[str, int]:
    idx = start
    value = ""

    # Read until close quotes
    while idx < len(text):
        next = text[idx]

        if next == "\\":
            try:
                next = text[idx + 1]
            except IndexError:
                raise ValueError("Trailing \\")
            # Re-escape $, for variable replacements
            if quote_style == '"' and next == "$":
                next = "\\$"

            value += next
            idx += 2
            continue

        # Auto-escape $ in single quotes
        if quote_style == "'" and next == "$":
            next = "\\$"

        idx += 1

        if next == quote_style:
            return value, idx
        value += next


def _read_easy_string(text: str, start: int, terminators: str = ",") -> tuple[str, int]:
    idx = start
    value = ""

    # Read until ,
    while idx < len(text):
        next = text[idx]

        if next in terminators:
            return value, idx

        idx += 1
        value += next

    return value, idx
