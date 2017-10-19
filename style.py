def from_camel(s):
	l=[s[0]]
	for c in s[1:]:
		if c.istitle(): l.append('')
		l[-1]+=c
	return l

def to_camel(l, upper=False):
	s=''
	for i in range(len(l)):
		if i==0 and not upper:
			s+=l[i].lower()
		else:
			s+=l[i].capitalize()
	return s

def from_upper(s): return s.split('_')
def   to_upper(l): return '_'.join([x.upper() for x in l])

def from_lower(s): return s.split('_')
def   to_lower(l): return '_'.join([x.lower() for x in l])

def indent(content, tabs=1):
	if type(content)==str: content=content.splitlines()
	return ''.join(['\t'*tabs+i+'\n' if i else '\n' for i in content])
