import regex as re
import ham_file as HamFile

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
            if type (line) is VariableLine:
                yield line
    

    def contains_flag(self, flag):
        for line in self.lines:
            if flag in line.flags:
                return True
        return False
    

    def unique_flags(self) -> 'set[str]':
        all = []
        for line in self.lines:
            try:
                all += line.flags
            except AttributeError:
                pass
        return set(all)
    

    def to_dict(self, ham:HamFile) -> dict:
        return {
            'flags': list(self.unique_flags()),
            'lines': [l.to_dict(ham) for l in self.lines if not l.exclude_from_json_lines],
        }


class LineBase:
    re_line_comment = re.compile(r'#(.*)$')

    def __init__(self, raw_line:str):            
        self._line_comment = self._parse_line_comment(raw_line)
        self.time = None

        self.exclude_from_json_lines = False


    def raw(self) -> str:
        raw = self._raw().split('\n')
        raw = '\n+   '.join(raw)

        if self._line_comment:
            return '%s #%s' % raw, self._line_comment()

        return raw


    def pretty_print(self) -> str:
        return self.raw()


    def line_comment(self, value:str=None) -> str:
        if value:
            self._line_comment = value.rstrip()

        return self._line_comment or ''


    def to_dict(self, ham:HamFile) -> 'dict':
        return {
            'kind': self.kind,
            'name': self.name(),
            'text': self.text(),
        }

    
    def _parse_line_comment(self, line:str) -> str:
        if not line:
            return

        line = line.rstrip()
        match = LineBase.re_line_comment.search(line)
        if not match:
            return None
        return match.groups()[0].strip()


    def __str__(self) -> str:
        return self.raw()


class CommentLine (LineBase):
    def __init__(self, raw_line:str, text:str):
        super().__init__(raw_line)
        self.kind = 'comment'

        self._text = text.rstrip()


    def name(self) -> str:
        return '#'


    def text(self, value:str=None) -> str:
        if value:
            self._text = value
            self._on_change()
        return self._text
    

    def _parse_line_comment(self, line:str) -> str:
        # No line comments on comment lines!
        return None


    def _raw(self):
        return "#%s" % self._text


class InstructionLine (LineBase):
    def __init__(self, raw_line:str, instruction:str, text:str):
        super().__init__(raw_line)
        self.kind = 'instruction'

        self._instruction = instruction.upper().strip()
        self._text = text.strip()

        if self._instruction == 'SCENE':
            self._pretty_spaces = '\n\n'
        elif self._instruction == 'ACTION':
            self._pretty_spaces = '  '
        else:
            self._pretty_spaces = ''

    # TODO remove, just use self.name
    def instruction(self, value:str=None) -> str:
        if value:
            self._instruction = value
        return self._instruction
    

    def name(self, value:str=None) -> str:
        return self.instruction(value)

    
    def text(self, value:str=None) -> str:
        if value:
            self._text = value
        return self._text


    def pretty_print(self) -> str:
        return self._pretty_spaces + self.raw()

    
    def _raw(self):
        return "!%s %s" % (self._instruction, self._text)
    

class VariableLine (LineBase):
    def __init__(self, raw_line:str, name:str, value:str):
        super().__init__(raw_line)
        self.kind = 'variable'

        self._name = name.strip().upper()
        self._value = value.strip()

        self.exclude_from_json_lines = True

    def name(self, value:str=None) -> str:
        if value:
            self._name = value
    
        return self._name
    
    def text(self, value:str=None) -> str:
        return self.value(value)

    # TODO remove
    def value(self, new_value:str=None) -> str:
        if new_value:
            self._value = new_value
    
        return self._value
    

    def to_dict(self, ham:HamFile) -> 'dict':
        return {
            'name': self.name(),
            'value': self.text(),
        }


    def _raw(self):
        return "%s = %s" % (self._name, self._value)


class TextLine (LineBase):
    def __init__(self, raw_line:str, speaker:str, text:str, flags:'tuple[str]'=()):
        super().__init__(raw_line)
        self.kind = 'text'

        self._speaker = speaker.strip()
        self._text = text.strip()
        self._action = ''
        self.flags = flags


    # TODO remove, just use self.name
    def speaker(self, value:str=None) -> str:
        if value:
            self._speaker = value
        return self._speaker
    

    def name(self, value:str=None) -> str:
        return self.speaker(value)


    # TODO return full text, add methods for parsing speech/action
    def text(self, value:str=None) -> str:
        if value:
            self._text = value
        return self._text
    

    def action(self, value:str=None) -> str:
        if value:
            self._action = value
        return self._action


    def _raw(self):
        speaker = self._speaker.capitalize()

        if self._action:
            return "%s: [%s] %s" % (speaker, self._action, self._text)
        else:
            return "%s: %s" % (speaker, self._text)