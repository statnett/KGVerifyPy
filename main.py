from pathlib import Path
from cim_plugin.utilities import load_graphs_from_cimxml


def main():
    file = Path.cwd().parent / "../Nordic44/instances/Grid/cimxml/Nordic44-HV_EQ.xml"
    pr = load_graphs_from_cimxml(file)
    print(len(pr))

if __name__ == "__main__":
    main()
