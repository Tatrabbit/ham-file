import regex as re
from .exceptions import *
from ._scene import *


class HamFile:
    re_instruction = re.compile(
        r"^!\s*([a-z_][a-z_0-9]*)(?:\s+([^#]+).*)?$", flags=re.IGNORECASE
    )
    re_processor = re.compile(
        r"^%\s*([a-z_][a-z_0-9]*)(?:\s+([^#]+).*)?$", flags=re.IGNORECASE
    )
    re_assignment = re.compile(r"\s*([a-zA-Z_]\w*)\s*=\s*(.+)\s*$")
    re_line_action = re.compile(r"\s*\[([^\]]*)\]\s*")
    re_speaker_change = re.compile(r"^(.+?)\s*:\s*(.*?)\s*$")
    re_variable = re.compile(r"(?<!\\)(?:\$([_a-z]\w*))", flags=re.IGNORECASE)
    re_comment = re.compile(r"^\s*#(.*)$")
    re_scene = re.compile(r"\s*==\s*(.+?)\s*==\s*$")
    re_continuation = re.compile(r"^\+\s*(.*)$")

    def __init__(self, file_name=""):
        self.file_name = file_name
        self.scenes = [HamFileScene()]

    def __str__(self) -> str:
        text = []

        for scene in self.scenes:
            for line in scene.lines:
                text.append(str(line))
        return "\n".join(text)

    def variables(self):
        for scene in self.scenes:
            yield from scene.variables()

    def lines(self):
        for scene in self.scenes:
            for line in scene.lines:
                yield line

    def get_scene_by_name(self, name: str) -> HamFileScene:
        for scene in self.scenes:
            if not scene.name:
                continue
            if scene.name.casefold() == name.casefold():
                return scene

    def to_dict(self):
        obj = {}

        obj["scenes"] = []
        for scene in self.scenes:
            scene_dict = scene.to_dict(self, include_comments=False)
            if len(scene_dict["lines"]) == 0:
                continue
            obj["scenes"].append(scene_dict)

        variables = []
        for scene in self.scenes:
            for variable in scene.variables():
                name = variable.name()

                is_local = name.startswith("_")
                if is_local:
                    continue

                value = self.fill_variables(variable.text(), scene, recurse=True)

                var = {
                    "name": name,
                    "value": value,
                }
                variables.append(var)
        obj["variables"] = variables

        # obj["variables"] = [v.to_dict(self) for v in self.variables()]
        return obj

    def append_scene_line(self, name: str) -> HamFileScene:
        scene = HamFileScene(name)
        line = InstructionLine("scene", name)
        self.scenes[-1].lines.append(line)
        return scene

    def get_variable(self, name: str, scene=None) -> str | None:
        line = self.find_variable_line(name, scene)
        if not line:
            return None
        return line.value()

    def set_variable(self, name: str, value: str, scene=None):
        line = self.find_variable_line(name, scene)
        if not line:
            line = VariableLine(f"{name} = {value}", name, value)
            if not scene:
                scene = self.scenes[0]
                scene.lines.append(line)
            return

        line.value(value)

    def get_scene(self, line: LineBase):
        for scene in self.scenes:
            if line in scene.lines:
                return scene
        return None

    def find_variable_line(
        self, name: str, preferred_scene: HamFileScene = None
    ) -> VariableLine:
        name = name.upper()

        def find_in(scene: HamFileScene):
            for line in scene.lines:
                if line.kind != "variable":
                    continue
                if line.name() == name:
                    return line

        if name.startswith("_"):
            return find_in(preferred_scene) if preferred_scene else None

        for scene in self.scenes:
            found = find_in(scene)
            if found:
                return found

        return None

    def fill_variables(
        self, text: str, local_scene: HamFileScene = None, recurse: bool = True
    ) -> str:
        def sub(match: re.Match[str]) -> str:
            name = match.group(1)
            variable_line = self.find_variable_line(name, local_scene)
            if not variable_line:
                return name
            variable_scene = self.get_scene(variable_line)
            value = variable_line.text()
            if recurse:
                value = self.fill_variables(
                    variable_line.text(), variable_scene, recurse=True
                )
            return value

        text = self.re_variable.sub(sub, str(text))
        return text.replace("\\$", "$")

        # self.find_variable_line()
        # if recurse:
        #     old_text = None
        #     while old_text != text:
        #         old_text = text
        #         text = self.fill_variables(text, local_scene=local_scene, recurse=False)
        #     return text

        # def sub(match: re.Match[str]) -> str:
        #     return self.get_variable(match.group(1), local_scene)

        # text = HamFile.re_variable.sub(sub, str(text))
        # return text.replace("\\$", "$")

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
        current_speech_time = None
        current_speech_duration = None
        current_speech_padding = None

        def add_line(raw_line: str, text: str):
            if not current_speaker:
                raise HamFileError("No speaker", line_number, self.file_name)
            if not current_scene:
                raise HamFileError("No scene", line_number, self.file_name)

            text = text.strip()

            match = HamFile.re_line_action.match(text)
            if match:
                text = text[match.end() :]
                action = match.group(1)
            else:
                action = ""

            line = TextLine(raw_line, current_speaker, text.strip())
            line.time = current_speech_time
            line.padding = current_speech_padding
            line.duration = current_speech_duration
            line.original_line_number = line_number

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
                comment_line.original_line_number = line_number
                current_scene.lines.append(comment_line)
                continue

            if len(line) == 0:
                blank_line = CommentLine("", None)
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
                    raise HamFileError(
                        "Variable already exists", line_number, self.file_name
                    )
                variable_line = VariableLine(raw_line, var_name, value)
                variable_line.original_line_number = line_number
                current_scene.lines.append(variable_line)
                continue

            match = HamFile.re_scene.match(line)
            if match:
                current_speaker = None

                if current_scene:
                    self.scenes.append(current_scene)

                name = match.group(1)
                current_scene = HamFileScene(name.casefold())

                processor_line = ProcessorLine(raw_line, "scene", name)
                processor_line.original_line_number = line_number
                current_scene.lines.append(processor_line)
                continue

            match = HamFile.re_processor.match(line)
            if match:
                name = match.group(1)
                text = match.group(2)
                processor_line = ProcessorLine(raw_line, name, text)
                processor_line.original_line_number = line_number
                current_scene.lines.append(processor_line)

                name = name.casefold()
                text = text.casefold()
                if name == "t":

                    def read_splits():
                        splits = text.split(":")
                        try:
                            time = float(splits[0])
                            return (time,) + tuple(
                                float(t) for t in splits[1].split(",")
                            )
                        except ValueError:
                            raise HamFileError(
                                "Expected float for speech time, got '%s'" % text,
                                line_number,
                                self.file_name,
                            )

                    (
                        current_speech_time,
                        current_speech_duration,
                        current_speech_padding,
                    ) = read_splits()
                continue

            # Instructions
            match = HamFile.re_instruction.match(line)
            if match:
                instruction_text = match.group(2)
                if not instruction_text:
                    instruction_text = ""

                instruction = InstructionLine(
                    raw_line, match.group(1), instruction_text.strip()
                )
                instruction.original_line_number = line_number
                instruction.time = current_speech_time

                instruction_name = instruction.instruction()

                if instruction_name == "SCENE":
                    raise HamFileError(
                        "'!SCENE foo' is not supported! use '== foo =='\n"
                    )

                elif instruction_name == "SPEECHTIME":
                    try:
                        val = instruction.text().split(":")[0]
                        current_speech_time = float(val)
                    except ValueError:
                        raise HamFileError(
                            "Expected float for SPEECHTIME, got '%s'"
                            % instruction.text(),
                            line_number,
                            self.file_name,
                        )

                current_scene.lines.append(instruction)
                continue

            # Continuation
            match = HamFile.re_continuation.match(line)
            if match:
                try:
                    last_line = current_scene.lines[-1]
                except IndexError:
                    raise HamFileError("No line to continue")

                last_line.text(last_line.text() + "\n" + match.group(1))
                continue

            # Speaker Change
            match = HamFile.re_speaker_change.match(line)
            if match:
                speaker_var = "VOICE_" + match.group(1).upper().replace(" ", "_")
                current_speaker = self.get_variable(speaker_var)
                if not current_speaker:
                    current_speaker = match.group(1).lower()

                line = match.group(2)

            add_line(raw_line, line)

        self.scenes.append(current_scene)

    def find_line_scene(self, line: "LineBase") -> "HamFileScene":
        for scene in self.scenes:
            for scene_line in scene.lines:
                if line is scene_line:
                    return scene


def from_file(file_or_name, name: str = "") -> "HamFile":
    if type(file_or_name) == str:
        name = file_or_name

        ham = HamFile(name)
        with open(name, "r") as file_or_name:
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
