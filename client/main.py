import csv

import requests
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .api import (
    create_catalog_entry,
    delete_catalog_entry,
    ping_server,
    search_catalog_entries,
    update_catalog_entry,
)
from .settings import load_settings, save_settings


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


class ClientApp(QWidget):
    def __init__(self):
        super().__init__()

        self.current_page = 0
        self.entries_per_page = 50  # can be 50, 100, etc
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("University Catalog Search")
        self.resize(900, 600)

        layout = QVBoxLayout()

        # 🔵 Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search for university, department, head, admin..."
        )

        self.search_input.textChanged.connect(self.handle_search_input_change)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)

        # 🔵 Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            [
                "University",
                "Department",
                "Department Head",
                "Head Email",
                "Admin",
                "Admin Email",
            ]
        )

        self.results_table.itemSelectionChanged.connect(self.update_delete_button_state)

        self.results_table.setSortingEnabled(True)

        # Pagination controls
        self.arrow_widget = QWidget()
        arrow_layout = QHBoxLayout()
        arrow_layout.setContentsMargins(0, 0, 0, 0)
        arrow_layout.setSpacing(5)  # small gap between arrows
        self.prev_button = QPushButton("⟵")
        self.prev_button.setFixedSize(25, 25)
        self.prev_button.clicked.connect(self.go_to_previous_page)
        self.page_label = QLabel("1")
        self.page_label.setFixedWidth(20)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_button = QPushButton("⟶")
        self.next_button.setFixedSize(25, 25)
        self.next_button.clicked.connect(self.go_to_next_page)
        arrow_layout.addWidget(self.prev_button)
        arrow_layout.addWidget(self.page_label)
        arrow_layout.addWidget(self.next_button)
        self.arrow_widget.setLayout(arrow_layout)
        search_layout.addWidget(
            self.arrow_widget, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.search_input.returnPressed.connect(self.perform_search)

        self.export_button = QPushButton("Export to CSV")
        self.export_button.clicked.connect(self.export_to_csv)
        search_layout.addWidget(self.export_button)

        self.new_entry_button = QPushButton("Create New Entry")
        self.new_entry_button.clicked.connect(self.open_new_entry_dialog)
        search_layout.addWidget(self.new_entry_button)

        self.edit_button = QPushButton("Edit Selected Entry")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_selected_entry)
        search_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Selected Entry")
        self.delete_button.setEnabled(False)  # Start disabled
        self.delete_button.clicked.connect(self.delete_selected_entry)
        search_layout.addWidget(self.delete_button)

        layout.addLayout(search_layout)
        layout.addWidget(self.results_table)

        self.status_label = QLabel("Status: Unknown")
        layout.addWidget(self.status_label)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        search_layout.addWidget(self.settings_button)

        self.setLayout(layout)

        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start(5000)  # every 5 seconds for ongoing checks
        # 🔵 Do the first check after a tiny delay (half a second)
        QTimer.singleShot(500, self.check_connection)
        QTimer.singleShot(600, self.perform_search)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.perform_search)

    def perform_search(self):
        query = self.search_input.text().strip()

        try:
            offset = self.current_page * self.entries_per_page
            results = search_catalog_entries(
                query, offset=offset, limit=self.entries_per_page
            )
            self.populate_table(results)

            # 🔵 Update pagination buttons
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(len(results) == self.entries_per_page)
            self.page_label.setText(f"{self.current_page + 1}")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error contacting server: {e}")

    def populate_table(self, results):
        self.results_table.setRowCount(0)

        for row_data in results:
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)

            fields = [
                row_data.get("university_name", ""),
                row_data.get("department_name", ""),
                row_data.get("department_head_name", ""),
                row_data.get("department_head_email", ""),
                row_data.get("admin_name", ""),
                row_data.get("admin_email", ""),
            ]

            id_fields = {"catalog_entry_id": row_data.get("id")}

            for column, value in enumerate(fields):
                item = QTableWidgetItem(value)
                # 🔵 Store the IDs invisibly in the first column item (safe choice)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, id_fields)
                self.results_table.setItem(row_position, column, item)

    def open_new_entry_dialog(self):
        dialog = NewEntryDialog(self)
        if dialog.exec():
            data = dialog.get_data()

            # 🔵 Step 0: Validate required fields
            if not data["university_name"]:
                QMessageBox.warning(
                    self, "Missing Data", "University name is required."
                )
                return

            if not data["department_name"]:
                QMessageBox.warning(
                    self, "Missing Data", "Department name is required."
                )
                return

            try:
                create_catalog_entry(
                    {
                        "university_name": data["university_name"],
                        "department_name": data["department_name"],
                        "department_head_name": data.get("head_name") or None,
                        "department_head_email": data.get("head_email") or None,
                        "admin_name": data.get("admin_name") or None,
                        "admin_email": data.get("admin_email") or None,
                    }
                )
                QMessageBox.information(self, "Success", "Entry created successfully!")
                self.search_input.setText("")
                self.perform_search()

            except requests.HTTPError as e:
                if e.response.status_code == 400:
                    error_detail = e.response.json().get(
                        "detail", "Duplicate entry detected."
                    )
                    QMessageBox.warning(self, "Duplicate Entry", error_detail)
                else:
                    QMessageBox.warning(self, "Error", f"Server error: {e}")

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to create entry: {e}")

    def update_delete_button_state(self):
        selected_rows = self.results_table.selectionModel().selectedRows()
        if selected_rows:
            self.delete_button.setEnabled(True)
            self.edit_button.setEnabled(True)
        else:
            self.delete_button.setEnabled(False)
            self.edit_button.setEnabled(False)

    def delete_selected_entry(self):
        selected_row = self.results_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(
                self, "No Selection", "Please select an entry to delete."
            )
            return

        item = self.results_table.item(selected_row, 0)
        ids = item.data(Qt.ItemDataRole.UserRole)

        entry_id = ids.get("catalog_entry_id")

        if not entry_id:
            QMessageBox.warning(self, "Error", "Missing catalog entry ID.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this catalog entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_catalog_entry(entry_id)
            QMessageBox.information(
                self, "Deleted", "Catalog entry deleted successfully."
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete entry: {e}")

        self.perform_search()

    def edit_selected_entry(self):
        selected_row = self.results_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "No Selection", "Please select an entry to edit.")
            return

        # Extract current data
        current_data = {
            "university_name": self.results_table.item(selected_row, 0).text(),
            "department_name": self.results_table.item(selected_row, 1).text(),
            "department_head_name": self.results_table.item(selected_row, 2).text(),
            "department_head_email": self.results_table.item(selected_row, 3).text(),
            "admin_name": self.results_table.item(selected_row, 4).text(),
            "admin_email": self.results_table.item(selected_row, 5).text(),
        }

        item = self.results_table.item(selected_row, 0)
        ids = item.data(Qt.ItemDataRole.UserRole)

        entry_id = ids.get("catalog_entry_id")

        if not entry_id:
            QMessageBox.warning(self, "Error", "Missing catalog entry ID.")
            return

        # Open edit dialog
        dialog = EditEntryDialog(current_data, self)
        if dialog.exec():
            new_data = dialog.get_data()

            # Check if any field actually changed (optional optimization)
            if new_data == current_data:
                QMessageBox.information(self, "No Changes", "No fields were modified.")
                return

            try:
                update_catalog_entry(
                    entry_id,
                    {
                        "university_name": new_data["university_name"],
                        "department_name": new_data["department_name"],
                        "department_head_name": new_data.get("department_head_name")
                        or None,
                        "department_head_email": new_data.get("department_head_email")
                        or None,
                        "admin_name": new_data.get("admin_name") or None,
                        "admin_email": new_data.get("admin_email") or None,
                    },
                )
                QMessageBox.information(self, "Updated", "Entry updated successfully.")
                self.perform_search()

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update entry: {e}")

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

            QMessageBox.information(
                self,
                "Settings Updated",
                "Server settings updated. Please restart the application.",
            )

    def handle_search_input_change(self):
        self._search_timer.stop()
        self._search_timer.start(400)

    def go_to_previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.perform_search()

    def go_to_next_page(self):
        self.current_page += 1
        self.perform_search()

    def export_to_csv(self):
        try:
            # 🔵 Fetch all entries (no search, no pagination)
            results = search_catalog_entries(query="", offset=0, limit=1000000)

            if not results:
                QMessageBox.information(
                    self, "No Data", "No catalog entries to export."
                )
                return

            # 🔵 Ask where to save the CSV file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Catalog as CSV", "catalog_export.csv", "CSV Files (*.csv)"
            )

            if not file_path:
                return  # User cancelled

            # 🔵 Write to CSV
            with open(file_path, mode="w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    [
                        "University",
                        "Department",
                        "Department Head",
                        "Head Email",
                        "Admin",
                        "Admin Email",
                    ]
                )  # header

                for row in results:
                    writer.writerow(
                        [
                            row.get("university_name", ""),
                            row.get("department_name", ""),
                            row.get("department_head_name", ""),
                            row.get("department_head_email", ""),
                            row.get("admin_name", ""),
                            row.get("admin_email", ""),
                        ]
                    )

            QMessageBox.information(
                self,
                "Export Complete",
                f"Catalog exported successfully to:\n{file_path}",
            )

        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Failed to export catalog: {e}")


