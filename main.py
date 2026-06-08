from logging.config import dictConfig
from kgverifypy.log_config import LOG_CONFIG
from kgverifypy.gui import CIMShaclGUI

dictConfig(LOG_CONFIG)



def main():
    CIMShaclGUI()


if __name__ == "__main__":
    main()
