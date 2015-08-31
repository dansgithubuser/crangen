#!/usr/bin/python

#imports
import argparse, re, os

#declare args
parser=argparse.ArgumentParser(description=(
	'A limited c preprocessor designed to work with fake_libc_include. '+
	'#include, #ifdef, #ifndef, #else, and #endif are supported. '+
	'#if and #elif will always evaluate as false. '+
	'#define must be of the form "#define X" or "#define X y".'
))
parser.add_argument('-I', action='append', help='include directory')
parser.add_argument('-D', action='append', help='define')
parser.add_argument('input', help='source file to fake preprocess')
args=parser.parse_args()

#helpers
class IncludeHelper:
	def __init__(self): self.paths=[]

	def add_path(self, path): self.paths.append(path)

	def include(self, includer, includee):
		paths=self.paths+[os.path.split(os.path.realpath(includer))[0]]
		for path in paths:
			file_path=os.path.join(path, includee)
			if os.path.isfile(file_path):
				with open(file_path) as f:
					return f.readlines()

class Preprocessor:
	def __init__(self):
		self.defines={}
		self.include_helper=IncludeHelper()
		self.in_block_comment=False
		self.ifs=[]

	def preprocess(self, line, output):
		result=[]
		#comments
		decommented=''
		i=0
		while i<len(line):
			if not self.in_block_comment:
				if   '//' in line[i:i+2]: break
				elif '/*' in line[i:i+2]:
					self.in_block_comment=True
					i+=1
			if not self.in_block_comment: decommented+=line[i]
			if     self.in_block_comment:
				if   '*/' in line[i:i+2]:
					self.in_block_comment=False
					i+=1
			i+=1
		if not decommented.endswith('\n'): decommented+='\n'
		line=decommented
		#directives
		stripped=line.strip()
		if stripped.startswith('#include'):
			includee=re.search('["<](.*)[>"]', line).group(1)
			result+=self.include_helper.include(args.input, includee)
		elif stripped.startswith('#ifdef'):
			define=re.search(r'#ifdef\s+(\w+)', stripped).group(1)
			self.ifs.append(define in self.defines)
		elif stripped.startswith('#ifndef'):
			define=re.search(r'#ifndef\s+(\w+)', stripped).group(1)
			self.ifs.append(define not in self.defines)
		elif stripped.startswith('#if'   ): self.ifs.append(False)
		elif stripped.startswith('#elif' ): self.ifs[-1]='stay false' if self.ifs[-1] else False
		elif stripped.startswith('#else' ): self.ifs[-1]=not self.ifs[-1]
		elif stripped.startswith('#endif'): self.ifs.pop()
		elif stripped.startswith('#define'):
			match=re.search(r'#define\s+(\w+)\s+(\w+)', stripped)
			if match: self.defines[match.group(1)]=match.group(2)
			else:
				match=re.search(r'#define\s+(\w+)', stripped)
				self.defines[match.group(1)]=''
		elif stripped.startswith('#'): pass
		elif all([x==True for x in self.ifs]): output.append(line)
		#macros
		while len(output):
			again=False
			for macro in self.defines:
				match=re.search(r'(^|\W)('+macro+r')($|\W)', output[-1])
				if match:
					i=match.start(2)
					line=output[-1]
					output[-1]=line[:i]+self.defines[macro]+line[i+len(macro):]
					again=True
					break
			if not again: break
		return result

#declare variables
preprocessor=Preprocessor()
output=[]

#process args
if args.I:
	for path in args.I: preprocessor.include_helper.add_path(path)

if args.D:
	for d in args.D: preprocessor.defines[d]=''

#main
with open(args.input) as input_file: lines=input_file.readlines()
while len(lines): lines=preprocessor.preprocess(lines[0], output)+lines[1:]
print(''.join(output))
