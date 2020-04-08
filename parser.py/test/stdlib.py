import sys, os, re, inspect

def start(filepath, destination, root_function, export_function):
    ### Open source file
    with open(filepath, 'r') as file:
        content = file.read().replace("\t", "    ")

    try:
        ### Convert !
        RELATIVE_INDEXES.append(0)
        ITERATORS.append(None)
        root_function(Argument(content))
        RELATIVE_INDEXES.pop()
        ITERATORS.pop()
        ### Export !
        output = export_function()

    except ParsingException as error:
        ### Error parsing
        (malformed, line_start_index) = line_from_index(content, error.INDEX)
        (line_pos, column_pos) = line_column_position_from_index(content, error.INDEX)
        print("[PARSING ERROR] (line %s, column %s) %s :\n    %s\n    %s^" % (line_pos, column_pos, error.message, malformed, " " * (error.INDEX - line_start_index)))
        sys.exit(-1)

    if output != None:
        ### Export destination file
        with open(os.path.abspath(destination), 'w') as file:
            file.write(output)

#################################
###           STDLIB          ###
#################################

RELATIVE_INDEXES = [] # Stack of integers

ITERATORS = [] # Stack of 'Iterator' objects below

REGEX_DICTIONARY = {} # Dictionary of regex -> compiled regex engines

class ParsingException(Exception):
    def __init__(self, message, index = None, relative = False):
        if index == None:
            index = 0 if ITERATORS[-1] == None else ITERATORS[-1].INDEX
            index = absolute_index(index)
        elif isinstance(index, Argument):
            index = index.INDEX
        elif relative == True:
            index = absolute_index(index)

        self.message = message
        self.INDEX = index

class Argument:
    def __init__(self, value, index = 0):
        self.VALUE = value
        self.INDEX = absolute_index(index)
        self.RELATIVE_INDEX = index

    def __len__(self):
        return len(self.VALUE)

    def __getitem__(self, index):
        return self.VALUE[index]

    def __repr__(self):
        return str(self.VALUE)

    def __add__(self, other):
        return self.VALUE + str(other)

    def __eq__(self, other):
        if other == None:
            return self.VALUE == None
        return self.VALUE == str(other)

    def __ne__(self, other):
        if other == None:
            return self.VALUE != None
        return self.VALUE != str(other)

class Iterator:
    def __init__(self, argument):
        ITERATORS[-1] = self
        self.ARG = argument
        self.INDEX = trim_start(self.ARG, 0)

    def has_remaining(self):
        return self.INDEX < len(self.ARG)

    def __len__(self):
        return len(self.ARG)

    def __getitem__(self, index):
        return self.ARG[index]

    def __repr__(self):
        return str(self.INDEX)

### Converts a relative index into an absolute index
def absolute_index(relative_index):
    for idx in RELATIVE_INDEXES:
        relative_index += idx
    for iterator in ITERATORS:
        if iterator != None:
            relative_index += iterator.ARG.RELATIVE_INDEX
    return relative_index

### Returns the regex engine associated to the given regex
def get_regex_engine(regex):
    regex_engine = REGEX_DICTIONARY.get(regex, None)
    if regex_engine == None:
        regex_engine = re.compile(regex, re.DOTALL)
        REGEX_DICTIONARY[regex] = regex_engine
    return regex_engine

### Attempts to call the given function with the given matched patterns
def bind_patterns(function, result_regex):
    spec = inspect.getargspec(function)
    # Check matched patterns and function signature
    if len(spec.args) != len(result_regex.groups()):
        raise Exception("\nNumber of matched arguments doesn't correspond to arguments of function : \n\t%s\n\t%s\nRegex result :\n\t%s\n\t%s" \
            % (function, spec, result_regex, result_regex.groups()))

    # Conctruct Argument object based on matched patterns
    arguments = []
    i = 1
    (start_index, _) = result_regex.span(0)
    for value in result_regex.groups():
        if value == None:
            arguments.append(None)
        else:
            (start, _) = result_regex.span(i)
            arguments.append(Argument(value, start - start_index))
        i += 1

    # Call the function with matched patterns
    function(*arguments)

###
### Parsing
###

# Parses the given regex, and potentially calls the given function with the matched patterns
def parse(regex, function = None):
    iterator = ITERATORS[-1]
    ### Check regex
    regex_engine = get_regex_engine(regex)
    result_regex = regex_engine.match(iterator.ARG.VALUE, iterator.INDEX)
    if result_regex == None:
        return None
    if function != None:
        # Call function
        RELATIVE_INDEXES.append(iterator.INDEX)
        ITERATORS.append(None)
        bind_patterns(function, result_regex)
        RELATIVE_INDEXES.pop()
        ITERATORS.pop()

    ### Advance index
    (_, start_index) = result_regex.span()

    ### Trim
    iterator.INDEX = trim_start(iterator.ARG, start_index)
    return result_regex

