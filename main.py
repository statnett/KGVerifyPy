from pathlib import Path
from kgraphpy.graph import CIMGraph
from kgraphpy.utilities import load_graphs_from_cimxml
from kgraphpy.jsonld_utilities import load_json_from_url, extract_datatype_map, enrich_graph_datatypes, DEFAULT_CONTEXT_LINK
from kgraphpy.namespaces import CGMES_CIM
from kgraphpy.processor import CIMProcessor
from rdflib import Graph, URIRef, RDF, Literal
from rdflib.namespace import XSD, SH
from pyshacl import validate
from kgverifypy.file_handling import make_graph_from
from kgverifypy.shacl_validation import find_focus_nodes
from owlrl import DeductiveClosure, RDFS_Semantics
from typing import Optional, Sequence

def add_datatypes_from_default_context(g: Graph) -> None:
    context_data = load_json_from_url(DEFAULT_CONTEXT_LINK)
    context_data["@context"]["cim"] = "http://iec.ch/TC57/CIM100#"
    context_data["@context"]["eu"] = "http://iec.ch/TC57/CIM100-European#"
    datatype_map = extract_datatype_map(context_data)
    enrich_graph_datatypes(g, datatype_map)


def prepare_data_for_validation(files: Sequence[str|Path], ontology: Optional[Graph] = None) -> Graph:
    pr_list = load_graphs_from_cimxml(files)

    data = Graph()
    for pr in pr_list:
        pr.update_namespace("eu", "http://iec.ch/TC57/CIM100-European#")
        for prefix, namespace in pr.graph.namespace_manager.store.namespaces():
            data.bind(prefix, namespace)
        data += pr.graph

    if ontology:
        data += ontology
        DeductiveClosure(RDFS_Semantics).expand(data)

    add_datatypes_from_default_context(data)

    return data

def shacl_validation_with_file_output(output_name: str|Path, data: Graph, shacl_graph: Graph, ontology: Optional[Graph] = None) -> None:
    inference = "rdfs" if ontology else "none"
    
    r = validate(data, shacl_graph=shacl_graph, 
                 ont_graph=ontology, 
                 inference=inference, 
                 debug=False)
    conforms, results_graph, results_text = r
    assert isinstance(results_graph, Graph)
    print("Conforms:", conforms)
    print("Number of validation results:", len(list(results_graph.subjects())))
    
    outfile_txt = f"{output_name}.txt"
    outfile_jsonld = f"{output_name}.json"

    results_graph.serialize(outfile_jsonld, format="json-ld")
    with open(outfile_txt, "w", encoding="utf-8") as f:
        f.write(results_text)


def main():
    ontology_path = "../application-profiles-library/CGMES/CurrentRelease/RDFS"
    ontology_file1 = Path(ontology_path) / "61970-600-2_DiagramLayout-AP-Voc-RDFS2020.rdf"
    ontology_file2 = Path(ontology_path) / "61970-600-2_Equipment-AP-Voc-RDFS2020.rdf"
    ontology_file3 = Path(ontology_path) / "61970-600-2_GeographicalLocation-AP-Voc-RDFS2020.rdf"
    ontology_file4 = Path(ontology_path) / "61970-600-2_Operation-AP-Voc-RDFS2020.rdf"
    ontology_file5 = Path(ontology_path) / "61970-600-2_StateVariables-AP-Voc-RDFS2020.rdf"
    ontology_file6 = Path(ontology_path) / "61970-600-2_SteadyStateHypothesis-AP-Voc-RDFS2020.rdf"
    ontology_file7 = Path(ontology_path) / "61970-600-2_Topology-AP-Voc-RDFS2020.rdf"
    # ontology_graph = make_graph_from([
    #     ontology_file1,
    #     ontology_file2,
    #     ontology_file3,
    #     ontology_file4,
    #     ontology_file5,
    #     ontology_file6,
    #     ontology_file7
    # ])
    # ontology_input = ontology_graph
    ontology_input = None

    shacl_path = "../application-profiles-library/CGMES/CurrentRelease/SHACL/TTL/"
    shacl_file = Path(shacl_path) / "61970-600-2_Equipment-AP-Con-Simple-SHACL.ttl"
    shacl = Graph()
    shacl.parse(shacl_file, format="ttl")

    outpath = Path.cwd().parent / "shacl_validation_result"
    outfilename = outpath / "validation_output"

    file1 = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_DL.xml"
    file2 = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_EQ.xml"
    file3 = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_GL.xml"
    file4 = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_OP.xml"
    file5 = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_SSH.xml"
    file6 = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_SV.xml"
    file7 = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_TP.xml"

    file_list = [
        file1, 
        file2, 
        file3, 
        file4, 
        file5, 
        file6, 
        file7
        ]
    
    

    data = prepare_data_for_validation(file_list, ontology=ontology_input)
    
    shape_info = find_focus_nodes(data_graph=data, shapes_graph=shacl)

    total_shapes = len(shape_info)
    shapes_with_no_focus = sum(1 for _, f in shape_info if len(f) == 0)
    shapes_with_focus_nodes = sum(1 for _, f in shape_info if len(f) > 0)

    shacl_validation_with_file_output(outfilename, data, shacl, ontology=ontology_input)

    print("Total shapes:", total_shapes)
    print("Shapes with focus nodes:", shapes_with_focus_nodes)
    for shape, focus_nodes in shape_info:
        if len(focus_nodes) > 0:
            print(f"Shape: {shape}, Focus nodes count: {len(focus_nodes)}")
    """
    counter = 0
    for s, p, o in data.triples((None, None, None)):
        print(s, p, o)
        counter += 1
        if counter >= 10:
            break

    """


if __name__ == "__main__":
    # main()
    print("running nothing")
