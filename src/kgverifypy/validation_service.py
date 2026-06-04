"""Validation-focused service layer for SHACL operations."""

from dataclasses import dataclass
from rdflib import Graph
from rdflib.namespace import RDF, SH
from pyshacl import validate
from owlrl import DeductiveClosure, RDFS_Semantics
from kgverifypy.datatype_enrichment import add_datatypes_from_context
import logging

logger = logging.getLogger("primary")

@dataclass(frozen=True)
class FocusNodeSummary:
	"""Summary statistics for SHACL shape focus-node coverage."""

	total_shapes: int
	shapes_with_focus_nodes: int


@dataclass(frozen=True)
class ShaclValidationResult:
	"""Outcome of validating a data graph against SHACL shapes."""

	conforms: bool
	results_graph: Graph | None


class ShaclValidationService:
	"""Pure SHACL validation and reporting operations."""

	def prepare_data_for_validation(self, data_graph: Graph, rdfs_graph: Graph | None, add_datatypes: bool = False, context_url: str | None = None) -> None:
		"""Prepare the data graph for SHACL validation by optionally expanding with RDFS semantics and adding datatypes from a context.
		
		Parameters:
			data_graph (Graph): The RDF graph containing the data to be validated.
			rdfs_graph (Graph | None): An optional RDF graph containing RDFS semantics to expand the data graph.
			add_datatypes (bool): Whether to add datatypes from a context.
			context_url (str | None): The URL of the context to use for adding datatypes. If None a default context is applied.
		"""
		if data_graph is None:
			return
		
		if rdfs_graph is not None:
			logger.info("Expanding data graph with RDFS semantics from provided ontology.")
			self._expand_with_rdfs(data_graph, rdfs_graph)

		if add_datatypes:
			logger.info(f"Adding datatypes from context: {context_url if context_url else 'default context'}")
			add_datatypes_from_context(data_graph, context_url)

	
	def _expand_with_rdfs(self, data_graph: Graph, rdfs_graph: Graph) -> None:
		"""Expand the data graph with RDFS semantics from the provided RDFS graph.

		Parameters:
			data_graph (Graph): The RDF graph containing the data to be expanded.
			rdfs_graph (Graph): The RDF graph containing RDFS semantics to expand the data graph with.
		"""
		if data_graph is None or rdfs_graph is None:
			return
		
		for prefix, namespace in rdfs_graph.namespace_manager.store.namespaces():
			data_graph.namespace_manager.bind(prefix, namespace, override=False)
		data_graph += rdfs_graph

		DeductiveClosure(RDFS_Semantics).expand(data_graph)

	def summarize_focus_nodes(self, data_graph: Graph | None, shacl_graph: Graph | None) -> FocusNodeSummary | None:
		"""Summarize the number of shapes in the SHACL graph and how many have explicit focus nodes in the data graph.
		
		Parameters:
			data_graph (Graph | None): The RDF graph containing the data to be validated.
			shacl_graph (Graph | None): The RDF graph containing the SHACL shapes.
		
		Returns:
			FocusNodeSummary | None: A summary of total shapes and how many have explicit focus nodes, or None if either graph is not provided.
		"""
		if data_graph is None or shacl_graph is None:
			return None

		shape_info = find_focus_nodes(data_graph, shacl_graph)
		total_shapes = len(shape_info)
		shapes_with_focus_nodes = sum(1 for _, focus_nodes in shape_info if focus_nodes)
		return FocusNodeSummary(
			total_shapes=total_shapes,
			shapes_with_focus_nodes=shapes_with_focus_nodes,
		)

	def validate_graphs(self, data_graph: Graph | None, shacl_graph: Graph | None, rdfs_graph: Graph | None) -> ShaclValidationResult | None:
		if data_graph is None or shacl_graph is None:
			return None
		
		inference = "rdfs" if rdfs_graph is not None else "none"
			
		conforms, results_graph, _ = validate(
			data_graph,
			shacl_graph=shacl_graph,
			ont_graph=rdfs_graph,
			inference=inference,
			debug=False,
		)
		
		assert isinstance(conforms, bool)
		graph_result = results_graph if isinstance(results_graph, Graph) else None
		return ShaclValidationResult(conforms=conforms, results_graph=graph_result)
	
	def serialize_results(self, results_graph: Graph | None, output_path: str, output_format: str) -> bool:
		if results_graph is None:
			return False
		results_graph.serialize(destination=output_path, format=output_format)
		return True


def find_focus_nodes(data_graph: Graph, shapes_graph: Graph) -> list[tuple[str, set[str]]]:
	"""Find explicit focus nodes for each shape in the SHACL shapes graph based on the data graph.
	
	Implicit focus nodes that are generated dynamically during validation are not captured by this function. 

	Parameters:
		data_graph (Graph): The RDF graph containing the data to be validated.
		shapes_graph (Graph): The RDF graph containing the SHACL shapes.

	Returns:
		list[tuple[str, set[str]]]: List of shape identifiers with focus nodes associated with each shape.
	"""
	if data_graph is None or shapes_graph is None:
		return []
	
	shapes = list(shapes_graph.subjects(RDF.type, SH.NodeShape)) + \
				list(shapes_graph.subjects(RDF.type, SH.PropertyShape))

	results = []

	for shape in shapes:
		focus_nodes = set()

		# sh:targetClass
		for cls in shapes_graph.objects(shape, SH.targetClass):
			for node in data_graph.subjects(RDF.type, cls):
				focus_nodes.add(node)

		# sh:targetNode
		for node in shapes_graph.objects(shape, SH.targetNode):
			focus_nodes.add(node)

		# sh:targetSubjectsOf
		for prop in shapes_graph.objects(shape, SH.targetSubjectsOf):
			for subj in data_graph.subjects(prop, None):
				focus_nodes.add(subj)

		# sh:targetObjectsOf
		for prop in shapes_graph.objects(shape, SH.targetObjectsOf):
			for obj in data_graph.objects(None, prop):
				focus_nodes.add(obj)

		results.append((shape, focus_nodes))

	return results


if __name__ == "__main__":
	print("Classes for handling pyshacl validation logic.")