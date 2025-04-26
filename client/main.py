import sys
from pathlib import Path

import tomli
import tomli_w
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
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
    add_admin,
    add_department,
    add_department_head,
    add_university,
    delete_admin,
    delete_department_head,
    ping_server,
    search_catalog,
    update_admin,
    update_department,
    update_department_head,
    update_university,
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Server Settings")

        layout = QVBoxLayout()

        # 🔵 Load current settings safely
        SETTINGS_FILE = Path(__file__).parent.parent / "settings.toml"
        try:
            with open(SETTINGS_FILE, "rb") as f:
                settings = tomli.load(f)
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

    def perform_search(self):
        query = self.search_input.text().strip()

        try:
            results = search_catalog(query)
            self.populate_table(results)
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

            id_fields = {
                "university_id": row_data.get("university_id"),
                "department_id": row_data.get("department_id"),
                "department_head_id": row_data.get("department_head_id"),
                "admin_id": row_data.get("admin_id"),
            }

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

            # 🔵 Step 0: Validate fields first
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

            if (data["head_name"] and not data["head_email"]) or (
                data["head_email"] and not data["head_name"]
            ):
                QMessageBox.warning(
                    self,
                    "Missing Data",
                    "Both Department Head name and email must be filled, or both left blank.",
                )
                return

            if (data["admin_name"] and not data["admin_email"]) or (
                data["admin_email"] and not data["admin_name"]
            ):
                QMessageBox.warning(
                    self,
                    "Missing Data",
                    "Both Admin name and email must be filled, or both left blank.",
                )
                return

            # 🔵 Step 1: Search if entries already exist
            existing = search_catalog(data["university_name"])
            university_exists = any(
                result.get("university_name", "").lower()
                == data["university_name"].lower()
                for result in existing
            )

            existing_dep = search_catalog(data["department_name"])
            department_exists = any(
                result.get("department_name", "").lower()
                == data["department_name"].lower()
                for result in existing_dep
            )

            existing_head = search_catalog(data["head_name"])
            head_exists = any(
                result.get("department_head_name", "").lower()
                == data["head_name"].lower()
                for result in existing_head
            )

            existing_admin = search_catalog(data["admin_name"])
            admin_exists = any(
                result.get("admin_name", "").lower() == data["admin_name"].lower()
                for result in existing_admin
            )

            if university_exists or department_exists or head_exists or admin_exists:
                QMessageBox.warning(
                    self,
                    "Already Exists",
                    "Some fields already exist. Please check your entries.",
                )
                return

            # 🔵 Step 2: Create in order
            uni_result = add_university(data["university_name"])
            if not uni_result:
                QMessageBox.warning(self, "Error", "Failed to add university.")
                return

            university_id = uni_result["id"]

            dep_result = add_department(data["department_name"], university_id)
            if not dep_result:
                QMessageBox.warning(self, "Error", "Failed to add department.")
                return

            department_id = dep_result["id"]

            if data["head_name"] and data["head_email"]:
                add_department_head(
                    data["head_name"], data["head_email"], department_id, university_id
                )

            if data["admin_name"] and data["admin_email"]:
                add_admin(
                    data["admin_name"],
                    data["admin_email"],
                    department_id,
                    university_id,
                )

            QMessageBox.information(self, "Success", "Entry created successfully!")
            self.search_input.setText("")
            self.perform_search()

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

        department_head_id = ids.get("department_head_id")
        admin_id = ids.get("admin_id")

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete the Department Head and Admin for this entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        success = True

        if department_head_id:
            if not delete_department_head(department_head_id):
                success = False

        if admin_id:
            if not delete_admin(admin_id):
                success = False

        if success:
            QMessageBox.information(self, "Deleted", "Entry deleted successfully.")
        else:
            QMessageBox.warning(
                self, "Partial Failure", "Some deletions may have failed."
            )

        self.perform_search()

    def edit_selected_entry(self):
        selected_row = self.results_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "No Selection", "Please select an entry to edit.")
            return

        # Extract data
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

        dialog = EditEntryDialog(current_data, self)
        if dialog.exec():
            new_data = dialog.get_data()

            changes_made = False

            # Check and update fields individually
            if new_data["university_name"] != current_data["university_name"]:
                changes_made |= update_university(
                    ids.get("university_id"), new_data["university_name"]
                )

            if new_data["department_name"] != current_data["department_name"]:
                changes_made |= update_department(
                    ids.get("department_id"), new_data["department_name"]
                )

            if ids.get("department_head_id") and (
                new_data["department_head_name"] != current_data["department_head_name"]
                or new_data["department_head_email"]
                != current_data["department_head_email"]
            ):
                changes_made |= update_department_head(
                    ids.get("department_head_id"),
                    new_data["department_head_name"],
                    new_data["department_head_email"],
                )

            if ids.get("admin_id") and (
                new_data["admin_name"] != current_data["admin_name"]
                or new_data["admin_email"] != current_data["admin_email"]
            ):
                changes_made |= update_admin(
                    ids.get("admin_id"), new_data["admin_name"], new_data["admin_email"]
                )

            if changes_made:
                QMessageBox.information(self, "Updated", "Entry updated successfully!")
                self.perform_search()
            else:
                QMessageBox.information(self, "No Changes", "No fields were modified.")

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

            # Save to settings.toml
            SETTINGS_FILE = Path(__file__).parent.parent / "settings.toml"

            with open(SETTINGS_FILE, "wb") as f:
                tomli_w.dump({"server": new_settings}, f)

            QMessageBox.information(
                self,
                "Settings Updated",
                "Server settings updated. Please restart the application.",
            )


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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = ClientApp()
    client.show()
    sys.exit(app.exec())
