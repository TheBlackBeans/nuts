import itertools

# ~ Errors ~

class Error(BaseException):
    pass

# ~ Boundary ~

class Boundary:
    """
Unique Boundary:
Works as a standard (FIFO) queue, but ensures items are only present once inside the queue.
"""
    def __init__(self, iterable=tuple()):
        self._content = set()
        self._queue = []
        for item in iterable:
            self.push(item)
    def push(self, value):
        if value in self._content:
            return
        self._content.add(value)
        self._queue.append(value)
    def pop(self):
        a = self._queue.pop()
        self._content.remove(a)
        return a
    def __contains__(self, value):
        return value in self._content
    def __bool__(self):
        return bool(self._queue)
        

# ~ Deterministic Finite Automaton ~

class DFA:
    def __init__(self, nfa, accepting_id=None, priority=0):
        nfa.compute_epsilon_reachables()
        start = nfa.states[nfa.start]
        states = {}
        done = set()
        boundary = Boundary()
        start_id = {start.id}
        for state in nfa.epsilon_reachables[start]:
            start_id.add(state.id)
        start_id = frozenset(start_id)
        states[start_id] = CompoundState(start_id)
        self._start = states[start_id]
        boundary.push(states[start_id])
        while boundary:
            current = boundary.pop()
            if current in done: continue
            done.add(current)
            
            accepting, label, prior = False, None, None
            for id in current.id:
                state = nfa.states[id]
                if state.accepting:
                    if prior == None or state.priority > prior:
                        accepting = True
                        label = state.label
                        prior = state.priority
            current.set_accepting(accepting, label)
            
            transitions = {}

            for id in current.id:
                for key, value in nfa.states[id].transition.items():
                    if key == EPSILON: continue
                    if key not in transitions:
                        transitions[key] = set()
                    transitions[key].update(value)
            for key, value in transitions.items():
                id = set()
                for state in value:
                    id.add(state.id)
                    for s in nfa.epsilon_reachables[state]:
                        id.add(s.id)
                id = frozenset(id)
                if id not in states:
                    states[id] = CompoundState(id)
                current.set_transition(key, states[id])
                boundary.push(states[id])
    def match_all(self, string):
        """
Yields all the indexes i such that string[:i] matches the regex.
"""
        current = self._start
        for i, char in enumerate(string):
            if current.accepting: yield MatchResult(True, 0, i, string[0:i], current.label)
            if char not in current.transition:
                return
            current = current.transition[char]
        if current.accepting: MatchReuslt(True, 0, len(string), string, current.label)
    def match(self, string):
        """
Returns if the regex matches at any point (if there exists an i such that string[:i] exactly matches the regex).
"""
        return self.match_longest(string)
    def match_shortest(self, string):
        """
Returns the shortest i such that string[:i] exactly matches the regex, of -1 if none, and the label of the accepting state.
"""
        current = self._start
        for i, char in enumerate(string):
            if current.accepting: return MatchResult(True, 0, i, string[0:i], current.label)
            if char not in current.transition:
                return MatchResult(False, 0, i, string, None)
            current = current.transition[char]
        return MatchResult(current.accepting, 0, len(string), string, current.label)
    def match_longest(self, string):
        """
Returns the longest i such that string[:i] exactly matches the regex, or -1 if none, and the label of the accepting state.
"""
        current = self._start
        successful = False
        max = 0
        label = None
        for i, char in enumerate(string):
            if current.accepting:
                successful = True
                max = i
                label = current.label
            if char not in current.transition:
                return MatchResult(successful, 0, max, string[0:max], label)
            current = current.transition[char]
        successful |= current.accepting
        if current.accepting:
            max = len(string)
            label = current.label
        return MatchResult(sucessful, 0, max, string[0:max], label)
    def match_exactly(self, string):
        raise NotImplementedError("This is not implemented and yet it is already deprecated! Just don't use it, right?")
        return match_longest(string) == len(string)
    def to_graph(self):
        result = """digraph {
rankdir=LR;
%s

%s
}
"""
        nodes = []
        edges = []

        done = {self._start}
        
        boundary = [self._start]
        while boundary:
            current = boundary.pop()
            nodes.append('node_%s [shape="%s", label="%s"];' % ('_'.join(str(e) for e in sorted(list(current.id))), "doublecircle" if current.accepting else "circle", ','.join(str(e) for e in current.id)))
            for key, node in current.transition.items():
                edges.append('node_%s -> node_%s [label="%s"];' % ('_'.join(str(e) for e in sorted(list(current.id))), '_'.join(str(e) for e in sorted(list(node.id))), key))
                if node not in done:
                    done.add(node)
                    boundary.append(node)
        return result % ('\n'.join(nodes), '\n'.join(edges))
        

