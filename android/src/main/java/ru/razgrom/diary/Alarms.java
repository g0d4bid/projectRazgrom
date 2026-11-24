package ru.razgrom.diary;
import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.os.Build;
import java.time.*;
public class Alarms extends BroadcastReceiver {
    static final String FIRE="ru.razgrom.diary.FIRE";
    static PendingIntent intent(Context c,long id){
        Intent i=new Intent(c,Alarms.class).setAction(FIRE).setData(android.net.Uri.parse("razgrom:task/"+id)).putExtra("id",id);
        return PendingIntent.getBroadcast(c,0,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    }
    static void sync(Context c,long id){
        AlarmManager alarm=c.getSystemService(AlarmManager.class);PendingIntent pi=intent(c,id);
        alarm.cancel(pi);
        c.getSystemService(NotificationManager.class).cancel(Long.toString(id),1);
        try(Store db=new Store(c);Cursor row=db.getReadableDatabase().rawQuery("SELECT day,time FROM tasks WHERE id=? AND done=0 AND remind=1 AND time<>''",new String[]{Long.toString(id)})){
            if(!row.moveToFirst())return;
            long when=LocalDateTime.parse(row.getString(0)+"T"+row.getString(1)).atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
            if(when<=System.currentTimeMillis())return;
            if(Build.VERSION.SDK_INT<31||alarm.canScheduleExactAlarms())alarm.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,when,pi);
            else alarm.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,when,pi);
        }
    }
    public void onReceive(Context c,Intent event){
        try(Store db=new Store(c)){
            if(!FIRE.equals(event.getAction())){
                try(Cursor rows=db.getReadableDatabase().rawQuery("SELECT id FROM tasks WHERE done=0 AND remind=1",null)){while(rows.moveToNext())sync(c,rows.getLong(0));}
                return;
            }
            long id=event.getLongExtra("id",0);
            try(Cursor row=db.getReadableDatabase().rawQuery("SELECT title FROM tasks WHERE id=? AND done=0 AND remind=1",new String[]{Long.toString(id)})){
                if(!row.moveToFirst())return;
                NotificationManager nm=c.getSystemService(NotificationManager.class);
                nm.createNotificationChannel(new NotificationChannel("tasks","Напоминания",NotificationManager.IMPORTANCE_HIGH));
                if(!nm.areNotificationsEnabled())return;
                PendingIntent open=PendingIntent.getActivity(c,0,new Intent(c,Main.class),PendingIntent.FLAG_IMMUTABLE);
                nm.notify(Long.toString(id),1,new Notification.Builder(c,"tasks").setSmallIcon(android.R.drawable.ic_lock_idle_alarm).setContentTitle("Разгром · Напоминание").setContentText(row.getString(0)).setAutoCancel(true).setContentIntent(open).build());
            }
        }
    }
}
