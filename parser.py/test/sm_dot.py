import json, sys, copy, os
import math

#######################################################################
##  dot file formats
##

str_dotFile = """digraph %s {\n    compound=true;\n    bgcolor="#dddddd";\n\n    node\n        [shape=Mrecord width=1.5];\n\n    %s\n\n    //\n    // Transitions (Edges)\n    //\n\n    %s\n\n}\n"""

str_dotMap = """\n    subgraph cluster_%s {\n\n        label="%s";\n        bgcolor="#ffffff";\n\n        //\n        // States (Nodes)\n        //\n\n        %s\n\n    }\n"""

str_dotStart = """\n        "%%start"\n            [label="" shape=circle style=filled fillcolor=black width=0.25];\n"""

str_dotState = """\n        "%s::%s"\n            [label="{%s%s%s%s}" %s];\n"""

str_dotTrx = """\n    "%s::%s" -> "%s"\n        [label="%s"%s];\n"""
	

#######################################################################
## Parse a .sm file
## Handle the changes
## Generate the full dot file
##

class smMachine:
	def __init__(self, name, defaults):
		self.name = name
		
		with open(name) as f:
			_f = "\n".join([x[:x.index('//')] if '//' in x else x for x in f.read().split('\n')])
			_f = _f.replace('ctxt.', '').split("%%")
			
		start = next(x for x in _f[0].split('\n') if x.startswith('%start')).replace('%start', '').strip()
		self.maps = [smMap(_f[i], _f[i+1], start, defaults) for i in range(0, len(_f)-1, 2)]
	
	def json(self):
		s = [x.repr() for x in self.maps]
		
		with open("result.json", "w+") as f:
			json.dump(s, f, indent=4);
		
	def dot(self, lv):
		mps = ""
		trxs = ""
		for m in self.maps:
			mps += m.dot(lv)
			trxs += m.trx_dot(lv)
			
		dot = str_dotFile % (self.name.split('.')[0], mps, trxs)
		return dot

	def rem_state(self, state):
		smap = state.split('::')[0]
		sname = state.split('::')[1]
		
		sm = next((x for x in self.maps if x.name == smap), None)
		if sm is not None:
			for i in range(0, len(sm.states)):
				if sm.states[i].name == sname:
					sm.states.pop(i)
					
					for _sm in self.maps:
						for _st in _sm.states:
							_st.trx = [x for x in _st.trx if not ((x.next == sname and x.pmap == smap) or (x.next == state))]
					break
	
	def _do_from(self, state, action):
		st = next((y for y in next((x.states for x in self.maps if x.name == state.split('::')[0]), []) if y.name == state.split('::')[-1]), None)
		if st is not None:
			for t in st.trx:
				action(t)
	
	def _do_to(self, state, action):
		for m in self.maps:
			for s in m.states:
				for t in s.trx:
					if t.next == state or m.name == state.split('::')[0] and t.next == state.split('::')[1] and 'color' not in t.opt:
						action(t)
	
	def _do_fromto(self, fstate, tstate, action):
		if fstate != tstate:
			st = next((y for y in next((x.states for x in self.maps if x.name == fstate.split('::')[0]), []) if y.name == fstate.split('::')[-1]), None)
			if st is not None:
				t = next((x for x in st.trx if x.next == tstate or x.pmap == tstate.split('::')[0] and x.next == tstate.split('::')[1]), None)
				if t is not None:
					action(t)
		else:
			self._do_from(fstate, action)
			self._do_to(tstate, action)
			st = next((y for y in next((x.states for x in self.maps if x.name == fstate.split('::')[0]), []) if y.name == fstate.split('::')[-1]), None)
			if st is not None:
				action(st)
				
	def colorize(self, color='', fromState=None, toState=None, state=False):
		def set_color(t):
			chk = ['color']
			if fromState is not None and toState is None:
				chk = ['ltail', 'color']
				
			for c in chk:
				if c in t.opt:
					return
			t.opt += ' color="%s"' % color
		
		if fromState is not None and toState is not None:
			self._do_fromto(fromState, toState, set_color)
		
		if fromState is not None and toState is None:
			self._do_from(fromState, set_color)

		if toState is not None and fromState is None:
			self._do_to(toState, set_color)
	
	def weightize(self, weight=-1, fromState=None, toState=None):
		weight = min(10, max(0, int(weight)))
		def set_weight(t):
			t.weight = weight
		
		if fromState is not None and toState is not None:
			if fromState != toState:
				self._do_fromto(fromState, toState, set_weight)
			else:
				self._do_from(fromState, set_weight)
				self._do_to(toState, set_weight)
		
		if fromState is not None and toState is None:
			self._do_from(fromState, set_weight)

		if toState is not None and fromState is None:
			self._do_to(toState, set_weight)
		