class CompoundState:
    """
CompoundState is the main class for each DFA state. As its name suggests, it represents many NFA states combined.
Look up for the subset algorithm for more details about transforming an NFA to an DFA.
"""
    def __init__(self, id):
        self.id = id
        self.accepting = False
        self.label = None
        self.transition = {}
    def __repr__(self):
        return 'CS%s(%s)' % ('A'*self.accepting, ','.join(str(e) for e in self.id))
    def set_accepting(self, value=True, label=None):
        self.label = label
        self.accepting = value
    def set_transition(self, key, state):
        self.transition[key] = state
    def __bool__(self):
        return self.accepting

# ~ Nondeterministic Finite Automaton ~

EPSILON = ""
class AnyType: pass
ANY = AnyType()

class NFA:
    """
Nondeterministic Finite Automaton.
Generated by a regex. It is necessary to call the compute_epsilon_reachables after every state has been added.
"""
    def __init__(self):
        self.genid = itertools.count()
        self.states = {}
        self.epsilon_reachables = {}
        self.start = -1
    def create_state(self):
        id = next(self.genid)
        self.states[id] = State(id)
        return self.states[id]
    def set_start(self, state):
        self.start = state.id
    def _compute_e_reachable(self, state):
        if state not in self.epsilon_reachables:
            if EPSILON not in state.transition:
                self.epsilon_reachables[state] = frozenset()
            else:
                f = set()
                for s in state.transition[EPSILON]:
                    if s == state:
                        continue
                    f.update(self._compute_e_reachable(s))
                    f.add(s)
                self.epsilon_reachables[state] = frozenset(f)
        return self.epsilon_reachables[state]
    def compute_epsilon_reachables(self):
        for value in self.states.values():
            self._compute_e_reachable(value)
    def union(self, right):
        self.epsilon_reachables.clear()
        old_start = right.start
        for id, state in right.states.items():
            if id == old_start:
                self.states[self.start].add_transition(EPSILON, state)
            newid = next(self.genid)
            state.id = newid
            self.states[newid] = state
    def to_graph(self):
        result = """digraph {
rankdir=LR;
%s

%s
}
"""
        nodes = []
        edges = []

        done = {self.states[self.start]}
        
        boundary = [self.states[self.start]]
        while boundary:
            current = boundary.pop()
            nodes.append('%s [shape="%s"];' % (current.id, "doublecircle" if current.accepting else "circle"))
            for key, s in current.transition.items():
                for node in s:
                    edges.append('%s -> %s [label="%s"];' % (current.id, node.id, key if key != EPSILON else "ϵ"))
                    if node not in done:
                        done.add(node)
                        boundary.append(node)
        return result % ('\n'.join(nodes), '\n'.join(edges))

