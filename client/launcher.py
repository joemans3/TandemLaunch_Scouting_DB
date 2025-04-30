import sys

from PyQt6.QtWidgets import QApplication, QDialog

from .main import ClientApp, UniversityDataLoaderDialog


def main():
    app = QApplication(sys.argv)

    loader_dialog = UniversityDataLoaderDialog()
    if loader_dialog.exec() != QDialog.DialogCode.Accepted:
        sys.exit(1)

    client = ClientApp()
    client.show()
    sys.exit(app.exec())