#######################################################################
## Parse a sm map
## Generate the map subgraph
## Handle the Default -> __state(s) transitions move
##

class smMap:
	def __init__(self, s0, s1, start, defaults):
		self.name = next(x.replace("%map", "").strip() for x in s0.split('\n') if x.startswith("%map"))
		self.states = [smState(self.name, x.strip()) for x in s1.split('\n}\n\n') if len(x) > 0]
		
		if start.startswith(self.name + ':'):
			self.states.append(smState(self.name, """%%%%start\n{\n	 		%s {}\n}\n""" % start.replace(self.name, '').replace('::', '')))
			self.states[-1].weight = 1
		
		d = next((x for x in self.states if x.name == 'Default'), None)
		if d is not None:
			dtx = [x for x in d.trx if x.next == 'Default']
			for s in self.states:
				if s.name != 'Default':
					s.dtrx = dtx
		
			for t in d.trx:
				if not '::' in t.next:
					for _s in self.states:
						if _s.name != 'Default' and not _s.name.startswith('%'):
							_s.trx.append(smTrx(t.pmap, _s.name, t.name + '[' + t.cond + ']    ' + t.next + '{' + t.action + '}'))
		
		for s in self.states:
			s.facto()
			
		f = None
		if self.name in defaults:
			f = next((x for x in self.states if x.name == defaults[self.name]), None)
		if f is None:
			f = self.states[int(math.floor(len(self.states)/2))]
			
		if d is not None:
			for t in d.trx:
				if '::' in t.next:
					_t = smTrx(t.pmap, f.name, t.name + '[' + t.cond + ']    ' + t.next + '{' + t.action + '}')
					_t.label = t.label
					_t.opt += ' ltail=cluster_%s' % self.name
					f.trx.append(_t)
	
	def repr(self):
		return {"name": self.name, "states": [x.repr() for x in self.states]}
	
	def dot(self, lv):
		sts = ""
		for _s in self.states:
			if _s.name != 'Default':
				try:
					sts += _s.dot(lv) % self.name
				except TypeError:
					sts += _s.dot(lv).replace('%%', '%')
		
		s = str_dotMap % (self.name, self.name, sts)
		return s
	
	def trx_dot(self, lv):
		trxs = ""
		for _s in self.states:
			for _t in _s.trx:
				trxs += _t.dot(lv)
		
		return trxs
		

#######################################################################
## Parse a sm state
## Generate the state dot descr
## Handle the transitions factorization
##

class smState:
	def __init__(self, pmap, data):
		self.pmap = pmap
		self.name = data.split('\n')[0].strip()
		self.trx = []
		self.entry = ""
		self.exit = ""
		self.dtrx = []
		self.opt = ""
		
		data = data[data.index(self.name)+len(self.name)+1:].strip()
		
		if data.startswith("Entry"):
			self.entry = data.split('{')[1].split('}')[0].strip().replace('\t', '')
			while '  ' in self.entry:
				self.entry = self.entry.replace('  ', ' ')
			data = data[data.find('}')+1:].strip()

		if data.startswith("Exit"):
			self.exit = data.split('{')[1].split('}')[0].strip().replace('\t', '')
			while '  ' in self.exit:
				self.exit = self.exit.replace('  ', ' ')
			data = data[data.find('}')+1:].strip()
		
		data = data[data.find('{')+1:].strip().split('}\n')
		self.trx = sorted([smTrx(self.pmap, self.name, x.strip()) for x in data if len(x.strip()) > 1], key=lambda x: x.name)
		
	def facto(self):
		done = []
		trx = [x for x in self.trx]
		self.trx = []
		for i in range(0, len(trx)):
			if i not in done:
				for j in range(i+1, len(trx)):
					if trx[i].next == trx[j].next:
						done.append(j)
						trx[i].label += '\l' + trx[j].label
				self.trx.append(trx[i])
		
	def repr(self):
		return {"name": self.name, "trx": [x.repr() for x in self.trx], "entry": self.entry, "exit": self.exit}
	
	def dot(self, lv):
		if self.name == '%%start':
			s = str_dotStart
		else:
			lo = "\l".join([x.label if lv > 0 else x.name + '/\l' for x in self.trx if x.next == self.name])
			lo += "\l".join([x.label if lv > 0 else x.name + '/\l' for x in self.dtrx])
			en = self.entry.replace('\n', '\l') + "\l" if lv > 0 else ''
			ex = self.exit.replace('\n', '\l') + "\l" if lv > 0 else ''

			s = str_dotState % (self.pmap, self.name, self.name,
								("|Entry/\l" + en if len(self.entry) > 0 else ""),
								("|Exit/\l" + ex if len(self.exit) > 0 else ""),
								("|" + lo if len(lo) > 0 else ""),
								self.opt)
			
		return s
	
	def trx_dot(self, lv):
		trxs = ''
		for t in self.trx:
			trxs += t.dot(lv)
		return trxs


