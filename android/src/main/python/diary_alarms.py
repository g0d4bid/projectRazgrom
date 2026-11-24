from contextlib import closing
from datetime import datetime
from android.app import AlarmManager, Notification, NotificationChannel, NotificationManager, PendingIntent
from android.content import BroadcastReceiver, Context, Intent
from android.net import Uri
from android.os import Build
from java import static_proxy, Override, jvoid, jlong, jint
from razgrom_core import TaskRepository, ReminderPlanner

FIRE = "ru.razgrom.diary.FIRE"

def repository(ctx):
    return TaskRepository(str(ctx.getFilesDir().getAbsolutePath()) + "/razgrom.db")

def preferences(ctx):
    return ctx.getSharedPreferences("reminders", 0)

def ticket(ctx, task_id):
    intent = Intent(FIRE).setClassName(ctx, "ru.razgrom.diary.Alarms")
    intent.setData(Uri.parse("razgrom:task/" + str(task_id)))
    return PendingIntent.getBroadcast(ctx, 0, intent, PendingIntent.FLAG_IMMUTABLE)

def sync(ctx, task_id, task):
    manager = ctx.getSystemService(Context.ALARM_SERVICE)
    alarm = ticket(ctx, task_id)
    manager.cancel(alarm)
    ctx.getSystemService(Context.NOTIFICATION_SERVICE).cancel(str(task_id), 1)
    prefs = preferences(ctx)
    if task is None or not prefs.getBoolean("enabled", True):
        return
    due = ReminderPlanner(prefs.getInt("minutes", 0)).fire_time(task)
    if due is None or due <= datetime.now():
        return
    when = jlong(int(due.timestamp() * 1000))
    if Build.VERSION.SDK_INT < 31 or manager.canScheduleExactAlarms():
        manager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, when, alarm)
    else:
        manager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, when, alarm)

def reschedule(ctx, repo):
    for task in repo.active_with_reminders():
        sync(ctx, task.id, task)

class Alarms(static_proxy(BroadcastReceiver, package="ru.razgrom.diary")):
    @Override(jvoid, [Context, Intent])
    def onReceive(self, ctx, event):
        with closing(repository(ctx)) as repo:
            if event.getAction() != FIRE:
                reschedule(ctx, repo)
                return
            task = repo.get(int(str(event.getData()).rsplit("/", 1)[1]))
            if not task or task.is_done or not task.remind or not preferences(ctx).getBoolean("enabled", True):
                return
            nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE)
            nm.createNotificationChannel(NotificationChannel("tasks", "Напоминания", NotificationManager.IMPORTANCE_HIGH))
            if nm.areNotificationsEnabled():
                launch = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName())
                tap = PendingIntent.getActivity(ctx, 0, launch, PendingIntent.FLAG_IMMUTABLE)
                notification = (Notification.Builder(ctx, "tasks").setContentTitle("Разгром")
                                .setContentText(task.title).setSmallIcon(jint(17301550))
                                .setAutoCancel(True).setContentIntent(tap).build())
                nm.notify(str(task.id), 1, notification)
