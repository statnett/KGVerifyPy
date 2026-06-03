"""Validation-focused service layer for SHACL operations."""

from dataclasses import dataclass
from rdflib import Graph
from pyshacl import validate
from owlrl import DeductiveClosure, RDFS_Semantics
from kgverifypy.shacl_validation import find_focus_nodes
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


if __name__ == "__main__":
	print("Classes for handling pyshacl validation logic.")