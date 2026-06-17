from logging.config import dictConfig
from kgverifypy.log_config import LOG_CONFIG
from kgverifypy.gui import CIMShaclGUI

dictConfig(LOG_CONFIG)



def main():
    gui = CIMShaclGUI()
    gui.run()

if __name__ == "__main__":
    main()
