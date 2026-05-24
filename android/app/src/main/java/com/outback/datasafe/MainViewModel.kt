package com.outback.datasafe

import android.content.Context
import android.net.Uri
import android.util.Log
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import java.io.File
import java.io.FileOutputStream

class MainViewModel : ViewModel() {
    private lateinit var apiClient: ApiClient
    
    private val _authState = MutableLiveData<Boolean>()
    val authState: LiveData<Boolean> = _authState
    
    private val _user = MutableLiveData<User>()
    val user: LiveData<User> = _user
    
    private val _files = MutableLiveData<List<File>>()
    val files: LiveData<List<File>> = _files
    
    private val _photos = MutableLiveData<List<Photo>>()
    val photos: LiveData<List<Photo>> = _photos
    
    private val _currentPath = MutableLiveData<List<String>>()
    val currentPath: LiveData<List<String>> = _currentPath
    
    private val _message = MutableLiveData<String>()
    val message: LiveData<String> = _message
    
    private val _isLoading = MutableLiveData<Boolean>()
    val isLoading: LiveData<Boolean> = _isLoading
    
    private var currentParentId: Int? = null
    private val pathHistory = mutableListOf<Pair<Int?, String>>()
    
    fun setApiClient(client: ApiClient) {
        apiClient = client
    }
    
    fun checkAuth() {
        val token = getAuthToken()
        if (token != null) {
            apiClient.setAuthToken(token)
            _authState.value = true
        } else {
            _authState.value = false
        }
    }
    
    fun login(username: String, password: String) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val response = apiClient.apiService.login(LoginRequest(username, password))
                saveAuthToken(response.access_token)
                apiClient.setAuthToken(response.access_token)
                _authState.value = true
                _message.value = "Login successful"
            } catch (e: Exception) {
                _message.value = "Login failed: ${e.message}"
                Log.e("DataSafe", "Login error", e)
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun register(username: String, email: String, password: String) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                apiClient.apiService.register(RegisterRequest(username, email, password))
                _message.value = "Registration successful, please login"
            } catch (e: Exception) {
                _message.value = "Registration failed: ${e.message}"
                Log.e("DataSafe", "Registration error", e)
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun logout() {
        clearAuthToken()
        apiClient.clearAuthToken()
        _authState.value = false
        currentParentId = null
        pathHistory.clear()
        _currentPath.value = emptyList()
    }
    
    fun loadUserInfo() {
        viewModelScope.launch {
            try {
                val user = apiClient.apiService.getMe()
                _user.value = user
            } catch (e: Exception) {
                Log.e("DataSafe", "Failed to load user info", e)
            }
        }
    }
    
    fun loadFiles(parentId: Int? = currentParentId) {
        viewModelScope.launch {
            try {
                val files = apiClient.apiService.getFiles(parentId)
                _files.value = files
            } catch (e: Exception) {
                _message.value = "Failed to load files: ${e.message}"
                Log.e("DataSafe", "Failed to load files", e)
            }
        }
    }
    
    fun loadPhotos() {
        viewModelScope.launch {
            try {
                val photos = apiClient.apiService.getPhotos(limit = 100)
                _photos.value = photos
            } catch (e: Exception) {
                _message.value = "Failed to load photos: ${e.message}"
                Log.e("DataSafe", "Failed to load photos", e)
            }
        }
    }
    
    fun navigateToDirectory(directoryId: Int) {
        val directory = _files.value?.find { it.id == directoryId }
        if (directory != null) {
            pathHistory.add(currentParentId to directory.original_filename)
            currentParentId = directoryId
            _currentPath.value = pathHistory.map { it.second }
            loadFiles()
        }
    }
    
    fun navigateBack() {
        if (pathHistory.isNotEmpty()) {
            val (parentId, _) = pathHistory.removeAt(pathHistory.size - 1)
            currentParentId = parentId
            _currentPath.value = pathHistory.map { it.second }
            loadFiles()
        }
    }
    
    fun uploadFiles(uris: List<Uri>) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                uris.forEach { uri ->
                    val file = uriToFile(uri)
                    val requestFile = RequestBody.create(
                        "multipart/form-data".toMediaTypeOrNull(),
                        file
                    )
                    val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
                    
                    val parentIdPart = currentParentId?.let {
                        RequestBody.create(
                            "multipart/form-data".toMediaTypeOrNull(),
                            it.toString()
                        )
                    }
                    
                    apiClient.apiService.uploadFile(body, parentIdPart)
                }
                loadFiles()
                loadUserInfo()
                _message.value = "Files uploaded successfully"
            } catch (e: Exception) {
                _message.value = "Upload failed: ${e.message}"
                Log.e("DataSafe", "Upload error", e)
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun uploadPhotos(uris: List<Uri>) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                uris.forEach { uri ->
                    val file = uriToFile(uri)
                    val requestFile = RequestBody.create(
                        "multipart/form-data".toMediaTypeOrNull(),
                        file
                    )
                    val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
                    
                    apiClient.apiService.uploadPhoto(body)
                }
                loadPhotos()
                loadUserInfo()
                _message.value = "Photos uploaded successfully"
            } catch (e: Exception) {
                _message.value = "Upload failed: ${e.message}"
                Log.e("DataSafe", "Upload error", e)
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun createFolder(name: String) {
        viewModelScope.launch {
            try {
                apiClient.apiService.createDirectory(
                    mapOf(
                        "filename" to name,
                        "parent_id" to (currentParentId ?: ""),
                        "is_directory" to true
                    )
                )
                loadFiles()
                _message.value = "Folder created successfully"
            } catch (e: Exception) {
                _message.value = "Failed to create folder: ${e.message}"
                Log.e("DataSafe", "Create folder error", e)
            }
        }
    }
    
    fun downloadFile(fileId: Int, filename: String) {
        viewModelScope.launch {
            try {
                val response = apiClient.apiService.downloadFile(fileId)
                saveFile(response, filename)
                _message.value = "File downloaded successfully"
            } catch (e: Exception) {
                _message.value = "Download failed: ${e.message}"
                Log.e("DataSafe", "Download error", e)
            }
        }
    }
    
    fun viewPhoto(photo: Photo) {
        // Implement photo viewer
        _message.value = "Photo viewer coming soon"
    }
    
    fun refresh() {
        loadUserInfo()
        loadFiles()
        loadPhotos()
    }
    
    private suspend fun uriToFile(uri: Uri): File = withContext(Dispatchers.IO) {
        val inputStream = getApplication<Context>().contentResolver.openInputStream(uri)
        val file = File(getApplication<Context>().cacheDir, "temp_${System.currentTimeMillis()}")
        inputStream?.use { input ->
            FileOutputStream(file).use { output ->
                input.copyTo(output)
            }
        }
        file
    }
    
    private suspend fun saveFile(body: ResponseBody, filename: String) = withContext(Dispatchers.IO) {
        val file = File(
            getApplication<Context>().getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS),
            filename
        )
        file.outputStream().use { output ->
            body.byteStream().copyTo(output)
        }
    }
    
    private fun saveAuthToken(token: String) {
        // Implement token storage (SharedPreferences or EncryptedSharedPreferences)
    }
    
    private fun getAuthToken(): String? {
        // Implement token retrieval
        return null
    }
    
    private fun clearAuthToken() {
        // Implement token clearing
    }
}
