import regex as re

class HamFileScene:
    def __init__(self, name=None):
        self.name = name
        self.lines = []

    def __str__(self) -> str:
        if not self.name:
            return "Blank Scene"
        return "Scene " + self.name
    
    def contains_flag(self, flag):
        for line in self.lines:
            if flag in line.flags:
                return True
        return False
    
    def unique_flags(self) -> 'set[str]':
        all = []
        for line in self.lines:
            all += line.flags
        return set(all)


class LineBase:
    re_line_comment = re.compile(r'#(.*)$')

    def __init__(self, line:str=None):
        if line:
            line = line.rstrip()
            self._raw_line = line

            def get_comment(line:str) -> str:
                match = LineBase.re_line_comment.search(line)
                if not match:
                    return None
                return match.groups()[0].strip()

            self._line_comment = get_comment(line)
        else:
            self._line_comment = None
            self._on_change()

    def raw(self) -> str:
        if self._line_comment:
            return '%s #%s' % (self._raw_line, self._line_comment)
        return self._raw_line
    
    def pretty_print(self) -> str:
        return self.raw()

    def line_comment(self, value:str=None) -> str:
        if value:
            self._line_comment = " " + value.strip()
            self._on_change()

        if not self._line_comment:
            return ''
        return self._line_comment


class CommentLine (LineBase):
    def __init__(self, text:str):
        self._text = text.rstrip()
        super().__init__(None)


    def text(self, value:str=None) -> str:
        if value:
            self._text = value
            self._on_change()
        return self._text
    

    def _on_change(self):
        self._raw_line = "#%s" % self._text


class InstructionLine (LineBase):
    def __init__(self, instruction:str, text:str):
        self._instruction = instruction.upper().strip()
        self._text = text.strip()

        if self._instruction == 'SCENE':
            self._pretty_spaces = '\n\n'
        elif self._instruction == 'ACTION':
            self._pretty_spaces = '  '
        else:
            self._pretty_spaces = ''

        super().__init__(None)


    def instruction(self, value:str=None) -> str:
        if value:
            self._instruction = value
            self._on_change()
        return self._instruction

    
    def text(self, value:str=None) -> str:
        if value:
            self._text = value
            self._on_change()
        return self._text
    

    def pretty_print(self) -> str:
        return self._pretty_spaces + self.raw()
    
    
    def _on_change(self):
        self._raw_line = "!%s %s" % (self._instruction, self._text)
    

class VariableLine (LineBase):
    def __init__(self, name:str, value:str, raw_line:str = None):
        self._name = name.strip().upper()
        self._value = value.strip()

        super().__init__(raw_line)


    def name(self, value:str=None) -> str:
        if value:
            self._name = value
            self._on_change()
    
        return self._name
    
    def value(self, new_value:str=None) -> str:
        if new_value:
            self._value = new_value
            self._on_change()
    
        return self._value


    def _on_change(self):
        self._raw_line = "%s = %s" % (self._name, self._value)


    def __str__(self) -> str:
        return "%s = %s" % (self._name, self._value)


class TextLine (LineBase):
    def __init__(self, speaker:str, text:str, flags:'tuple[str]'=(), raw_line:str = None):
        self._speaker = speaker.strip()
        self._text = text.strip()
        self.flags = flags
        self._action = ''

        if not raw_line:
            raw_line = "%s: %s" % (self._speaker.capitalize(), self._text)

        super().__init__(raw_line)

    def speaker(self, value:str=None) -> str:
        if value:
            self._speaker = value
            self._on_change()
        return self._speaker

    def text(self, value:str=None) -> str:
        if value:
            self._text = value
            self._on_change()
        return self._text
    
    def action(self, value:str=None) -> str:
        if value:
            self._action = value
            self._on_change()
        return self._action

    def _on_change(self):
        if len(self._action) > 0:
            action = ' [%s]' % self._action
        else:
            action = ''
    
        self._raw_line = "%s:%s %s" % (self._speaker.capitalize(), action, self._text)

    def __str__(self) -> str:
        return "%s: %s" % (self._speaker.capitalize(), self._text)