package ru.razgrom.diary;
import android.content.*;
import android.database.Cursor;
import android.database.sqlite.*;
final class Store extends SQLiteOpenHelper {
    Store(Context c){super(c,"razgrom.db",null,1);}
    public void onCreate(SQLiteDatabase db){
        db.execSQL("CREATE TABLE tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,day TEXT NOT NULL,time TEXT NOT NULL,priority INTEGER NOT NULL,done INTEGER NOT NULL DEFAULT 0,remind INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX tasks_day ON tasks(day)");
    }
    public void onUpgrade(SQLiteDatabase db,int from,int to){throw new IllegalStateException("Unknown schema version");}
    long save(long id,String title,String day,String time,int priority,boolean remind){
        Rules.validate(title,day,time,priority);
        ContentValues v=new ContentValues();
        v.put("title",title.trim());v.put("day",day);v.put("time",time);v.put("priority",priority);v.put("remind",remind?1:0);
        if(id==0)return getWritableDatabase().insertOrThrow("tasks",null,v);
        getWritableDatabase().update("tasks",v,"id=?",new String[]{Long.toString(id)});return id;
    }
    Cursor range(String start,String end){return getReadableDatabase().rawQuery("SELECT id,title,day,time,priority,done,remind FROM tasks WHERE day BETWEEN ? AND ? ORDER BY day,done,time='',time,priority DESC,id",new String[]{start,end});}
}
