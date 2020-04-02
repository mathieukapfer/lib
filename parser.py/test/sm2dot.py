from stdlib import * # stdlib.py required
import json

def help():
    print("************************")
    print("*** Sm2Dot converter ***")
    print("************************")
    print()
    print("Python 3 script")
    print()
    print("Converts a given .sm file into a .dot file")
    print()
    print("Arguments (order is irrelevant) :")
    print()
    print("    [MANDATORY] <filepath>.sm   // State machine filepath (.sm extension is mandatory)")
    print("    [OPTIONAL]  <filepath>.dot  // Destination filepath (.dot extension is ensured)")
    print("                                // Default value is <.sm filename>.dot")
    print("    [OPTIONAL]  <filepath>.json // JSON filepath for cosmetic options (.json extension is mandatory)")
    sys.exit(0)

def main(argv):
    ### Help
    if len(argv) < 1 or len(argv) > 3 or argv[0] == "--help":
        help()

    sm = None # Filepath to .sm file
    dot = None # Filepath of destination .dot file
    json = None # Filepath to .json file

    ## Parse CLI arguments
    for arg in argv:
        if arg.endswith(".sm"):
            sm = arg
        elif arg.endswith(".json"):
            json = arg
        else:
            dot = arg

    ## Filepath
    if sm == None:
        raise Exception("Missing .sm filepath, extension is mandatory")

    ## Destination
    if dot == None:
        dot = sm
    # Ensure .dot extension
    (dot, _) = os.path.splitext(dot)
    dot += ".dot"

    ## Json
    if json != None:
        load_json(json)

    ### Start
    start(sm, dot, node_root, export)

#################################
###           MODEL           ###
#################################

class Model:
    def __init__(self):
        self.StartMap = None
        self.StartName = None
        self.Class = None
        self.Header = None
        self.Maps = [] # List of 'Map' objects below

    def add_map(self, map):
        for m in self.Maps:
            if m.Name == map.Name:
                raise ParsingException("Duplicate map '%s'" % map.Name)

        self.Maps.append(map)
        map.Parent = self # Double linked

class Map:
    def __init__(self, name):
        self.Name = name
        self.Nodes = [] # List of 'Node' objects below
        MODEL.add_map(self)

    def add_node(self, node):
        for n in self.Nodes:
            if n.Name == node.Name:
                raise ParsingException("Duplicate node '%s::%s'" % (self.Name, node.Name))

        self.Nodes.append(node)
        node.Parent = self # Double linked

class Node:
    def __init__(self, name):
        self.Name = name
        self.Entry = None # Object 'Code' below
        self.Exit = None # Object 'Code' below
        self.Transitions = [] # List of 'Transition' objects below
        MODEL.Maps[-1].add_node(self)

    def add_transition(self, transition):
        self.Transitions.append(transition)
        transition.Parent = self # Double linked

class Transition:
    def __init__(self):
        self.Signature = None # Either 'Eval' or 'TimerEvent(...)'
        self.Condition = None
        self.Map = None
        self.Name = None
        self.Code = None # Object 'Code' below
        MODEL.Maps[-1].Nodes[-1].add_transition(self)

class Code:
    def __init__(self, text):
        self.Text = text

MODEL = Model()

#################################
###          GRAMMAR          ###
#################################

_Name = "[a-zA-Z0-9_]+"
_File = "[a-zA-Z0-9_.]+"
_Space = "[ \t\n]+"
_opt_Space = "[ \t\n]*"
_Anything = ".+?" # Non-greedy
_opt_Anything = ".*?" # Non-greedy

### Captured tokens
TOKEN_Name = "(" + _Name + ")"
TOKEN_File = "(" + _File + ")"
TOKEN_Anything = "(" + _Anything + ")"
TOKEN_opt_Anything = "(" + _opt_Anything + ")"
TOKEN_Node = TOKEN_Name + _opt_Space + "::" + _opt_Space + TOKEN_Name

