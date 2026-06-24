
TOOLTIP_TEXTS = {
    "FOCUS_NODES": "Total number of shapes in shacl file is shown along with the number of shapes that have explicitly defined focus nodes in the data graph. "
        "Be aware that even if there are 0 explicit focus nodes in data graph, there may be implicit focus nodes that are created dynamically during validation. "
            "These are not reported. If explicit focus nodes are 0 and validation conforms, check if the shacl shape file used is correct and whether the namespaces match between the data, shacl shapes and rdfs graphs. "
                "The result may be incorrect due to mismatch between graphs.",

    "ADD_DATATYPES": "Add datatypes to the graph based on the provided context file or the default context.",
    
    "RDFS": "RDFS files are used to expand the data graph with inferred triples. This is required for some SHACL shapes."
}

if __name__ == "__main__":
    print("Texts for tooltips in KGVerifyPy GUI.")