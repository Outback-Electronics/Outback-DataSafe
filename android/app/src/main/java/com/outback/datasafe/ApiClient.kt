package com.outback.datasafe

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

// Data models
data class User(
    val id: Int,
    val username: String,
    val email: String,
    val quota: Long,
    val used_space: Long,
    val is_admin: Boolean
)

data class LoginRequest(
    val username: String,
    val password: String
)

data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String
)

data class TokenResponse(
    val access_token: String,
    val token_type: String
)

data class File(
    val id: Int,
    val filename: String,
    val original_filename: String,
    val file_size: Long,
    val mime_type: String?,
    val created_at: String,
    val modified_at: String,
    val parent_id: Int?,
    val is_directory: Boolean
)

data class Photo(
    val id: Int,
    val file_path: String,
    val thumbnail_path: String?,
    val width: Int,
    val height: Int,
    val capture_date: String?,
    val location: String?,
    val created_at: String
)

// API Interface
interface ApiService {
    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): TokenResponse
    
    @POST("api/auth/register")
    suspend fun register(@Body request: RegisterRequest): User
    
    @GET("api/auth/me")
    suspend fun getMe(): User
    
    @GET("api/files")
    suspend fun getFiles(@Query("parent_id") parentId: Int? = null): List<File>
    
    @Multipart
    @POST("api/files")
    suspend fun uploadFile(
        @Part file: okhttp3.MultipartBody.Part,
        @Part parent_id: okhttp3.MultipartBody.Part? = null
    ): File
    
    @POST("api/files/directory")
    suspend fun createDirectory(@Body request: Map<String, Any>): File
    
    @GET("api/files/{file_id}/download")
    suspend fun downloadFile(@Path("file_id") fileId: Int): okhttp3.ResponseBody
    
    @DELETE("api/files/{file_id}")
    suspend fun deleteFile(@Path("file_id") fileId: Int)
    
    @GET("api/photos")
    suspend fun getPhotos(
        @Query("limit") limit: Int = 100,
        @Query("offset") offset: Int = 0
    ): List<Photo>
    
    @Multipart
    @POST("api/photos")
    suspend fun uploadPhoto(@Part file: okhttp3.MultipartBody.Part): Photo
}

// API Client
class ApiClient(private val baseUrl: String = "http://YOUR_SERVER_IP:8000") {
    private var authToken: String? = null
    
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }
    
    private val authInterceptor = Interceptor { chain ->
        val original = chain.request()
        authToken?.let {
            val request = original.newBuilder()
                .header("Authorization", "Bearer $it")
                .build()
            chain.proceed(request)
        } ?: chain.proceed(original)
    }
    
    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .addInterceptor(authInterceptor)
        .build()
    
    private val retrofit = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    val apiService: ApiService = retrofit.create(ApiService::class.java)
    
    fun setAuthToken(token: String) {
        authToken = token
    }
    
    fun clearAuthToken() {
        authToken = null
    }
    
    fun updateBaseUrl(newBaseUrl: String) {
        // Note: In production, you'd want to recreate the Retrofit instance
    }
}
