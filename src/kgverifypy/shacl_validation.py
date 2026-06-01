from rdflib.namespace import RDF, SH

def find_focus_nodes(data_graph, shapes_graph):
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
    print("SHACL validation module for KGVerifyPy.")