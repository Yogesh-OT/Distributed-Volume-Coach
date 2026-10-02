# Retrofit, OkHttp, kotlinx.serialization and Room ship their own R8 rules.
# Keep the serializable DTOs' generated serializers.
-keepclassmembers class app.dvcoach.** {
    *** Companion;
}
-keepclasseswithmembers class app.dvcoach.** {
    kotlinx.serialization.KSerializer serializer(...);
}
