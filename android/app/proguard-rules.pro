# Kotlinx Serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class kotlinx.serialization.json.** { kotlinx.serialization.KSerializer serializer(...); }
-keep,includedescriptorclasses class com.ganeshvisarjan.fieldtracker.**$$serializer { *; }
-keepclassmembers class com.ganeshvisarjan.fieldtracker.** { *** Companion; }
-keepclasseswithmembers class com.ganeshvisarjan.fieldtracker.** { kotlinx.serialization.KSerializer serializer(...); }

# Room
-keep class * extends androidx.room.RoomDatabase

# Retrofit / OkHttp
-dontwarn okhttp3.**
-dontwarn retrofit2.**
-keepattributes Signature, Exceptions

# Hilt / Dagger handled automatically by the Hilt Gradle plugin.
