package app.dvcoach.reminders

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import app.dvcoach.MainActivity
import app.dvcoach.R
import app.dvcoach.engine.Rating
import app.dvcoach.engine.SetState

object Notifier {
    private const val CHANNEL_SETS = "sets"
    private const val CHANNEL_CHECKIN = "checkin"
    private const val CHECKIN_ID = 1

    fun createChannels(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_SETS, "Set prompts", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "A prompt for each set during your training window"
            }
        )
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_CHECKIN, "Morning check-in", NotificationManager.IMPORTANCE_DEFAULT).apply {
                description = "A reminder to check in after you wake up"
            }
        )
    }

    fun canPost(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission") // checked by canPost()
    fun showSetPrompt(context: Context, date: String, set: SetState, allRefs: List<String>) {
        if (!canPost(context)) return
        // Clear older prompts so a stale "Done" can't be tapped for the wrong set.
        allRefs.filter { it != set.ref }.forEach { cancelSetPrompt(context, it) }

        val notification = NotificationCompat.Builder(context, CHANNEL_SETS)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("${set.targetReps} push-ups")
            .setContentText("Stop with a few reps left in the tank.")
            .setContentIntent(openApp(context))
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            // Android shows at most three buttons. Easy, Skip and Pain are in the app.
            .addAction(0, "Done", LogActionReceiver.log(context, date, set.ref, Rating.SOLID))
            .addAction(0, "Hard", LogActionReceiver.log(context, date, set.ref, Rating.HARD))
            .addAction(0, "Snooze 15 min", LogActionReceiver.snooze(context, date, set.ref))
            .build()
        NotificationManagerCompat.from(context).notify(idFor(set.ref), notification)
    }

    fun cancelSetPrompt(context: Context, ref: String) {
        NotificationManagerCompat.from(context).cancel(idFor(ref))
    }

    fun cancelAllSetPrompts(context: Context) {
        for (i in 1..PromptScheduler.MAX_SETS) cancelSetPrompt(context, "s$i")
    }

    @SuppressLint("MissingPermission") // checked by canPost()
    fun showCheckinReminder(context: Context) {
        if (!canPost(context)) return
        val notification = NotificationCompat.Builder(context, CHANNEL_CHECKIN)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Morning check-in")
            .setContentText("Three quick questions, then today's plan.")
            .setContentIntent(openApp(context))
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(CHECKIN_ID, notification)
    }

    private fun idFor(ref: String): Int = 100 + (ref.removePrefix("s").toIntOrNull() ?: 0)

    private fun openApp(context: Context): PendingIntent =
        PendingIntent.getActivity(
            context,
            0,
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
}
