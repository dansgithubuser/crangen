import style, lang_c
import argparse, os, re

parser=argparse.ArgumentParser(description=(
	'This is simple code generation framework. '+
	'The main goal is to be able to generate target code inline with Python code. '+
	'Inline Python code is marked with surrounding /*\\ and \\*/ markings, each on their own line. '+
	'Inline Python code can call the functions store(name, value) and load(name) to store variables across blocks. '+
	'Inline Python code can access the path variable to get the folder containing the metasource. '
	'Inline Python code can set result to a string of target code, result is initialized as "". '
))
parser.add_argument('input', help='where to base metasource paths off of')
parser.add_argument('--metasource', action='append', help='a metasource to process and create an output from')
parser.add_argument('--output', default='.', help='where to put output')
parser.add_argument('--define', action='append', help='define a variable with a value, separate with an equal sign, like variable=value')
args=parser.parse_args()

values={}
def store(name, value): values[name]=value
def load(name): return values[name]
def exec_local(x, metasource):
	locals={'result': ''}
	exec(x,
		{
			'store': store,
			'load': load,
			'path': os.path.split(os.path.realpath(metasource))[0],
			'style': style,
			'lang_c': lang_c,
			're': re,
			'os': os
		},
		locals
	)
	return locals['result']

if args.define:
	for d in args.define:
		name, value=d.split('=')
		store(name, value)

for m in args.metasource:
	full_path=os.path.join(args.input, m)
	with open(full_path) as f: lines=f.readlines()
	output=''
	meta=False
	metablock=''
	tabs=0
	for i in range(len(lines)):
		if '/*\\' in lines[i]:
			meta=True
			tabs=len(re.match(r'(\t*)/\*\\', lines[i]).group(1))
		elif '\\*/' in lines[i]:
			meta=False
			try:
				result=exec_local(metablock, full_path)
			except Exception as e:
				import traceback, sys
				numbered_metablock=metablock.split('\n')
				number_size=len(str(len(numbered_metablock)))
				for j in range(len(numbered_metablock)):
					format='{0:'+str(number_size)+'} '
					numbered_metablock[j]=format.format(j+1)+numbered_metablock[j]
				numbered_metablock='\n'.join(numbered_metablock)
				print('exception raised executing metablock ending on line {0}'.format(i+1))
				print(traceback.format_exc())
				print(numbered_metablock)
				sys.exit(1)
			result=result.strip().split('\n')
			for j in range(len(result)): result[j]='\t'*tabs+result[j]
			result='\n'.join(result)+'\n'
			output+=result
			metablock=''
		elif meta:
			if re.search(r'\S', lines[i]):
				if lines[i][:tabs]!='\t'*tabs:
					raise Exception('indentation error on line {0}'.format(i+1))
			metablock+=lines[i][tabs:]
		else: output+=lines[i]
	path=os.path.join(args.output, m.replace('.meta', ''))
	try: os.makedirs(os.path.split(path)[0])
	except: pass
	with open(path, 'w') as f: f.write(output)