class State:
    def __init__(self, id):
        self.id = id
        self.transition = {}
        self.accepting = False
        self.refuting = False
        self.label = None
        self.priority = 0
    def add_transition(self, key, state):
        if key not in self.transition:
            self.transition[key] = set()
        self.transition[key].add(state)
    def set_accepting(self, value=True, label=None, priority=None):
        if label != None:
            self.label = label
        if priority != None:
            self.priority = priority
        self.accepting = value
    def set_refuting(self, value=True):
        self.refuting = refuting
    def __hash__(self):
        return hash(self.id)
    def __eq__(self, right):
        return self.id == right.id
    def __repr__(self):
        # return 'State%s{%s}' % ('A'*self.accepting,self.id)
        return 'S%s{%s}' % ('A'*self.accepting,self.id)
    def __bool__(self):
        return self.accepting
        
# ~ Pushdown Automaton to parse the regex ~

class Pattern:
    def __init__(self, stack):
        self.stack = stack
    def __repr__(self):
        return ''.join(repr(el) for el in self.stack)
    def to_NFA(self, start, nfa):
        for pattern in self.stack:
            start = pattern.to_NFA(start, nfa)
        return start

class Char(Pattern):
    def __init__(self, char):
        self.char = char
    def __repr__(self):
        return self.char
    def to_NFA(self, start, nfa):
        accepting = nfa.create_state()
        start.add_transition(self.char, accepting)
        return accepting
    
class ParenthesizedPattern(Pattern):
    def __init__(self, pattern):
        self.pattern = pattern
    def __repr__(self):
        return '(%s)' % repr(self.pattern)
    def to_NFA(self, start, nfa):
        return self.pattern.to_NFA(start, nfa)
    
class AlternatePattern(Pattern):
    def __init__(self, pat1, pat2):
        self.pattern1 = pat1
        self.pattern2 = pat2
    def __repr__(self):
        return '%s|%s' % (repr(self.pattern1), repr(self.pattern2))
    def to_NFA(self, start, nfa):
        n1 = nfa.create_state()
        n2 = nfa.create_state()
        accepting = nfa.create_state()
        
        start.add_transition(EPSILON, n1)
        e1 = self.pattern1.to_NFA(n1, nfa)
        e1.add_transition(EPSILON, accepting)
        
        start.add_transition(EPSILON, n2)
        e2 = self.pattern2.to_NFA(n2, nfa)
        e2.add_transition(EPSILON, accepting)
        return accepting
    
class RepeatPattern(Pattern):
    def __init__(self, pattern):
        if isinstance(pattern, RepeatPattern):
            raise Error('Multiple repeat')

class RepeatAny(RepeatPattern):
    def __init__(self, pattern):
        self.pattern = pattern
    def __repr__(self):
        return '%s*' % repr(self.pattern)
    def to_NFA(self, start, nfa):
        accepting = nfa.create_state()
        start.add_transition(EPSILON, accepting)
        n = nfa.create_state()
        start.add_transition(EPSILON, n)
        e = self.pattern.to_NFA(n, nfa)
        e.add_transition(EPSILON, n)
        e.add_transition(EPSILON, accepting)
        return accepting

class RepeatPlus(RepeatPattern):
    def __init__(self, pattern):
        self.pattern = pattern
    def __repr__(self):
        return '%s+' % repr(self.pattern)
    def to_NFA(self, start, nfa):
        accepting = nfa.create_state()
        n = nfa.create_state()
        start.add_transition(EPSILON, n)
        e = self.pattern.to_NFA(n, nfa)
        e.add_transition(EPSILON, n)
        e.add_transition(EPSILON, accepting)
        return accepting

class Optional(RepeatPattern):
    def __init__(self, pattern):
        self.pattern = pattern
    def __repr__(self):
        return '%s?' % repr(self.pattern)
    def to_NFA(self, start, nfa):
        accepting = nfa.create_state()
        start.add_transition(EPSILON, accepting)
        e = self.pattern.to_NFA(start, nfa)
        e.add_transition(EPSILON, accepting)
        return accepting
    
class Any(Pattern):
    def __init__(self):
        pass
    def __repr__(self):
        return '.'
    def to_NFA(self, start, nfa):
        accepting = nfa.create_state()
        start.add_transition(ANY, accepting)
        return accepting

