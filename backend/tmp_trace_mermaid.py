from pathlib import Path
import json
import re
from cortex.pipeline.infrastructure.ast_parser import PythonASTParser
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.pipeline.infrastructure.artifact_generator import MermaidGenerator

root = Path('src').resolve()
files = sorted([
    p for p in root.rglob('*.py')
    if '__pycache__' not in p.parts and p.name != 'setup.py'
])
parser = PythonASTParser()
parsed = []
for path in files:
    text = path.read_text(encoding='utf-8', errors='ignore')
    rel_path = str(path.relative_to(Path('src').resolve())).replace('\\', '/')
    parsed.append(parser.parse(text, rel_path))

result = GraphBuilder(job_id='job-demo', repo_url='https://github.com/example/Cortex').build(parsed)
output = MermaidGenerator().generate(result, 'Cortex')
node_count = result.node_count()
edge_count = result.edge_count()
mermaid_nodes = len(re.findall(r'^\s*[A-Za-z_][A-Za-z0-9_]*\["', output, flags=re.M))
print(json.dumps({
    'graph_builder_nodes': node_count,
    'graph_builder_edges': edge_count,
    'mermaid_input_nodes': node_count,
    'mermaid_output_nodes': mermaid_nodes,
    'node_types': {n.node_type.value: sum(1 for item in result.nodes if item.node_type == n.node_type) for n in sorted(set(result.nodes), key=lambda item: item.node_type.value)},
    'edge_types': {e.relationship.value: sum(1 for item in result.edges if item.relationship == e.relationship) for e in sorted(set(result.edges), key=lambda item: item.relationship.value)},
}, indent=2))
