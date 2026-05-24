package com.outback.datasafe

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.outback.datasafe.databinding.ItemFileBinding

class FilesAdapter(
    private val onFileClick: (File) -> Unit
) : ListAdapter<File, FilesAdapter.FileViewHolder>(FileDiffCallback()) {
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): FileViewHolder {
        val binding = ItemFileBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return FileViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: FileViewHolder, position: Int) {
        holder.bind(getItem(position))
    }
    
    inner class FileViewHolder(private val binding: ItemFileBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(file: File) {
            binding.fileNameTextView.text = file.original_filename
            binding.fileSizeTextView.text = if (file.is_directory) "" else formatBytes(file.file_size)
            binding.fileIconTextView.text = if (file.is_directory) "📁" else getFileIcon(file.mime_type)
            
            binding.root.setOnClickListener {
                onFileClick(file)
            }
        }
        
        private fun formatBytes(bytes: Long): String {
            if (bytes < 1024) return "$bytes B"
            if (bytes < 1024 * 1024) return "${bytes / 1024} KB"
            if (bytes < 1024 * 1024 * 1024) return "${bytes / (1024 * 1024)} MB"
            return "${bytes / (1024 * 1024 * 1024)} GB"
        }
        
        private fun getFileIcon(mimeType: String?): String {
            return when {
                mimeType?.startsWith("image/") == true -> "🖼️"
                mimeType?.startsWith("video/") == true -> "🎬"
                mimeType?.startsWith("audio/") == true -> "🎵"
                mimeType?.contains("pdf") == true -> "📕"
                mimeType?.contains("word") == true -> "📘"
                mimeType?.contains("excel") == true -> "📗"
                mimeType?.contains("powerpoint") == true -> "📙"
                else -> "📄"
            }
        }
    }
    
    class FileDiffCallback : DiffUtil.ItemCallback<File>() {
        override fun areItemsTheSame(oldItem: File, newItem: File): Boolean {
            return oldItem.id == newItem.id
        }
        
        override fun areContentsTheSame(oldItem: File, newItem: File): Boolean {
            return oldItem == newItem
        }
    }
}
