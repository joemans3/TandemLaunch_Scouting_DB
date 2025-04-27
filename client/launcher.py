import sys

from PyQt6.QtWidgets import QApplication

from .main import ClientApp


def main():
    app = QApplication(sys.argv)
    client = ClientApp()
    client.show()
    sys.exit(app.exec())
