import style

def gen_enum(name, series):
	result='enum class {0}{{\n'.format(name)
	for i in series: result+='\t{0},\n'.format(style.to_upper(style.from_camel(i)))
	result+='\tSENTINEL\n'
	result+='};\n'
	return result
