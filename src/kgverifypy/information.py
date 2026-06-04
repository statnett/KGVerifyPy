focus_nodes_info = """

Total number of shapes in shacl file is shown along with the number of shapes that have explicitly defined focus nodes in the data graph. Be aware that even if there are 0 explicit focus nodes in data graph, there may
be implicit focus nodes that are created dynamically during validation. These are not reported. If explicit focus nodes are 0 and validation conforms, check if the shacl shape file used is correct and 
whether the namespaces match between the data, shacl shapes and rdfs graphs. The result may be incorrect due to mismatch between graphs.

"""