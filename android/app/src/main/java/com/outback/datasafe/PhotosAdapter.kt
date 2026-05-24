package com.outback.datasafe

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.outback.datasafe.databinding.ItemPhotoBinding

class PhotosAdapter(
    private val onPhotoClick: (Photo) -> Unit
) : ListAdapter<Photo, PhotosAdapter.PhotoViewHolder>(PhotoDiffCallback()) {
    
    private var baseUrl: String = "http://10.0.2.2:8000"
    
    fun setBaseUrl(url: String) {
        baseUrl = url
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PhotoViewHolder {
        val binding = ItemPhotoBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return PhotoViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: PhotoViewHolder, position: Int) {
        holder.bind(getItem(position))
    }
    
    inner class PhotoViewHolder(private val binding: ItemPhotoBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(photo: Photo) {
            val thumbnailUrl = "$baseUrl/api/photos/${photo.id}/thumbnail"
            
            Glide.with(binding.root.context)
                .load(thumbnailUrl)
                .placeholder(android.R.drawable.ic_menu_gallery)
                .error(android.R.drawable.ic_menu_report_image)
                .centerCrop()
                .into(binding.photoImageView)
            
            binding.root.setOnClickListener {
                onPhotoClick(photo)
            }
        }
    }
    
    class PhotoDiffCallback : DiffUtil.ItemCallback<Photo>() {
        override fun areItemsTheSame(oldItem: Photo, newItem: Photo): Boolean {
            return oldItem.id == newItem.id
        }
        
        override fun areContentsTheSame(oldItem: Photo, newItem: Photo): Boolean {
            return oldItem == newItem
        }
    }
}
