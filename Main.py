import sys
from PyQt6.QtWidgets import QApplication, QWidget

from Window import Window

app = QApplication(sys.argv)

window = Window()
window.show()

app.exec()