def node_root(file_content):
    blank_comments(file_content, "//", '{', '}')
    iterator = Iterator(file_content)
    while iterator.has_remaining() == True:

        # Ex : %start standby::StateA
        regex_start = "%start" + _Space + TOKEN_Node
        result = parse(regex_start, node_start)
        if result != None:
            continue

        # Ex : %class CpwStateMachine
        regex_class = "%class" + _Space + TOKEN_Name
        result = parse(regex_class, node_class)
        if result != None:
            continue

        # Ex : %header CpwStateMachine.h
        regex_header = "%header" + _Space + TOKEN_File
        result = parse(regex_header, node_header)
        if result != None:
            continue

        # Ex : %map standby %% ... %%
        regex_map = "%map" + _Space + TOKEN_Name + _opt_Space + "%%" + TOKEN_opt_Anything + "%%"
        result = parse(regex_map, node_map)
        if result != None:
            continue

        if iterator.has_remaining() == True:
            # None of the above regexes worked, raise an exception
            raise ParsingException("Malformed expression, expected '%start' <name> OR '%class' <name> OR '%header' <name> OR '%map' <name> '%%' ... '%%'")

def node_start(map, name):
    if MODEL.StartMap != None or MODEL.StartName != None:
        raise ParsingException("'%start' has already been set", map)

    MODEL.StartMap = map
    MODEL.StartName = name

def node_class(class_value):
    if MODEL.Class != None:
        raise ParsingException("'%class' has already been set", class_value)

    MODEL.Class = class_value

def node_header(header_value):
    if MODEL.Header != None:
        raise ParsingException("'%header' has already been set", header_value)

    MODEL.Header = header_value

def node_map(map_name, map_content):
    map = Map(map_name)
    blank_comments(map_content, "//", '{', '}')
    iterator = Iterator(map_content)
    while iterator.has_remaining() == True:

        # Ex : StateA Entry { ... } Exit { ... } { ... }
        # Ex : Default { ... }
        regex_node = TOKEN_Name                                                               \
                   + "(?:" + _Space + "Entry" + _opt_Space + "{" + TOKEN_opt_Anything + "})?" \
                   + "(?:" + _Space + "Exit" + _opt_Space + "{" + TOKEN_opt_Anything + "})?"
        result = parse(regex_node, node_node)
        if result == None:
            raise ParsingException("Malformed expression, expected <name> ['Entry' '{' ... '}'] ['Exit' '{' ... '}'] '{' ... '}'")

        # Find content of braces { } manually
        # Regexes can't help here since inner braces { } are present
        result = parse_between('{', '}', node_transitions)

def node_node(name, _opt_entry, _opt_exit):
    node = Node(name)
    if _opt_entry != None:
        node.Entry = Code(_opt_entry)
    if _opt_exit != None:
        node.Exit = Code(_opt_exit)

def node_transitions(transitions_content):
    blank_comments(transitions_content, "//", '{', '}')
    iterator = Iterator(transitions_content)
    while iterator.has_remaining() == True:

        # Ex : Eval
        # Ex : Eval [ ... ]
        # Ex : TimerEvent(...)
        # Ex : TimerEvent(...) [ ... ]
        regex_transition_part1 = "(Eval|TimerEvent" + _opt_Space + "(?:\(" + _opt_Anything + "\)))" \
                               + _opt_Space + "(?:\[" + TOKEN_opt_Anything + "\])?"                 \

        result = parse(regex_transition_part1, node_transition_part1)
        if result == None:
            raise ParsingException("Malformed expression, expected ('Eval' OR 'TimerEvent' '(' ... ')') ['[' <condition> ']'] (<name> OR 'jump' '(' <map> '::' <name> ')') '{' ... '}'")

        # Ex : StateA { ... }
        # Ex : jump(standby::StateB) { ... }
        regex_transition_part2 = "(?:" + TOKEN_Name + "|jump" + _opt_Space + "\(" + _opt_Space + TOKEN_Node + _opt_Space + "\))" \
                               + _opt_Space + "{" + TOKEN_opt_Anything + "}"                                                     \

        result = parse(regex_transition_part2, node_transition_part2)
        if result == None:
            raise ParsingException("Malformed expression, expected (<name> OR 'jump' '(' <map> '::' <name> ')') '{' ... '}'")

def node_transition_part1(signature, _opt_condition):
    transition = Transition()
    transition.Signature = signature
    if _opt_condition != None:
        transition.Condition = _opt_condition

