try:
	from pycparser import c_ast as c
	from pycparser import parse_file
except ImportError:
	print('+---------------------------------------+')
	print('| pycparser missing, continuing without |')
	print('+---------------------------------------+')

import os

def unhandled(node):
	raise Exception('unhandled node type: '+describe(node))

def describe(node):
	import io, sys
	if   sys.version_info[0]==2: b=io.BytesIO()
	elif sys.version_info[0]==3: b=io.StringIO()
	else: Exception('unhandled version')
	node.show(buf=b)
	attrs=[
		attr+': '+str(getattr(node, attr))
		for attr in dir(node)
		if not attr.startswith('_')
	]
	return str(type(node))+'\n'+'\n'.join(attrs)+'\n'+b.getvalue()

def get_ast(path):
	folder=os.path.split(os.path.realpath(__file__))[0]
	cpp_path='python'
	cpp_args=[
		os.path.join(folder, 'fake_cpp.py'),
		'-I'+os.path.join(folder, 'fake_libc_include')
	]
	return parse_file(path, use_cpp=True, cpp_path=cpp_path, cpp_args=cpp_args)

def get_node(name, nodes):
	class NodeGetter(c.NodeVisitor):
		def generic_visit(self, node):
			if get_name(node)==self.name: self.result=node
			else: c.NodeVisitor.generic_visit(self, node)
		def get(self, name, nodes):
			self.name=name
			self.result=None
			for node in nodes:
				self.visit(node)
				if self.result: return self.result
	return NodeGetter().get(name, nodes)

def get_name(node):
	if isinstance(node, c.Decl): return node.name
	elif isinstance(node, c.Typedef): return node.name
	elif isinstance(node, c.TypeDecl): return node.declname
	elif isinstance(node, c.Enum): return node.name
	elif isinstance(node, c.Union): return node.name
	elif isinstance(node, c.IdentifierType): return ' '.join(node.names)
	elif isinstance(node, c.ArrayDecl): return get_name(node.type)
	elif isinstance(node, c.PtrDecl): return get_name(node.type)
	elif isinstance(node, c.FuncDecl): return get_name(node.type)
	elif isinstance(node, c.Struct): return None
	elif isinstance(node, c.EnumeratorList): return None
	elif isinstance(node, c.Enumerator): return None
	elif isinstance(node, c.Constant): return None
	elif isinstance(node, c.BinaryOp): return None
	elif isinstance(node, c.ParamList): return None
	unhandled(node)

def get_value(node, ast):
	if isinstance(node, c.Constant): return int(node.value)
	unhandled(node)

#get the C code that represents the type of this node
def get_type_str(node):
	if type(node)==c.Decl:
		storage=' '.join(node.storage)+' 'if node.storage else ''
		return storage+get_type_str(node.type)
	elif type(node)==c.TypeDecl:
		quals=' '.join(node.quals)+' 'if node.quals else ''
		return quals+get_type_str(node.type)
	elif type(node)==c.IdentifierType:
		return ' '.join(node.names)
	elif type(node)==c.PtrDecl:
		quals=' '.join(node.quals)+' ' if node.quals else ''
		return quals+get_type_str(node.type)+'*'
	#keeping these as comments because I haven't tested them (this code is from pycparser examples/cdecl.py)
	#elif type(node)==c.Typename:
	#	return get_type_str(node.type)
	#elif type(node)==c.ArrayDecl:
	#	arr='array'
	#	if node.dim: arr += '[%s]' % node.dim.value
	#	return arr + " of " + get_type_str(node.type)
	elif type(node)==c.FuncDecl:
		params=''
		if node.args: params=', '.join([get_type_str(param) for param in node.args.params])
		return get_type_str(node.type)+' (*)('+params+')'
	else: unhandled(node)

def get_args(node):
	if not is_function_declaration(node): raise Exception('node must be a function declaration')
	if not node.type.args: return []
	return node.type.args.params

def get_enum_list(node, ast):
	if isinstance(node, c.Typedef): return get_enum_list(node.type, ast)
	if isinstance(node, c.TypeDecl): return get_enum_list(node.type, ast)
	if not isinstance(node, c.Enum):
		raise Exception('not an enum')
	result=[]
	i=0
	for value in node.values.enumerators:
		if value.value: i=get_value(value.value, ast)
		result.append((value.name, i))
		i+=1
	return result