class Class(Pattern):
    def __init__(self, chars):
        self.chars = chars
    def __repr__(self):
        return '[' + ''.join(self.chars) + ']'
    def to_NFA(self, start, nfa):
        accepting = nfa.create_state()
        for char in self.chars:
            start.add_transition(char, accepting)
        return accepting

def read_class(string, pos=0):
    ignore = False
    range_ = False
    chars = []
    while pos < len(string):
        c = string[pos]
        if ignore:
            chars.append(c)
            ignore = False
        elif c == ']':
            return Class(chars), pos
        elif c == '\\':
            ignore = True
        elif c == '-':
            if chars:
                range_ = True
            chars.append(c)
        elif range_:
            chars.pop() # '-'
            start = chars.pop()
            if ord(start) > ord(c):
                raise Error("Bad character range %s-%s at %s" % (start, c, pos))
            for i in range(ord(start), ord(c)+1):
                chars.append(chr(i))
            range_ = False
        else:
            chars.append(c)
        pos += 1
    raise Error('EOF before class end')

def read_element(string, pos=0, endsat=None):
    stack = []
    ignore = False
    while pos < len(string):
        c = string[pos]
        if ignore:
            if c in ESCAPE_MAP:
                pat, _ = read_element(ESCAPE_MAP[c])
                stack.append(pat)
            else:
                stack.append(Char(c))
            ignore = False
        elif c == endsat:
            return Pattern(stack), pos
        elif c == '(':
            sub, pos = read_element(string, pos+1, endsat=')')
            stack.append(ParenthesizedPattern(sub))
        elif c == '|':
            pat2, pos = read_element(string, pos+1, endsat=endsat)
            pat1 = Pattern(stack)
            return AlternatePattern(pat1, pat2), pos
        # elif c == '.':
        #     stack.append(Any())
        # Not implemented yet
        elif c == '[':
            pat, pos = read_class(string, pos+1)
            stack.append(pat)
        elif c == '*':
            pat = stack.pop()
            stack.append(RepeatAny(pat))
        elif c == '+':
            pat = stack.pop()
            stack.append(RepeatPlus(pat))
        elif c == '?':
            pat = stack.pop()
            stack.append(Optional(pat))
        elif c == '\\':
            ignore = True
        else:
            stack.append(Char(c))
        pos += 1
    if ignore:
        raise Error('EOF during escape char')
    if endsat == None:
        return Pattern(stack), pos+1
    raise Error('EOF before reading %s' % endsat)

# ~ Interface ~

class MatchResult:
    def __init__(self, successful, start, end, substring, label):
        self.successful = successful
        self.start = start
        self.end = end
        self.substring = substring
        self.label = label
    def __repr__(self):
        if not self.successful:
            return 'MatchResult<failed>'
        label = (' label: %s' % self.label) if self.label != None else ''
        
        return 'MatchResult<%s to %s%s>' % (self.start, self.end, label)

ESCAPE_MAP = {
    'w': '[a-zA-Z_0-9]',
    'n': '[0-9]'
}
    
def compile(string, label=None):
    """
Generates a DFA from a given regex.
"""
    nfa = NFA()
    
    start = nfa.create_state()
    nfa.set_start(start)
    
    accepting = read_element(string, 0)[0].to_NFA(start, nfa)
    accepting.set_accepting(label=label)

    dfa = DFA(nfa)
    
    return dfa

def compile_nfa(string, label=None, priority=0):
    """
Generates a NFA from a given regex.
Notice you'll have to pass the nfa to a dfa before
you can actually use it to match strings.
"""
    nfa = NFA()

    start = nfa.create_state()
    nfa.set_start(start)

    accepting = read_element(string, 0)[0].to_NFA(start, nfa)
    accepting.set_accepting(label=label, priority=priority)

    return nfa