#######################################################################
## Parse a sm transition
## Generate the transition dot descr
##

class smTrx:
	def __init__(self, pmap, pstate, line):
		self.pmap = pmap
		self.pstate = pstate
		self.opt = ""
		self.weight = 0
		
		self.name = ""
		self.cond = ""
		self.next = ""
		self.action = ""
		
		self.action = line[line.rfind('{')+1:].replace('}', '').strip()
		line = line[:line.rfind('{')].strip()
		
		self.next = line[max(line.rfind(' '), line.rfind('\t'))+1:].strip()
		line = line[:max(line.rfind(' '), line.rfind('\t'))].strip()
		if self.next == 'nil':
			self.next = pstate
		if '/' in self.next:
			self.action += '\l' + self.next.split('/')[-1]
			self.next = self.next.split('/')[0]
		self.next = self.next.replace('jump(', '').replace('push(', '').replace(')', '')
		
		self.cond = line.split('[')[1].replace(']', '').replace('\t', '').strip() if '[' in line else ""
		while('  ' in self.cond):
			self.cond = self.cond.replace('  ', ' ')
		
		self.name = line.split('[')[0].strip()
		
		self.label = self.name + '/\l' + ('\[%s\]/\l' % self.cond.replace('\n', '\l') if len(self.cond) > 0 else '') + ('%s\l' % self.action.replace('\n', '\l') if len(self.action) > 0 else '')
			
	def repr(self):
		return {"name": self.name, "cond": self.cond, "next": self.next, "action": self.action}
	
	def dot(self, lv):
		if self.pstate == '%%start':
			return '\n    "%%start" -> "%s::%s"\n' % (self.pmap, self.next)
		
		n = self.next.replace('jump(', '').replace('push(', '').replace(')', '')
		if self.pstate == self.next or 'pop(' in self.next or self.next == 'Default' or self.pstate == 'Default':
			return ""
		
		return str_dotTrx % (self.pmap, self.pstate, (self.pmap + '::' if not ':' in self.next  else '') + self.next , (self.label if lv > 0 else self.name + '/\l'), ' ' + self.opt.strip() + (' weight=%d' % self.weight if self.weight > 0 else ''))


def usage():
	print("Usage: python sm_dot.py SOURCE.sm [OPTION]")
	print("Generate the dot file for a state machine from the SOURCE.sm file")
	print("")
	print("OPTION:")
	print("    full:    draw the state machine with source code in the graph")
	print("    light:   draw the state machine with minimal data. [optionnal]")
	print("")
	print("By default, if the OPTION is not set, the light version is drawn.")
	print("")
	print("")
	print("GRAPH CUSTOMIZATION")
	print("You can customize the output graph by adding a \"sm_dot.json\" file near your SOURCE.sm file")
	print("With this file, you can hide one or multiple states in the graph, you can colorize transitions or set a weight")
	print("(in order to try to move a bloc) to a transitions")
	print("")
	print("See the \"sm_dot.json\" file in \"Gen/example\" folder for formatting example. The \"color\" and \"weight\"")
	print("section work the same way. If you specify:")
	print("    - fromState only: all transitions from this state are affected")
	print("    - toState only: all transitions to this state are affected")
	print("    - formState and toState: if they are different, only the transition from fromState to toState is affected.")
	print("                             if it is the same state, all the transitions from AND to this state are affected.")
	

if __name__ == "__main__":
	if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
		usage()
		exit()
	
	lv = next((1 for x in sys.argv if x == 'full'), 0)
	try:
		with open("sm_dot.json") as f:
			params = json.loads(f.read())
	except:
		params = {"remove": [], "color": [], "weight": [], "defaults": {}}
	
	m = smMachine(sys.argv[1], params['defaults'])
	for r_state in params["remove"]:
		print("Remove state \"%s\"" % r_state)
		m.rem_state(r_state)
	for col in params["color"]:
		print("Colorize %s" % str(col).replace("u'", "'").replace('::', '@').replace(':', ' =').replace('{', '').replace('}', '').replace('@', '::'))
		m.colorize(**col)
	for w in params["weight"]:
		print("Weightize %s" % str(w).replace("u'", "'").replace('::', '@').replace(':', ' =').replace('{', '').replace('}', '').replace('@', '::'))
		m.weightize(**w)
	
	with open('%s.dot' % m.name.replace('.sm', '_sm'), 'w+') as f:
		f.write(m.dot(lv))
		