### Resolves the content between the given open/close tokens, and potentially calls the given function with the content
def parse_between(opening_token, closing_token, function = None):
    iterator = ITERATORS[-1]
    offset = 0
    idx = iterator.INDEX

    ### Find first opening token
    while idx < len(iterator):
        char = iterator[idx]
        if char == opening_token[offset]: ### Opening token
            offset += 1
            if offset == len(closing_token):
                break
        else:
            raise ParsingException("Expected opening token %s" % opening_token, idx, True)
        idx += 1 # Next char

    offset = 0
    idx += 1 # Next char
    body_index = idx
    counter = 1

    ### Find matching closing token
    while idx < len(iterator):
        char = iterator[idx]
        if char == opening_token[offset]: ### Opening token
            offset += 1
            if offset == len(closing_token):
                counter += 1 # Increment counter
                offset = 0
        elif char == closing_token[offset]: ### Closing token
            offset += 1
            if offset == len(closing_token):
                counter -= 1 # Decrement counter
                if counter == 0:
                    idx += 1
                    body = iterator.ARG.VALUE[body_index:idx-len(closing_token)]
                    if function != None:
                        # Call function
                        RELATIVE_INDEXES.append(body_index)
                        ITERATORS.append(None)
                        function(Argument(body))
                        RELATIVE_INDEXES.pop()
                        ITERATORS.pop()

                    ### Trim
                    iterator.INDEX = trim_start(iterator.ARG, idx)
                    return body
                offset = 0
        else:
            idx -= offset # Important for reevaluation
            offset = 0
        idx += 1 # Next char

    raise ParsingException("Expected closing token %s" % closing_token, body_index, True)

###
### Utility
###

### Trims the start of the given string, starting from the given index
def trim_start(argument, start_index = 0):
    trim_engine = get_regex_engine("[ \t\n]+")
    result_trim = trim_engine.match(argument.VALUE, start_index)
    if result_trim != None:
        ### Advance index
        (_, start_index) = result_trim.span()
    return start_index

### Replaces all comments with blanks, but preserves comments between given open/close tokens
def blank_comments(argument, comment_token = "//", opening_token = None, closing_token = None):
    counter = 0
    offset1 = 0
    offset2 = 0
    offset3 = 0
    idx = 0
    dump = False
    dump_index = 0

    while idx < len(argument):
        char = argument.VALUE[idx]
        if dump == True:
            if char == '\n':
                dump = False
                argument.VALUE = argument.VALUE[:dump_index] + " " * (idx - dump_index) + argument.VALUE[idx:]
        else:
            if offset3 == 0:
                if opening_token != None and char == opening_token[offset1]: ### Opening token
                    offset1 += 1
                    if offset1 == len(closing_token):
                        counter += 1 # Increment counter
                        offset1 = 0
                elif closing_token != None and char == closing_token[offset2]: ### Closing token
                    offset2 += 1
                    if offset2 == len(closing_token):
                        counter -= 1 # Decrement counter
                        offset2 = 0
                elif offset1 > 0:
                    idx -= offset1 # Important for reevaluation
                    offset1 = 0
                elif offset2 > 0:
                    idx -= offset2 # Important for reevaluation
                    offset1 = 0
                elif counter == 0 and char == comment_token[offset3]:
                    offset3 += 1
                    if offset3 == len(comment_token):
                        dump = True
                        dump_index = idx - offset3 + 1
                        offset3 = 0
            else:
                if char == comment_token[offset3]:
                    offset3 += 1
                    if offset3 == len(comment_token):
                        dump = True
                        dump_index = idx - offset3 + 1
                        offset3 = 0
                else:
                    idx -= offset1 # Important for reevaluation
                    offset3 = 0
        idx += 1 # Next char

    if dump == True:
        argument.VALUE = argument.VALUE[:dump_index] + " " * (idx - dump_index) + argument.VALUE[idx:]

### Returns the line/column position inside the given text based on the given string index
def line_column_position_from_index(text, index):
    lines = text.splitlines(True)
    idx = 0
    for linenum, line in enumerate(lines):
        if idx + len(line) > index:
            break
        idx += len(line)
    return linenum + 1, index - idx

### Returns the line inside the given text based on the given string index
def line_from_index(text, index):
    lines = text.splitlines(True)
    line_start_index = 0
    for line in lines:
        if line_start_index + len(line) > index:
            return (line[:-1], line_start_index)
        line_start_index += len(line)
    return ("", len(text))

### Ex : (a, b, c)
### becomes
### a
### b
### c
def to_string(list, eol = 1):
    result = ""
    for item in list:
        if item != None:
            result += str(item) + "\n" * eol
    return result[:-eol]

### Indents the given string
### Ex :
### er
### becomes
###     er
def indent(str):
    return "    " + str.replace("\n", "\n    ")
