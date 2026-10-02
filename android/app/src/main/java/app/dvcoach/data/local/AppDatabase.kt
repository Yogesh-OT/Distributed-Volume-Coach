package app.dvcoach.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [LocalProfile::class, PlanEntity::class, PlannedSetEntity::class, SetLogEntity::class, CheckinEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun profileDao(): ProfileDao
    abstract fun planDao(): PlanDao
    abstract fun logDao(): LogDao
    abstract fun checkinDao(): CheckinDao

    companion object {
        fun build(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "dvcoach.db").build()
    }
}
