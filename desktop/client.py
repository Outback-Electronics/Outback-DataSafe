import sys
import os
import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QListWidget, QFileDialog, QTabWidget, QProgressBar,
                               QMessageBox, QSplitter, QStatusBar, QMenu, QToolBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QAction

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def set_token(self, token):
        self.token = token
    
    def get_headers(self):
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            return True
        return False
    
    def register(self, username, email, password):
        response = requests.post(
            f"{self.base_url}/api/auth/register",
            json={"username": username, "email": email, "password": password}
        )
        return response.status_code == 200
    
    def get_user_info(self):
        response = requests.get(
            f"{self.base_url}/api/auth/me",
            headers=self.get_headers()
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_files(self, parent_id=None):
        params = {}
        if parent_id:
            params['parent_id'] = parent_id
        response = requests.get(
            f"{self.base_url}/api/files",
            headers=self.get_headers(),
            params=params
        )
        if response.status_code == 200:
            return response.json()
        return []
    
    def upload_file(self, file_path, parent_id=None):
        files = {'file': open(file_path, 'rb')}
        data = {}
        if parent_id:
            data['parent_id'] = parent_id
        
        response = requests.post(
            f"{self.base_url}/api/files",
            headers=self.get_headers(),
            files=files,
            data=data
        )
        files['file'].close()
        return response.status_code == 200
    
    def create_folder(self, name, parent_id=None):
        response = requests.post(
            f"{self.base_url}/api/files/directory",
            headers=self.get_headers(),
            json={"filename": name, "parent_id": parent_id, "is_directory": True}
        )
        return response.status_code == 200
    
    def download_file(self, file_id, save_path):
        response = requests.get(
            f"{self.base_url}/api/files/{file_id}/download",
            headers=self.get_headers()
        )
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    
    def get_photos(self, limit=100, offset=0):
        response = requests.get(
            f"{self.base_url}/api/photos",
            headers=self.get_headers(),
            params={"limit": limit, "offset": offset}
        )
        if response.status_code == 200:
            return response.json()
        return []
    
    def upload_photo(self, file_path):
        files = {'file': open(file_path, 'rb')}
        response = requests.post(
            f"{self.base_url}/api/photos",
            headers=self.get_headers(),
            files=files
        )
        files['file'].close()
        return response.status_code == 200

class UploadThread(QThread):
    progress = Signal(int)
    finished = Signal(bool, str)
    
    def __init__(self, client, file_paths, parent_id=None, is_photo=False):
        super().__init__()
        self.client = client
        self.file_paths = file_paths
        self.parent_id = parent_id
        self.is_photo = is_photo
    
    def run(self):
        total = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            try:
                if self.is_photo:
                    success = self.client.upload_photo(file_path)
                else:
                    success = self.client.upload_file(file_path, self.parent_id)
                
                if success:
                    self.progress.emit(int((i + 1) / total * 100))
                else:
                    self.finished.emit(False, f"Failed to upload {os.path.basename(file_path)}")
                    return
            except Exception as e:
                self.finished.emit(False, str(e))
                return
        
        self.finished.emit(True, "Upload complete")

class LoginWindow(QWidget):
    def __init__(self, client, on_login_success):
        super().__init__()
        self.client = client
        self.on_login_success = on_login_success
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("Outback DataSafe")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (for registration)")
        self.email_input.setVisible(False)
        layout.addWidget(self.email_input)
        
        button_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(self.login_btn)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.clicked.connect(self.toggle_register)
        button_layout.addWidget(self.register_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setWindowTitle("Login")
        self.setFixedSize(300, 250)
    
    def toggle_register(self):
        if self.email_input.isVisible():
            self.email_input.setVisible(False)
            self.register_btn.setText("Register")
            self.login_btn.setText("Login")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.handle_login)
        else:
            self.email_input.setVisible(True)
            self.register_btn.setText("Back to Login")
            self.login_btn.setText("Create Account")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.handle_register)
    
    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if self.client.login(username, password):
            self.on_login_success()
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password")
    
    def handle_register(self):
        username = self.username_input.text()
        email = self.email_input.text()
        password = self.password_input.text()
        
        if not username or not email or not password:
            QMessageBox.warning(self, "Registration Failed", "Please fill all fields")
            return
        
        if self.client.register(username, email, password):
            QMessageBox.information(self, "Registration Success", "Account created! Please login.")
            self.toggle_register()
        else:
            QMessageBox.warning(self, "Registration Failed", "Username or email already exists")

class MainWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.current_parent_id = None
        self.path_history = []
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Outback DataSafe")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        back_action = QAction("Back", self)
        back_action.triggered.connect(self.go_back)
        toolbar.addAction(back_action)
        
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_files)
        toolbar.addAction(refresh_action)
        
        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Files tab
        files_tab = QWidget()
        files_layout = QVBoxLayout()
        
        files_toolbar = QHBoxLayout()
        
        upload_btn = QPushButton("Upload Files")
        upload_btn.clicked.connect(self.upload_files)
        files_toolbar.addWidget(upload_btn)
        
        new_folder_btn = QPushButton("New Folder")
        new_folder_btn.clicked.connect(self.new_folder)
        files_toolbar.addWidget(new_folder_btn)
        
        files_toolbar.addStretch()
        
        self.quota_label = QLabel("Storage: 0 GB / 1 TB")
        files_toolbar.addWidget(self.quota_label)
        
        files_layout.addLayout(files_toolbar)
        
        self.files_list = QListWidget()
        self.files_list.itemDoubleClicked.connect(self.handle_file_double_click)
        files_layout.addWidget(self.files_list)
        
        files_tab.setLayout(files_layout)
        self.tabs.addTab(files_tab, "Files")
        
        # Photos tab
        photos_tab = QWidget()
        photos_layout = QVBoxLayout()
        
        photos_toolbar = QHBoxLayout()
        
        upload_photo_btn = QPushButton("Upload Photos")
        upload_photo_btn.clicked.connect(self.upload_photos)
        photos_toolbar.addWidget(upload_photo_btn)
        
        photos_toolbar.addStretch()
        
        photos_layout.addLayout(photos_toolbar)
        
        self.photos_list = QListWidget()
        self.photos_list.setViewMode(QListWidget.IconMode)
        self.photos_list.setIconSize(200, 200)
        self.photos_list.setResizeMode(QListWidget.Adjust)
        photos_layout.addWidget(self.photos_list)
        
        photos_tab.setLayout(photos_layout)
        self.tabs.addTab(photos_tab, "Photos")
        
        main_widget.setLayout(layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Load initial data
        self.load_user_info()
        self.load_files()
        self.load_photos()
    
    def load_user_info(self):
        user_info = self.client.get_user_info()
        if user_info:
            used_gb = user_info['used_space'] / (1024 ** 3)
            quota_gb = user_info['quota'] / (1024 ** 3)
            self.quota_label.setText(f"Storage: {used_gb:.2f} GB / {quota_gb:.2f} GB")
    
    def load_files(self):
        self.files_list.clear()
        files = self.client.get_files(self.current_parent_id)
        
        for file in files:
            icon_text = "📁" if file['is_directory'] else "📄"
            item_text = f"{icon_text} {file['original_filename']}"
            if not file['is_directory']:
                size = file['file_size']
                if size > 1024 ** 3:
                    size_str = f"{size / (1024 ** 3):.2f} GB"
                elif size > 1024 ** 2:
                    size_str = f"{size / (1024 ** 2):.2f} MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.2f} KB"
                else:
                    size_str = f"{size} B"
                item_text += f" ({size_str})"
            
            self.files_list.addItem(item_text)
    
    def load_photos(self):
        self.photos_list.clear()
        photos = self.client.get_photos()
        
        for photo in photos:
            self.photos_list.addItem(photo['original_filename'])
    
    def handle_file_double_click(self, item):
        row = self.files_list.row(item)
        files = self.client.get_files(self.current_parent_id)
        
        if row < len(files):
            file = files[row]
            if file['is_directory']:
                self.path_history.append((self.current_parent_id, file['original_filename']))
                self.current_parent_id = file['id']
                self.load_files()
            else:
                self.download_file(file['id'], file['original_filename'])
    
    def go_back(self):
        if self.path_history:
            self.current_parent_id, _ = self.path_history.pop()
            self.load_files()
    
    def refresh_files(self):
        self.load_files()
        self.load_photos()
        self.load_user_info()
    
    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        if files:
            self.start_upload(files, self.current_parent_id, is_photo=False)
    
    def upload_photos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Photos", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if files:
            self.start_upload(files, is_photo=True)
    
    def start_upload(self, file_paths, parent_id=None, is_photo=False):
        self.upload_thread = UploadThread(self.client, file_paths, parent_id, is_photo)
        self.upload_thread.progress.connect(self.update_upload_progress)
        self.upload_thread.finished.connect(self.upload_finished)
        self.upload_thread.start()
        
        self.status_bar.showMessage("Uploading...")
    
    def update_upload_progress(self, value):
        self.status_bar.showMessage(f"Uploading... {value}%")
    
    def upload_finished(self, success, message):
        if success:
            self.status_bar.showMessage("Upload complete!", 3000)
            self.refresh_files()
        else:
            QMessageBox.warning(self, "Upload Failed", message)
            self.status_bar.clear()
    
    def new_folder(self):
        name, ok = self.get_text_input("New Folder", "Enter folder name:")
        if ok and name:
            if self.client.create_folder(name, self.current_parent_id):
                self.load_files()
            else:
                QMessageBox.warning(self, "Failed", "Could not create folder")
    
    def download_file(self, file_id, filename):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", filename)
        if save_path:
            if self.client.download_file(file_id, save_path):
                QMessageBox.information(self, "Success", "File downloaded successfully")
            else:
                QMessageBox.warning(self, "Failed", "Could not download file")
    
    def get_text_input(self, title, label):
        from PySide6.QtWidgets import QInputDialog
        return QInputDialog.getText(self, title, label)

def main():
    app = QApplication(sys.argv)
    
    client = APIClient()
    
    login_window = LoginWindow(client, lambda: None)
    login_window.show()
    
    def on_login():
        main_window = MainWindow(client)
        main_window.show()
        login_window.close()
    
    login_window.on_login_success = on_login
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