def node_transition_part2(_opt_name, _opt_jump_map, _opt_jump_name, code):
    transition = MODEL.Maps[-1].Nodes[-1].Transitions[-1]
    if _opt_name != None:
        transition.Map = MODEL.Maps[-1].Name
        transition.Name = _opt_name
    else:
        transition.Map = _opt_jump_map
        transition.Name = _opt_jump_name
    transition.Code = Code(code)

#################################
###           EXPORT          ###
#################################

def export():
    check_integrity()
    return export_model()

NODE_DICTIONARY = {} # Dictionary of <map>::<name> -> 'Node' object

def check_integrity():
    ### Start node
    # Ensure start node is filled
    if MODEL.StartMap == None or MODEL.StartName == None:
        raise ParsingException("Start node is not filled, please use '%start <map>::<name>' in your .sm file", 0)
    # Ensure start node exists
    map = [map for map in MODEL.Maps if map.Name == MODEL.StartMap]
    if not map:
        raise ParsingException("Couldn't find associated map for start node '%s::%s'" % (MODEL.StartMap, MODEL.StartName), MODEL.StartMap)
    map = map[0]
    node = [node for node in map.Nodes if node.Name == MODEL.StartName]
    if not node:
        raise ParsingException("Couldn't find associated node for start node '%s::%s'" % (MODEL.StartMap, MODEL.StartName), MODEL.StartName)
    node = node[0]
    # Set start node at first position
    map.Nodes.remove(node)
    map.Nodes.insert(0, node)

    ### Transitions
    # Remove 'nil' transitions
    for map in MODEL.Maps:
        for node in map.Nodes:
            for i in range(len(node.Transitions)-1, -1, -1):
                if node.Transitions[i].Name == "nil":
                    node.Transitions.pop(i)
    # Fill node dictionary
    for map in MODEL.Maps:
        for node in map.Nodes:
            key = "%s::%s" % (map.Name, node.Name)
            NODE_DICTIONARY[key] = node

    # Ensure all transitions exist
    for map in MODEL.Maps:
        for node in map.Nodes:
            for transition in node.Transitions:
                key = "%s::%s" % (transition.Map, transition.Name)
                found = NODE_DICTIONARY.get(key, None)
                if found == None:
                    raise ParsingException("Couldn't find associated node for transition '%s::%s'" % (transition.Map, transition.Name), transition.Name)

def export_model():
    result =    'digraph cpw {'
    result += '\n    compound=true;'
    result += '\n    bgcolor="#dddddd";'
    result += '\n'
    result += '\n    node'
    result += '\n        [shape=Mrecord width=1.5];'
    result += '\n'
    result += '\n' + indent(to_string([export_map(map) for map in MODEL.Maps], 2))
    result += '\n'
    result += '\n' + indent(export_transitions())
    result += '\n}'
    return result

def export_map(map):
    result =    'subgraph cluster_%s {' % map.Name
    result += '\n    label="%s"' % map.Name
    result += '\n    bgcolor="#ffffff";'
    result += '\n'
    result += '\n    //'
    result += '\n    // States (Nodes)'
    result += '\n    //'
    result += '\n'
    result += '\n' + indent(to_string([export_node(node) for node in map.Nodes], 2))

    if map.Name == MODEL.StartMap:
        result += '\n'
        result += '\n    "%start"'
        result += '\n        [label="" shape=circle style=filled fillcolor=black width=0.25];'

    result += '\n}'
    return result

def export_node(node):
    if node.Name == "Default":
        return None # Skip default node

    ### Build label
    label = str(node.Name)
    if node.Entry != None:
        label += "|Entry"
    if node.Exit != None:
        label += "|Exit"

    result =    '"%s::%s"' % (node.Parent.Name, node.Name)
    result += '\n    [label="{%s}"];' % label
    return result