def get_fields(node, ast):
	if isinstance(node, c.Struct): return node.decls
	if isinstance(node, c.Decl): return get_fields(node.type, ast)
	if isinstance(node, c.TypeDecl): return get_fields(node.type, ast)
	if isinstance(node, c.Typedef): return get_fields(node.type, ast)
	if isinstance(node, c.IdentifierType): return get_fields(get_node(get_name(node), ast.ext), ast)
	unhandled(node)

def is_function_declaration(node):
	if not isinstance(node, c.Decl): return False
	if not isinstance(node.type, c.FuncDecl): return False
	return True

#check if a node represents a pointer or array -- may have false negatives
def is_pointy(node, ast):
	if isinstance(node, c.PtrDecl): return True
	if isinstance(node, c.ArrayDecl): return True
	if isinstance(node, c.Decl): return is_pointy(node.type, ast)
	if isinstance(node, c.TypeDecl): return is_pointy(node.type, ast)
	if isinstance(node, c.Typedef): return is_pointy(node.type, ast)
	if isinstance(node, c.IdentifierType):
		if node.names[-1] in ['char', 'int', 'unsigned', 'float', 'double']: return False
		return is_pointy(get_node(get_name(node), ast.ext), ast)
	return False

#check if a node represents a pointer -- may have false negatives
def is_pointer(node, ast):
	if isinstance(node, c.PtrDecl): return True
	if isinstance(node, c.Decl): return is_pointer(node.type, ast)
	if isinstance(node, c.TypeDecl): return is_pointer(node.type, ast)
	if isinstance(node, c.Typedef): return is_pointer(node.type, ast)
	if isinstance(node, c.IdentifierType):
		if node.names[-1] in ['char', 'int', 'unsigned', 'float', 'double']: return False
		return is_pointer(get_node(get_name(node), ast.ext), ast)
	return False

#check if a node represents an integer or enum -- may have false negatives
def is_integral(node, ast):
	if isinstance(node, c.Enum): return True
	if isinstance(node, c.Decl): return is_integral(node.type, ast)
	if isinstance(node, c.TypeDecl): return is_integral(node.type, ast)
	if isinstance(node, c.Typedef): return is_integral(node.type, ast)
	if isinstance(node, c.IdentifierType):
		if node.names[-1] in ['char', 'int', 'unsigned']: return True
		if node.names[-1] in ['float', 'double']: return False
		return is_integral(get_node(get_name(node), ast.ext), ast)
	return False

#check if a node represents a struct -- may have false negatives
def is_struct(node, ast):
	if isinstance(node, c.Struct): return True
	if isinstance(node, c.Decl): return is_struct(node.type, ast)
	if isinstance(node, c.TypeDecl): return is_struct(node.type, ast)
	if isinstance(node, c.Typedef): return is_struct(node.type, ast)
	if isinstance(node, c.IdentifierType):
		if node.names[-1] in ['char', 'int', 'unsigned', 'float', 'double']: return False
		return is_struct(get_node(get_name(node), ast.ext), ast)
	return False

#check if a node represents a floating point number -- may have false negatives
def is_floaty(node, ast):
	if isinstance(node, c.Decl): return is_floaty(node.type, ast)
	if isinstance(node, c.TypeDecl): return is_floaty(node.type, ast)
	if isinstance(node, c.Typedef): return is_floaty(node.type, ast)
	if isinstance(node, c.IdentifierType):
		if node.names[-1] in ['float', 'double']: return True
		if node.names[-1] in ['char', 'int', 'unsigned']: return False
		return is_floaty(get_node(get_name(node), ast.ext), ast)
	return False

def gen_print_enum(enum_variable, enum_node, ast, print_prefix='printf("', print_postfix='");'):
	result='switch('+enum_variable+'){\n'
	for enum, value in get_enum_list(enum_node, ast):
		result+='\tcase '+enum+': '+print_prefix+enum+print_postfix+' break;\n'
	result+='}\n';
	return result
