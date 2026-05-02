# Jam Confirmation Mode
# pip install PySide6 pymupdf

import sys
import os
import fitz
import subprocess
import tempfile

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFileDialog,
    QListWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QComboBox, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# SMART SUMATRA DETECTION
def get_sumatra_path():
    possible_paths = [
        os.path.join(os.getcwd(), "SumatraPDF.exe"),  # same folder as exe
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe"
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


SUMATRA_PATH = get_sumatra_path()

APP_NAME = "Counter_Jam"
APP_VERSION = "1.0.0"

class DuplexManager(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(QIcon("assets/icon.ico"))
        self.resize(860, 620)

        self.pdf_path = None
        self.total_pages = 0

        self.pages_queue = []
        self.current_index = 0

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout()

        self.info = QLabel("Load PDF to begin")
        layout.addWidget(self.info)

        # Row 1
        row1 = QHBoxLayout()

        self.load_btn = QPushButton("Load PDF")
        self.load_btn.clicked.connect(self.load_pdf)
        row1.addWidget(self.load_btn)

        self.side_box = QComboBox()
        self.side_box.addItems([
            "Front Side (Odd Normal)",
            "Back Side (Even Reverse)",
            "Back Side (Even Normal)"
        ])
        row1.addWidget(self.side_box)

        self.prepare_btn = QPushButton("Prepare Queue")
        self.prepare_btn.clicked.connect(self.prepare_queue)
        row1.addWidget(self.prepare_btn)

        layout.addLayout(row1)

        # Row 2
        row2 = QHBoxLayout()

        self.flip_box = QComboBox()
        self.flip_box.addItems([
            "Normal Back Print",
            "Rotate Back 180°",
            "Rotate All Pages 180°"
        ])
        row2.addWidget(self.flip_box)

        self.auto_confirm = QCheckBox("Auto-confirm trusted prints")
        row2.addWidget(self.auto_confirm)

        layout.addLayout(row2)

        self.listbox = QListWidget()
        layout.addWidget(self.listbox)

        # Row 3
        row3 = QHBoxLayout()

        self.start_btn = QPushButton("Start Queue")
        self.start_btn.clicked.connect(self.start_queue)
        row3.addWidget(self.start_btn)

        self.retry_btn = QPushButton("Retry Current")
        self.retry_btn.clicked.connect(self.retry_current)
        row3.addWidget(self.retry_btn)

        self.skip_btn = QPushButton("Skip Current")
        self.skip_btn.clicked.connect(self.skip_current)
        row3.addWidget(self.skip_btn)

        layout.addLayout(row3)

        self.setLayout(layout)

    # ------------------------------
    def load_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf)"
        )

        if file_path:
            self.pdf_path = file_path
            doc = fitz.open(file_path)
            self.total_pages = len(doc)
            doc.close()

            self.info.setText(f"Loaded PDF ({self.total_pages} pages)")
            self.listbox.clear()

    # ------------------------------
    def prepare_queue(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "Error", "Load PDF first.")
            return

        mode = self.side_box.currentText()

        if "Front" in mode:
            self.pages_queue = [
                p for p in range(1, self.total_pages + 1) if p % 2 == 1
            ]

        elif "Reverse" in mode:
            self.pages_queue = [
                p for p in range(1, self.total_pages + 1) if p % 2 == 0
            ]
            self.pages_queue.reverse()

        else:
            self.pages_queue = [
                p for p in range(1, self.total_pages + 1) if p % 2 == 0
            ]

        self.current_index = 0
        self.listbox.clear()

        for page in self.pages_queue:
            self.listbox.addItem(f"Page {page} - Waiting")

    # ------------------------------
    def make_temp_page(self, page_number, rotate=0):
        src = fitz.open(self.pdf_path)
        out = fitz.open()

        out.insert_pdf(src, from_page=page_number - 1, to_page=page_number - 1)

        if rotate:
            out[0].set_rotation(rotate)

        temp_path = os.path.join(
            tempfile.gettempdir(),
            f"temp_page_{page_number}.pdf"
        )

        out.save(temp_path)
        out.close()
        src.close()

        return temp_path

    # ------------------------------
    def print_page(self, page_number):
        # CHECK SUMATRA FIRST
        if not SUMATRA_PATH:
            QMessageBox.warning(
                self,
                "Error",
                "SumatraPDF not found.\nInstall it or place it next to the EXE."
            )
            return False

        try:
            rotate = 0
            mode = self.flip_box.currentText()

            if "Rotate All" in mode:
                rotate = 180

            elif "Rotate Back" in mode and "Back" in self.side_box.currentText():
                rotate = 180

            temp_pdf = self.make_temp_page(page_number, rotate)

            cmd = [
                SUMATRA_PATH,
                "-print-to-default",
                "-print-settings",
                "fit,a4,portrait,center",
                temp_pdf
            ]

            subprocess.run(cmd, check=True)
            return True

        except Exception as e:
            QMessageBox.warning(self, "Print Error", str(e))
            return False

    # ------------------------------
    def start_queue(self):
        if not self.pages_queue:
            QMessageBox.warning(self, "Error", "Prepare queue first.")
            return

        self.process_current_page()

    # ------------------------------
    def process_current_page(self):
        if self.current_index >= len(self.pages_queue):
            QMessageBox.information(self, "Done", "Queue completed.")
            return

        page = self.pages_queue[self.current_index]
        item = self.listbox.item(self.current_index)

        ok = self.print_page(page)

        if not ok:
            item.setText(f"Page {page} - Failed Send")
            item.setBackground(Qt.red)
            return

        if self.auto_confirm.isChecked():
            item.setText(f"Page {page} - Printed")
            item.setBackground(Qt.green)
            self.current_index += 1
            self.process_current_page()
            return

        answer = QMessageBox.question(
            self,
            "Confirm Print",
            f"Did Page {page} print correctly?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )

        if answer == QMessageBox.Yes:
            item.setText(f"Page {page} - Printed")
            item.setBackground(Qt.green)
            self.current_index += 1
            self.process_current_page()

        elif answer == QMessageBox.No:
            item.setText(f"Page {page} - Jammed / Retry Needed")
            item.setBackground(Qt.red)

        else:
            item.setText(f"Page {page} - Paused")
            item.setBackground(Qt.yellow)

    # ------------------------------
    def retry_current(self):
        self.process_current_page()

    # ------------------------------
    def skip_current(self):
        if self.current_index < len(self.pages_queue):
            page = self.pages_queue[self.current_index]
            item = self.listbox.item(self.current_index)

            item.setText(f"Page {page} - Skipped")
            item.setBackground(Qt.yellow)

            self.current_index += 1
            self.process_current_page()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DuplexManager()
    win.show()
    sys.exit(app.exec())