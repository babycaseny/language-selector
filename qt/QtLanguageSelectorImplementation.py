
import sys
from qt import *

from QtLanguageSelector import LanguageSelector

def hello(*args):
    print "hello"
    print args


if __name__ == "__main__":

    app = QApplication(sys.argv)
    
    lc = LanguageSelector()
    app.setMainWidget(lc)
    lc.show()

    app.connect(lc.pushButtonOk, SIGNAL("clicked()"), hello)

    app.exec_loop()
    
