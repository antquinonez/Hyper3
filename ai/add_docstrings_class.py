import ast, os
def add_class_docstrings(filepath, class_docs):
    with open(filepath) as f:
        lines = f.read().split('\n')
    source = '\n'.join(lines)
    tree = ast.parse(source)
    inserts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in class_docs:
            if not ast.get_docstring(node):
                first_stmt = node.body[0]
                line_idx = first_stmt.lineno - 1
                indent = len(lines[line_idx]) - len(lines[line_idx].lstrip())
                indent_str = ' ' * indent
                doc = f'{indent_str}\"\"\"{class_docs[node.name]}\"\"\"'
                inserts.append((line_idx, doc))
    inserts.sort(key=lambda x: x[0], reverse=True)
    for line_idx, doc in inserts:
        lines.insert(line_idx, doc)
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    return len(inserts)
src = 'src/hyper3'
