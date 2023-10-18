import regex as re


class HamFileScene:
    def __init__(self, name=None):
        self.name = name
        self.lines = []

    def __str__(self) -> str:
        if not self.name:
            return "Blank Scene"
        return "Scene " + self.name

    def variables(self):
        for line in self.lines:
            if type(line) is VariableLine:
                yield line

    def to_dict(self, ham, include_comments: True) -> dict:
        def is_included(line: LineBase):
            if line.exclude_from_json_lines():
                return False

            if include_comments:
                return True
            else:
                return line.kind != "comment"

        return {
            "name": self.name,
            "lines": [l.to_dict(ham, self) for l in self.lines if is_included(l)],
        }


class LineBase:
    re_line_comment = re.compile(r"#(.*)$")
    time = 0.0
    original_line_number = -1

    def __init__(self, raw_line: str):
        self._line_comment = self._parse_line_comment(raw_line)

    def raw(self) -> str:
        raw = self._raw().split("\n")
        raw = "\n+   ".join(raw)

        if self._line_comment:
            return "%s #%s" % (raw, self._line_comment)

        return raw

    def line_comment(self, value: str = None) -> str:
        if value:
            self._line_comment = value.rstrip()

        return self._line_comment or ""

    def to_dict(self, ham, scene) -> "dict":
        return {
            "kind": self.kind,
            "name": self.name(),
            "text": ham.fill_variables(self.text(), scene, True),
            # "text": self.text(),
            "time": self.time or 0.0,
            "line_number": self.original_line_number,
        }

    def exclude_from_json_lines(self):
        return False

    def _parse_line_comment(self, line: str) -> str:
        if not line:
            return

        line = line.rstrip()
        match = LineBase.re_line_comment.search(line)
        if not match:
            return None
        return match.groups()[0].strip()

    def __str__(self) -> str:
        return self.raw()


class CommentLine(LineBase):
    kind = "comment"
    _text = None

    def __init__(self, raw_line: str, text: str):
        super().__init__(raw_line)

        if text != None:
            self._text = text.rstrip()

    def name(self) -> str:
        return "#" if self._text != None else "blank"

    def text(self, value: str = None) -> str:
        if value:
            self._text = value
            self._on_change()
        return self._text

    def _parse_line_comment(self, line: str) -> str:
        # No line comments on comment lines!
        return None

    def _raw(self):
        if self._text is not None:
            return "#%s" % self._text
        else:
            return ""


class PrefixLine(LineBase):
    def __init__(self, raw_line: str, name: str, text: str):
        super().__init__(raw_line)

        self._name = name.strip().upper()
        self._text = text.strip()

    def name(self, value: str = None) -> str:
        if value:
            self._name = value
        return self._name

    def text(self, value: str = None) -> str:
        if value:
            self._text = value
        return self._text


class ProcessorLine(PrefixLine):
    kind = "processor"

    def __init__(self, raw_line: str, name: str, text: str):
        super().__init__(raw_line, name=name, text=text)

    def _raw(self):
        if self._name == "SCENE":
            return f"== {self._text} =="
        else:
            return "%%%s %s" % (self._name, self._text)

    def exclude_from_json_lines(self):
        # If other tools need access to processor lines,
        # it indicates a more fundamental problem.
        # Processor lines are meant to remain internal to
        # the reader.
        return True


class InstructionLine(PrefixLine):
    kind = "instruction"

    def __init__(self, raw_line: str, instruction: str, text: str):
        super().__init__(raw_line, name=instruction, text=text)

    # TODO remove, just use self.name
    def instruction(self, value: str = None) -> str:
        return self.name(value)

    def _raw(self):
        return "!%s %s" % (self._name, self._text)


class VariableLine(LineBase):
    kind = "variable"

    def __init__(self, raw_line: str, name: str, value: str):
        super().__init__(raw_line)

        self._name = name.strip().upper()
        self._value = value.strip()

    def name(self, value: str = None) -> str:
        if value:
            self._name = value

        return self._name

    def text(self, value: str = None) -> str:
        return self.value(value)

    # TODO remove
    def value(self, new_value: str = None) -> str:
        if new_value:
            self._value = new_value

        return self._value

    # def to_dict(self, ham, scene) -> "dict":
    #     return {
    #         "name": self.name(),
    #         "value": ham.fill_variables(self.text(), scene, recurse=True),
    #     }

    def exclude_from_json_lines(self):
        return True
        # return self.name().startswith("_")

    def _raw(self):
        return "%s = %s" % (self._name, self._value)


class TextLine(LineBase):
    kind = "text"

    padding = 0.0
    duration = 0.0

    def __init__(self, raw_line: str, speaker: str, text: str):
        super().__init__(raw_line)

        self._speaker = speaker.strip()
        self._text = text.strip()
        self._action = ""

    # TODO remove, just use self.name
    def speaker(self, value: str = None) -> str:
        if value:
            self._speaker = value
        return self._speaker

    def name(self, value: str = None) -> str:
        return self.speaker(value)

    # TODO return full text, add methods for parsing speech/action
    def text(self, value: str = None) -> str:
        if value:
            self._text = value
        return self._text

    def speech(self, value: str = None) -> str:
        return self.text(value)

    def action(self, value: str = None) -> str:
        if value:
            self._action = value
        return self._action

    def to_dict(self, ham, scene) -> dict:
        d = super().to_dict(ham, scene)
        d["text"] = f"[{self._action}] {self._text}"  # TODO/hack
        # d["action"] = self._action

        d["duration"] = self.duration
        d["padding"] = self.padding
        return d

    def _raw(self):
        speaker = self._speaker.capitalize()

        if self._action:
            return "%s: [%s] %s" % (speaker, self._action, self._text)
        else:
            return "%s: %s" % (speaker, self._text)