def export_transitions():
    result =    '//'
    result += '\n// Transitions (Edges)'
    result += '\n//'
    result += '\n'
    result += '\n"%%start" -> "%s::%s"' % (MODEL.StartMap, MODEL.StartName)


    for map in MODEL.Maps:
        cluster_out_done = set() # Set of <map> string
        for node in map.Nodes:
            if node.Name != "Default": # Skip default node
                transition_set = set() # Set of 'Transitions" objects
                for transition in node.Transitions:
                    if transition not in transition_set:

                        ### Tail / Head
                        tail = ''
                        head = ''
                        if map.Name != transition.Map:
                            if transition.Map.VALUE in cluster_out_done:
                                continue
                            cluster_out_done.add(transition.Map.VALUE)
                            tail = 'ltail=%s' % "cluster_%s" % map.Name
                            head = ' lhead=%s' % "cluster_%s" % transition.Map

                        ### Color / Head
                        option = get_json_option(transition)
                        color = '' if option.Color == None else ' color="%s"' % option.Color
                        weight = '' if option.Weight == None else ' weight="%s"' % option.Weight

                        ### Build label
                        has_eval = transition.Signature == "Eval"
                        has_timer = not has_eval
                        # Allows to display both 'Eval' and 'TimerEvent'
                        transition_set.add(transition)
                        for t in node.Transitions:
                            if t != transition and t.Name == transition.Name:
                                transition_set.add(t)
                                if has_eval == False:
                                    has_eval = t.Signature == "Eval"
                                elif has_timer == False:
                                    has_timer = t.Signature != "Eval"
                        if has_eval == True and has_timer == True:
                            label = "Eval\lTimerEvent"
                        elif has_eval == True:
                            label = "Eval"
                        else:
                            label = "TimerEvent"
                        label = 'label="%s"'% label

                        result += '\n'
                        result += '\n"%s::%s" -> "%s::%s"' % (node.Parent.Name, node.Name, transition.Map, transition.Name)
                        result += '\n    [%s%s%s%s%s];' % (label, tail, head, color, weight)

    return result

#################################
###            JSON           ###
#################################

JSON = None # Json file

BOTH_DICTIONARY = {} # Dictionary of <from map>::<from name>::<to map>::<to name> -> 'JsonOption' object
FROM_DICTIONARY = {} # Dictionary of <from map>::<from name>                      -> 'JsonOption' object
TO_DICTIONARY = {}   # Dictionary of                          <to map>::<to name> -> 'JsonOption' object

class JsonOption:
    def __init__(self):
        self.Color = None
        self.Weight = None

def ensure_exist(dictionary, key):
    result = dictionary.get(key, None)
    if result == None:
        result = JsonOption()
        dictionary[key] = result
    return result

def load_json(filepath):
    ### Load JSON file
    with open(filepath, 'r') as file:
        JSON = json.loads(file.read())

    # Iterate colors
    if "color" in JSON:
        for color in JSON["color"]:
            if "color" in color:
                from_state = None if "fromState" not in color else color["fromState"]
                to_state = None if "toState" not in color else color["toState"]
                ### Feed dictionaries
                if from_state != None and to_state != None:
                    ensure_exist(BOTH_DICTIONARY, "%s::%s" % (from_state, to_state)).Color = color["color"]
                elif from_state != None:
                    ensure_exist(FROM_DICTIONARY, from_state).Color = color["color"]
                elif to_state != None:
                    ensure_exist(TO_DICTIONARY, to_state).Color = color["color"]

    # Iterate weights
    if "weight" in JSON:
        for weight in JSON["weight"]:
            if "weight" in weight:
                from_state = None if "fromState" not in weight else weight["fromState"]
                to_state = None if "toState" not in weight else weight["toState"]
                ### Feed dictionaries
                if from_state != None and to_state != None:
                    ensure_exist(BOTH_DICTIONARY, "%s::%s" % (from_state, to_state)).Weight = weight["weight"]
                elif from_state != None:
                    ensure_exist(FROM_DICTIONARY, from_state).Weight= weight["weight"]
                elif to_state != None:
                    ensure_exist(TO_DICTIONARY, to_state).Weight = weight["weight"]

def get_json_option(transition):
    ### Check in dictionaries
    key = "%s::%s::%s::%s" % (transition.Parent.Parent.Name, transition.Parent.Name, transition.Map, transition.Name)
    options = BOTH_DICTIONARY.get(key, None)
    if options != None:
        return options # Option 'both'
    key = "%s::%s" % (transition.Parent.Parent.Name, transition.Parent.Name)
    options = FROM_DICTIONARY.get(key, None)
    if options != None:
        return options # Option 'from'
    key = "%s::%s" % (transition.Map, transition.Name)
    options = TO_DICTIONARY.get(key, None)
    if options != None:
        return options # Option 'to'
    return JsonOption() # Empty option

if __name__ == "__main__":
    main(sys.argv[1:])