class EditEntryDialog(QDialog):
    def __init__(self, entry_data, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Edit Entry")

        layout = QVBoxLayout()

        self.university_input = QLineEdit(entry_data.get("university_name", ""))
        self.department_input = QLineEdit(entry_data.get("department_name", ""))
        self.head_name_input = QLineEdit(entry_data.get("department_head_name", ""))
        self.head_email_input = QLineEdit(entry_data.get("department_head_email", ""))
        self.admin_name_input = QLineEdit(entry_data.get("admin_name", ""))
        self.admin_email_input = QLineEdit(entry_data.get("admin_email", ""))

        layout.addWidget(QLabel("University Name:"))
        layout.addWidget(self.university_input)

        layout.addWidget(QLabel("Department Name:"))
        layout.addWidget(self.department_input)

        layout.addWidget(QLabel("Department Head Name:"))
        layout.addWidget(self.head_name_input)

        layout.addWidget(QLabel("Department Head Email:"))
        layout.addWidget(self.head_email_input)

        layout.addWidget(QLabel("Admin Name:"))
        layout.addWidget(self.admin_name_input)

        layout.addWidget(QLabel("Admin Email:"))
        layout.addWidget(self.admin_email_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def get_data(self):
        return {
            "university_name": self.university_input.text().strip(),
            "department_name": self.department_input.text().strip(),
            "department_head_name": self.head_name_input.text().strip(),
            "department_head_email": self.head_email_input.text().strip(),
            "admin_name": self.admin_name_input.text().strip(),
            "admin_email": self.admin_email_input.text().strip(),
        }


class NewEntryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Entry")

        layout = QVBoxLayout()

        self.university_input = QLineEdit()
        self.department_input = QLineEdit()
        self.head_name_input = QLineEdit()
        self.head_email_input = QLineEdit()
        self.admin_name_input = QLineEdit()
        self.admin_email_input = QLineEdit()

        layout.addWidget(QLabel("University Name:"))
        layout.addWidget(self.university_input)

        layout.addWidget(QLabel("Department Name:"))
        layout.addWidget(self.department_input)

        layout.addWidget(QLabel("Department Head Name:"))
        layout.addWidget(self.head_name_input)

        layout.addWidget(QLabel("Department Head Email:"))
        layout.addWidget(self.head_email_input)

        layout.addWidget(QLabel("Admin Name:"))
        layout.addWidget(self.admin_name_input)

        layout.addWidget(QLabel("Admin Email:"))
        layout.addWidget(self.admin_email_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def get_data(self):
        return {
            "university_name": self.university_input.text().strip(),
            "department_name": self.department_input.text().strip(),
            "head_name": self.head_name_input.text().strip(),
            "head_email": self.head_email_input.text().strip(),
            "admin_name": self.admin_name_input.text().strip(),
            "admin_email": self.admin_email_input.text().strip(),
        }
