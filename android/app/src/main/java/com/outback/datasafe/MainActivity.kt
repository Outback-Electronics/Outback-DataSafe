package com.outback.datasafe

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.GridLayoutManager
import com.bumptech.glide.Glide
import com.outback.datasafe.databinding.ActivityMainBinding
import java.io.File

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var viewModel: MainViewModel
    private lateinit var apiClient: ApiClient
    private lateinit var filesAdapter: FilesAdapter
    private lateinit var photosAdapter: PhotosAdapter
    
    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        if (uris.isNotEmpty()) {
            viewModel.uploadFiles(uris)
        }
    }
    
    private val photoPickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        if (uris.isNotEmpty()) {
            viewModel.uploadPhotos(uris)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Initialize API client
        apiClient = ApiClient("http://10.0.2.2:8000") // For emulator, use your server IP for real device
        
        // Initialize ViewModel
        viewModel = ViewModelProvider(this)[MainViewModel::class.java]
        viewModel.setApiClient(apiClient)
        
        // Setup adapters
        setupAdapters()
        
        // Setup listeners
        setupListeners()
        
        // Observe ViewModel
        observeViewModel()
        
        // Check if logged in
        viewModel.checkAuth()
    }
    
    private fun setupAdapters() {
        filesAdapter = FilesAdapter { file ->
            if (file.is_directory) {
                viewModel.navigateToDirectory(file.id)
            } else {
                viewModel.downloadFile(file.id, file.original_filename)
            }
        }
        
        binding.filesRecyclerView.apply {
            layoutManager = GridLayoutManager(this@MainActivity, 1)
            adapter = filesAdapter
        }
        
        photosAdapter = PhotosAdapter { photo ->
            viewModel.viewPhoto(photo)
        }
        
        binding.photosRecyclerView.apply {
            layoutManager = GridLayoutManager(this@MainActivity, 3)
            adapter = photosAdapter
        }
    }
    
    private fun setupListeners() {
        binding.loginButton.setOnClickListener {
            val username = binding.usernameEditText.text.toString()
            val password = binding.passwordEditText.text.toString()
            viewModel.login(username, password)
        }
        
        binding.registerButton.setOnClickListener {
            val username = binding.usernameEditText.text.toString()
            val email = binding.emailEditText.text.toString()
            val password = binding.passwordEditText.text.toString()
            viewModel.register(username, email, password)
        }
        
        binding.logoutButton.setOnClickListener {
            viewModel.logout()
        }
        
        binding.uploadFilesButton.setOnClickListener {
            filePickerLauncher.launch("*/*")
        }
        
        binding.uploadPhotosButton.setOnClickListener {
            photoPickerLauncher.launch("image/*")
        }
        
        binding.newFolderButton.setOnClickListener {
            viewModel.createFolder("New Folder")
        }
        
        binding.backButton.setOnClickListener {
            viewModel.navigateBack()
        }
        
        binding.refreshButton.setOnClickListener {
            viewModel.refresh()
        }
    }
    
    private fun observeViewModel() {
        viewModel.authState.observe(this) { isLoggedIn ->
            if (isLoggedIn) {
                showMainApp()
                viewModel.loadUserInfo()
                viewModel.loadFiles()
                viewModel.loadPhotos()
            } else {
                showLoginScreen()
            }
        }
        
        viewModel.user.observe(this) { user ->
            binding.quotaTextView.text = "Storage: ${formatBytes(user.used_space)} / ${formatBytes(user.quota)}"
        }
        
        viewModel.files.observe(this) { files ->
            filesAdapter.submitList(files)
        }
        
        viewModel.photos.observe(this) { photos ->
            photosAdapter.submitList(photos)
        }
        
        viewModel.currentPath.observe(this) { path ->
            binding.pathTextView.text = if (path.isEmpty()) "Home" else path.joinToString(" / ")
        }
        
        viewModel.message.observe(this) { message ->
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        }
        
        viewModel.isLoading.observe(this) { isLoading ->
            binding.progressBar.visibility = if (isLoading) android.view.View.VISIBLE else android.view.View.GONE
        }
    }
    
    private fun showLoginScreen() {
        binding.loginLayout.visibility = android.view.View.VISIBLE
        binding.mainLayout.visibility = android.view.View.GONE
    }
    
    private fun showMainApp() {
        binding.loginLayout.visibility = android.view.View.GONE
        binding.mainLayout.visibility = android.view.View.VISIBLE
    }
    
    private fun formatBytes(bytes: Long): String {
        if (bytes < 1024) return "$bytes B"
        if (bytes < 1024 * 1024) return "${bytes / 1024} KB"
        if (bytes < 1024 * 1024 * 1024) return "${bytes / (1024 * 1024)} MB"
        return "${bytes / (1024 * 1024 * 1024)} GB"
    }
    
    fun getFileName(uri: Uri): String {
        var result: String? = null
        if (uri.scheme == "content") {
            contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (index >= 0) {
                        result = cursor.getString(index)
                    }
                }
            }
        }
        if (result == null) {
            result = uri.path
            val cut = result?.lastIndexOf('/')
            if (cut != -1) {
                result = result?.substring(cut!! + 1)
            }
        }
        return result ?: "unknown"
    }
}
