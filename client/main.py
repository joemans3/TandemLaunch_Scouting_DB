import traceback

import requests
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .api import (
    create_person,
    delete_person,
    download_people_csv,
    list_people,
    ping_server,
    update_person,
)
from .country_data import get_all_country_names
from .ror_loader import ensure_ror_data, load_university_names
from .settings import load_settings, save_settings


class DownloadThread(QThread):
    success = pyqtSignal()
    failure = pyqtSignal(str)
    status = pyqtSignal(str)

    def run(self):
        try:
            ensure_ror_data(status_cb=lambda msg: self.status.emit(msg))
            self.success.emit()
        except Exception:
            self.failure.emit(traceback.format_exc())


class UniversityDataLoaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preparing University Data")
        self.setModal(True)
        self.setFixedSize(400, 120)

        layout = QVBoxLayout()
        self.label = QLabel("Initializing...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # infinite-style spinner

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.setLayout(layout)

        self.thread = DownloadThread()
        self.thread.status.connect(self.label.setText)
        self.thread.success.connect(self.accept)
        self.thread.failure.connect(self.handle_failure)
        self.thread.start()

    def handle_failure(self, message):
        QMessageBox.critical(
            self,
            "Download Failed",
            f"Could not download university data:\n\n{message}",
        )
        self.reject()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Server Settings")

        layout = QVBoxLayout()

        settings = load_settings()
        try:
            current_host = settings["server"]["host"]
            current_port = str(settings["server"]["port"])
        except Exception:
            current_host = ""
            current_port = ""

        layout = QVBoxLayout()

        self.host_input = QLineEdit(current_host)
        self.port_input = QLineEdit(current_port)

        layout.addWidget(QLabel("Server Host:"))
        layout.addWidget(self.host_input)

        layout.addWidget(QLabel("Server Port:"))
        layout.addWidget(self.port_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def get_settings(self):
        return {
            "host": self.host_input.text().strip(),
            "port": int(self.port_input.text().strip()),
        }


ROLES = ["Department Head", "TTO Officer", "Professor", "Admin"]
SUBFIELDS = ["Department", "TTO Office", "Incubator"]


class NewPersonDialog(QDialog):
    def __init__(self, universities, countries, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Person")

        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.email_input = QLineEdit()

        self.university_input = QComboBox()
        self.university_input.setEditable(True)
        self.university_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.university_input.setMaxVisibleItems(15)
        self.university_input.setPlaceholderText("Start typing...")
        self.university_input.addItems(load_university_names())

        self.country_input = QComboBox()
        self.country_input.setEditable(True)
        self.country_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.country_input.setMaxVisibleItems(15)
        self.country_input.setPlaceholderText("Start typing...")
        self.country_input.addItems(get_all_country_names())

        self.subfield_input = QComboBox()
        self.subfield_input.addItems(SUBFIELDS)

        self.subfield_name_input = QLineEdit()

        self.role_input = QComboBox()
        self.role_input.addItems(ROLES)

        self.notes_input = QLineEdit()

        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Email:"))
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("University:"))
        layout.addWidget(self.university_input)

        layout.addWidget(QLabel("Country:"))
        layout.addWidget(self.country_input)

        layout.addWidget(QLabel("Subfield:"))
        layout.addWidget(self.subfield_input)

        layout.addWidget(QLabel("Subfield Name:"))
        layout.addWidget(self.subfield_name_input)

        layout.addWidget(QLabel("Role:"))
        layout.addWidget(self.role_input)

        layout.addWidget(QLabel("Notes:"))
        layout.addWidget(self.notes_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip(),
            "university": self.university_input.currentText(),
            "country": self.country_input.currentText(),
            "subfield": self.subfield_input.currentText(),
            "subfield_name": self.subfield_name_input.text().strip(),
            "role": self.role_input.currentText(),
            "notes": self.notes_input.text().strip(),
        }


class EditPersonDialog(QDialog):
    def __init__(self, data, universities, countries, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Person")
        layout = QVBoxLayout()

        self.name_input = QLineEdit(data["name"])
        self.email_input = QLineEdit(data["email"])

        # --- University ---
        self.university_input = QComboBox()
        self.university_input.setEditable(True)
        self.university_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.university_input.setMaxVisibleItems(15)
        self.university_input.setPlaceholderText("Start typing...")
        self.university_input.addItems(load_university_names())
        self.university_input.setCurrentText(data["university"])

        # --- Country ---
        self.country_input = QComboBox()
        self.country_input.setEditable(True)
        self.country_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.country_input.setMaxVisibleItems(15)
        self.country_input.setPlaceholderText("Start typing...")
        self.country_input.addItems(get_all_country_names())
        self.country_input.setCurrentText(data["country"])

        self.subfield_input = QComboBox()
        self.subfield_input.addItems(SUBFIELDS)
        self.subfield_input.setCurrentText(data["subfield"])

        self.subfield_name_input = QLineEdit(data["subfield_name"])
        self.role_input = QComboBox()
        self.role_input.addItems(ROLES)
        self.role_input.setCurrentText(data["role"])
        self.notes_input = QLineEdit(data["notes"])

        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Email:"))
        layout.addWidget(self.email_input)
        layout.addWidget(QLabel("University:"))
        layout.addWidget(self.university_input)
        layout.addWidget(QLabel("Country:"))
        layout.addWidget(self.country_input)
        layout.addWidget(QLabel("Subfield:"))
        layout.addWidget(self.subfield_input)
        layout.addWidget(QLabel("Subfield Name:"))
        layout.addWidget(self.subfield_name_input)
        layout.addWidget(QLabel("Role:"))
        layout.addWidget(self.role_input)
        layout.addWidget(QLabel("Notes:"))
        layout.addWidget(self.notes_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip(),
            "university": self.university_input.currentText(),
            "country": self.country_input.currentText(),
            "subfield": self.subfield_input.currentText(),
            "subfield_name": self.subfield_name_input.text().strip(),
            "role": self.role_input.currentText(),
            "notes": self.notes_input.text().strip(),
        }


class ClientApp(QWidget):
    def __init__(self):
        super().__init__()
        self.entries_per_page = 50
        self.current_page = 0
        self.universities = []
        self.countries = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("People Catalog")
        self.resize(1000, 600)

        layout = QVBoxLayout()
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, email, etc.")
        self.search_input.returnPressed.connect(self.perform_search)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)  # ms
        self._search_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)

        self.new_entry_button = QPushButton("Add Person")
        self.new_entry_button.clicked.connect(self.open_new_person_dialog)

        self.edit_button = QPushButton("Edit Selected Entry")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_selected_person)

        self.delete_button = QPushButton("Delete Selected Entry")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_person)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.export_button = QPushButton("Export All to CSV")
        self.export_button.clicked.connect(self.export_to_csv)
        search_layout.addWidget(self.settings_button)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.new_entry_button)
        search_layout.addWidget(self.edit_button)
        search_layout.addWidget(self.delete_button)
        search_layout.addWidget(self.export_button)

        layout.addLayout(search_layout)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Email",
                "University",
                "Country",
                "Subfield",
                "Subfield Name",
                "Role",
                "Notes",
            ]
        )
        self.results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.results_table.horizontalHeader().setStretchLastSection(True)

        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.results_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        layout.addWidget(self.results_table)
        self.status_label = QLabel("Status: Unknown")
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start(100)  # every 5 seconds for ongoing checks
        QTimer.singleShot(500, self.check_connection)
        QTimer.singleShot(600, self.perform_search)
        QTimer.singleShot(500, self.perform_search)

    def export_to_csv(self):
        from PyQt6.QtWidgets import QFileDialog

        try:
            # Ask user for where to save
            path, _ = QFileDialog.getSaveFileName(
                self, "Save People CSV", "people_export.csv", "CSV Files (*.csv)"
            )
            if not path:
                return

            data = download_people_csv()

            with open(path, "wb") as f:
                f.write(data)

            QMessageBox.information(self, "Success", f"CSV exported to:\n{path}")

        except requests.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = e.response.text
            QMessageBox.critical(self, "Download Failed", f"Server error:\n{detail}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")

    def check_connection(self):
        connected = ping_server()
        if connected:
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: green;")

            # Enable main features
            self.search_button.setEnabled(True)
            self.new_entry_button.setEnabled(True)
            self.edit_button.setEnabled(
                bool(self.results_table.selectionModel().selectedRows())
            )
            self.delete_button.setEnabled(
                bool(self.results_table.selectionModel().selectedRows())
            )
        else:
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: red;")

            # Disable features
            self.search_button.setEnabled(False)
            self.new_entry_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            new_settings = dialog.get_settings()
            save_settings({"server": new_settings})
            QMessageBox.information(self, "Settings Saved", "Success")

    def on_search_text_changed(self):
        self._search_timer.stop()
        self._search_timer.start()

    def delete_selected_person(self):
        row = self.results_table.currentRow()
        if row < 0:
            return

        person_id = self.results_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this person?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_person(person_id)
            QMessageBox.information(self, "Deleted", "Person deleted successfully.")
            self.perform_search()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete person: {e}")

    def on_selection_changed(self):
        selected = self.results_table.selectedItems()
        full_row_selected = bool(
            selected and len(selected) >= self.results_table.columnCount()
        )
        self.edit_button.setEnabled(full_row_selected)
        self.delete_button.setEnabled(full_row_selected)

    def perform_search(self):
        try:
            query = self.search_input.text().strip()
            people = list_people(query=query, offset=0, limit=self.entries_per_page)
            self.populate_table(people)
        except Exception as e:
            QMessageBox.warning(self, "Search Error", f"Could not fetch data:\n{e}")

    def populate_table(self, data):
        self.results_table.setRowCount(0)
        for row_data in data:
            row_pos = self.results_table.rowCount()
            self.results_table.insertRow(row_pos)
            for col, key in enumerate(
                [
                    "name",
                    "email",
                    "university",
                    "country",
                    "subfield",
                    "subfield_name",
                    "role",
                    "notes",
                ]
            ):
                item = QTableWidgetItem(row_data.get(key, ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row_data["id"])
                self.results_table.setItem(row_pos, col, item)

    def open_new_person_dialog(self):
        dialog = NewPersonDialog(self.universities, self.countries, self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                create_person(data)
                QMessageBox.information(self, "Success", "Person added successfully.")
                self.perform_search()
            except requests.HTTPError as e:
                try:
                    error_detail = e.response.json().get("detail", str(e))
                except Exception:
                    error_detail = e.response.text
                QMessageBox.warning(
                    self, "Server Error", f"Error submitting person:\n{error_detail}"
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def edit_selected_person(self):
        selected_row = self.results_table.currentRow()
        if selected_row < 0:
            return

        person_id = self.results_table.item(selected_row, 0).data(
            Qt.ItemDataRole.UserRole
        )
        current_data = {
            "name": self.results_table.item(selected_row, 0).text(),
            "email": self.results_table.item(selected_row, 1).text(),
            "university": self.results_table.item(selected_row, 2).text(),
            "country": self.results_table.item(selected_row, 3).text(),
            "subfield": self.results_table.item(selected_row, 4).text(),
            "subfield_name": self.results_table.item(selected_row, 5).text(),
            "role": self.results_table.item(selected_row, 6).text(),
            "notes": self.results_table.item(selected_row, 7).text(),
        }

        dialog = EditPersonDialog(current_data, self.universities, self.countries, self)
        while True:
            result = dialog.exec()
            if result != QDialog.DialogCode.Accepted:
                return  # user cancelled

            new_data = dialog.get_data()
            try:
                update_person(person_id, new_data)
                QMessageBox.information(self, "Success", "Person updated successfully.")
                self.perform_search()
                return
            except requests.HTTPError as e:
                try:
                    error_detail = e.response.json().get("detail", str(e))
                except Exception:
                    error_detail = e.response.text
                QMessageBox.critical(self, "Update Failed", f"{error_detail}")
            except Exception as e:
                QMessageBox.critical(self, "Unexpected Error", str(e))
