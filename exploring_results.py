from itertools import count
from pathlib import Path
from rdflib import Graph, URIRef, RDF
from collections import Counter
from kgraphpy.utilities import load_graphs_from_cimxml
from kgraphpy.namespaces import CGMES_CIM

def exploring_validation_results(file: str|Path):
    g = Graph()
    g.parse(file, format="json-ld")

    unique_subject_count = len(set(g.subjects()))
    print(f"Unique subjects: {unique_subject_count}")

    counter_errortype = Counter()
    for _, _, error_type in g.triples((None, URIRef("http://www.w3.org/ns/shacl#sourceConstraintComponent"), None)):
        counter_errortype[error_type] += 1

    for error_type, count in counter_errortype.most_common():
        print(f"{error_type}: {count}")

    counter_shape = Counter()
    for _, _, shape in g.triples((None, URIRef("http://www.w3.org/ns/shacl#sourceShape"), None)):
        counter_shape[shape] += 1

    for shape, count in counter_shape.most_common():
        print(f"{shape}: {count}")


if __name__ == "__main__":
    
    # file1 = "../Nordic44/instances/Grid/cimxml/Nordic44-HV_SSH.xml"
    # file2 = "../Nordic44/instances/Grid/cimxml/Nordic44-HV_EQ.xml"
    # pr = load_graphs_from_cimxml([file2])
    # # g = Graph()
    # # g.namespace_manager = pr[0].graph.namespace_manager
    # # for pr in pr:
    # #     g += pr.graph
    # g = pr[0].graph

    """
    currentlimitsubjects = set(g.subjects(predicate=RDF.type, object=CGMES_CIM.CurrentLimit))
    print(f"Number of CurrentLimit subjects: {len(currentlimitsubjects)}")

    # missing_limittype = []
    limittypes = set()
    ifname = set()
    iflimitset = set()
    normalvalue = set()
    for subject in currentlimitsubjects:
        if (subject, CGMES_CIM["OperationalLimit.OperationalLimitType"], None) in g:
            for _, _, limittype in g.triples((subject, CGMES_CIM["OperationalLimit.OperationalLimitType"], None)):
                limittypes.add(limittype)
        
    # print(f"Unique OperationalLimitType values: {len(limittypes)}")
    for limittype in limittypes:
        print(f"OperationalLimitType: {limittype}")
        for s, _, _ in g.triples((None, CGMES_CIM["OperationalLimit.OperationalLimitType"], limittype)):
            if (s, CGMES_CIM["IdentifiedObject.name"], None) in g:
                for _, _, name in g.triples((s, CGMES_CIM["IdentifiedObject.name"], None)):    
                    ifname.add(name)

            if (s, CGMES_CIM["OperationalLimit.OperationalLimitSet"], None) in g:
                for _, _, limitset in g.triples((s, CGMES_CIM["OperationalLimit.OperationalLimitSet"], None)):
                    if (limitset, CGMES_CIM["IdentifiedObject.name"], None) in g:
                        iflimitset.add(limitset)

            if (s, CGMES_CIM["CurrentLimit.normalValue"], None) in g:
                for _, _, value in g.triples((s, CGMES_CIM["CurrentLimit.normalValue"], None)):
                    normalvalue.add(value)

        print(f"  Name: {ifname}")
        print(f"  OperationalLimitSet: {len(iflimitset)}")
        print(f"  NormalValue: {len(normalvalue)}")


            
    

    #     count_limittype = len(list(g.triples((subject, CGMES_CIM["OperationalLimit.OperationalLimitType"], None))))
    #     count_value = len(list(g.triples((subject, CGMES_CIM["CurrentLimit.value"], None))))
    #     if count_limittype == 0:
    #         missing_limittype.append(subject)
            # print(f"Subject {subject} has no OperationalLimitType property.")
            # print("CurrentLimit.value count:", count_value)

        # if count_value == 0:
        #     print(f"Subject {subject} has no value property.")
        #     print("OperationalLimitType count:", count_limittype)

    # print(f"Number of CurrentLimit subjects missing OperationalLimitType: {len(missing_limittype)}")
    """
    outpath = Path.cwd().parent / "instance"
    valresult_file = outpath / "Instance_simple_EQ_noinference_nodebug.json"
    # valresult_path = Path.cwd().parent / "shacl_validation_result"
    # valresult_file = valresult_path / "N44_grid_allprofiles_TP_complex_inference.json"
    exploring_validation_results(valresult_file)