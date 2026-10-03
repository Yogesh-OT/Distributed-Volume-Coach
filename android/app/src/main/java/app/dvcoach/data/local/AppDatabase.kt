package app.dvcoach.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [LocalProfile::class, PlanEntity::class, PlannedSetEntity::class, SetLogEntity::class, CheckinEntity::class],
    version = 2,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun profileDao(): ProfileDao
    abstract fun planDao(): PlanDao
    abstract fun logDao(): LogDao
    abstract fun checkinDao(): CheckinDao

    companion object {
        /** Version 2 adds push-up levels. Existing max tests were standard push-ups (level 4). */
        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE local_profile ADD COLUMN level INTEGER NOT NULL DEFAULT 4")
                db.execSQL("ALTER TABLE plans ADD COLUMN level INTEGER")
            }
        }

        fun build(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "dvcoach.db")
                .addMigrations(MIGRATION_1_2)
                .build()
    }
}
