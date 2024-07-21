import sys
import os
import json
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QFileDialog, QLabel, QComboBox, QDialog
from PyQt5.QtCore import QTimer
import logging

CONFIG_FILE = 'backup_scheduler_config.json'

class BackupScheduler(QWidget):
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.load_tasks()
        self.init_ui()
        self.setup_logging()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_tasks)
        self.timer.start(60000)  # Check every minute

    def init_ui(self):
        layout = QVBoxLayout()

        # Task list
        self.task_list = QListWidget()
        layout.addWidget(self.task_list)

        # Add task button
        add_button = QPushButton('Add Task')
        add_button.clicked.connect(self.add_task)
        layout.addWidget(add_button)

        # Edit task button
        edit_button = QPushButton('Edit Task')
        edit_button.clicked.connect(self.edit_task)
        layout.addWidget(edit_button)

        # Delete task button
        delete_button = QPushButton('Delete Task')
        delete_button.clicked.connect(self.delete_task)
        layout.addWidget(delete_button)

        self.setLayout(layout)
        self.setWindowTitle('Backup Scheduler')
        self.update_task_list()
        self.show()

    def setup_logging(self):
        logging.basicConfig(filename='backup_scheduler.log', level=logging.INFO,
                            format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    def add_task(self):
        dialog = TaskDialog(self)
        if dialog.exec_():
            self.tasks.append(dialog.get_task())
            self.update_task_list()
            self.save_tasks()

    def edit_task(self):
        current_item = self.task_list.currentItem()
        if current_item:
            index = self.task_list.row(current_item)
            dialog = TaskDialog(self, self.tasks[index])
            if dialog.exec_():
                self.tasks[index] = dialog.get_task()
                self.update_task_list()
                self.save_tasks()

    def delete_task(self):
        current_item = self.task_list.currentItem()
        if current_item:
            index = self.task_list.row(current_item)
            del self.tasks[index]
            self.update_task_list()
            self.save_tasks()

    def update_task_list(self):
        self.task_list.clear()
        for task in self.tasks:
            self.task_list.addItem(f"{task['source']} -> {task['destination']} ({task['frequency']})")

    def check_tasks(self):
        current_time = datetime.now()
        for task in self.tasks:
            if self.should_run_task(task, current_time):
                self.run_backup(task)

    def should_run_task(self, task, current_time):
        if task['frequency'] == 'Minute':
            return True
        elif task['frequency'] == 'Hour':
            return current_time.minute == 0
        elif task['frequency'] == 'Daily':
            return current_time.hour == 0 and current_time.minute == 0
        elif task['frequency'] == 'Weekly':
            return current_time.weekday() == 0 and current_time.hour == 0 and current_time.minute == 0
        elif task['frequency'] == 'Monthly':
            return current_time.day == 1 and current_time.hour == 0 and current_time.minute == 0

    def run_backup(self, task):
        source = task['source']
        destination = task['destination']
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            destination_path = ""
            if os.path.isfile(source):
                filename = os.path.basename(source)
                new_filename = f"{timestamp}_{filename}"
                destination_path = os.path.join(destination, new_filename)
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                os.system(f"cp '{source}' '{destination_path}'")
            elif os.path.isdir(source):
                new_dirname = f"{timestamp}_{os.path.basename(source)}"
                destination_path = os.path.join(destination, new_dirname)
                os.system(f"cp -R '{source}' '{destination_path}'")

            logging.info(f"Backup completed: {source} -> {destination_path}")
        except Exception as e:
            logging.error(f"Backup failed: {source} -> {destination}. Error: {str(e)}")

    def save_tasks(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.tasks, f)

    def load_tasks(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.tasks = json.load(f)

class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.task = task
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Source file/directory selection
        source_layout = QHBoxLayout()
        self.source_label = QLabel('Source:')
        self.source_path = QLabel(self.task['source'] if self.task else '')
        self.source_button = QPushButton('Select Source')
        self.source_button.clicked.connect(self.select_source)
        source_layout.addWidget(self.source_label)
        source_layout.addWidget(self.source_path)
        source_layout.addWidget(self.source_button)
        layout.addLayout(source_layout)

        # Destination directory selection
        dest_layout = QHBoxLayout()
        self.dest_label = QLabel('Destination:')
        self.dest_path = QLabel(self.task['destination'] if self.task else '')
        self.dest_button = QPushButton('Select Destination')
        self.dest_button.clicked.connect(self.select_destination)
        dest_layout.addWidget(self.dest_label)
        dest_layout.addWidget(self.dest_path)
        dest_layout.addWidget(self.dest_button)
        layout.addLayout(dest_layout)

        # Frequency selection
        freq_layout = QHBoxLayout()
        self.freq_label = QLabel('Frequency:')
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(['Minute', 'Hour', 'Daily', 'Weekly', 'Monthly'])
        if self.task:
            self.freq_combo.setCurrentText(self.task['frequency'])
        freq_layout.addWidget(self.freq_label)
        freq_layout.addWidget(self.freq_combo)
        layout.addLayout(freq_layout)

        # Save button
        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.accept)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def select_source(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Source")
        if path:
            self.source_path.setText(path)

    def select_destination(self):
        path = QFileDialog.getExistingDirectory(self, "Select Destination")
        if path:
            self.dest_path.setText(path)

    def get_task(self):
        return {
            'source': self.source_path.text(),
            'destination': self.dest_path.text(),
            'frequency': self.freq_combo.currentText()
        }

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BackupScheduler()
    sys.exit(app.exec_())
