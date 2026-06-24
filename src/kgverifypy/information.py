
TOOLTIP_TEXTS = {
    "FOCUS_NODES": """Even if there are 0 explicit focus nodes in data graph, there may be implicit focus nodes that are created dynamically during validation. These are not reported. 
                    If there are 0 explicit focus nodes and validation conforms, check if the SHACL shape file used is correct and whether the namespaces match between the data, SHACL and RDFS graphs. 
                    The result may be misleading due to mismatch between graphs.""",

    "ADD_DATATYPES": "Add datatypes to the graph based on the provided context file or the default context.",
    
    "RDFS": "RDFS files are used to expand the data graph with inferred triples. This is required for some SHACL shapes.",

    "NAMESPACES": """Check if the namespaces used in the data, SHACL and RDFS graphs are matched. 
                    Mismatched namespaces may lead to incorrect validation results.""",
    
    "CSV_REPORT": "The CSV file will get the same name as the graph report file but with a .csv extension."
}

if __name__ == "__main__":
    print("Texts for tooltips in KGVerifyPy GUI.")