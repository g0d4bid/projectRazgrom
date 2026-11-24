package ru.razgrom.diary;
import android.app.*;
import android.os.*;
import android.content.*;
import android.database.Cursor;
import android.view.*;
import android.widget.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

public class Main extends Activity {
    Store store;
    LinearLayout root, list;
    LocalDate selected=LocalDate.now();
    boolean week=false;
    final String[] levels={"Низкий","Средний","Высокий"};
    final DateTimeFormatter display=DateTimeFormatter.ofPattern("dd MMMM, EEE",new Locale("ru"));
    int dp(int n){return (int)(n*getResources().getDisplayMetrics().density+0.5);}
    public void onCreate(Bundle state){
        super.onCreate(state);
        if(state!=null){selected=LocalDate.parse(state.getString("day"));week=state.getBoolean("week");}
        store=new Store(this);root=column();setContentView(root);
        root.setBackgroundColor(0xfff5f4ef);
        root.setOnApplyWindowInsetsListener((v,i)->{root.setPadding(dp(16),i.getSystemWindowInsetTop()+dp(8),dp(16),i.getSystemWindowInsetBottom()+dp(8));return i;});
        refresh();
        if(Build.VERSION.SDK_INT>=33 && checkSelfPermission("android.permission.POST_NOTIFICATIONS")!=0)requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"},1);
    }
    protected void onSaveInstanceState(Bundle b){super.onSaveInstanceState(b);b.putString("day",selected.toString());b.putBoolean("week",week);}
    protected void onDestroy(){store.close();super.onDestroy();}
    LinearLayout column(){LinearLayout l=new LinearLayout(this);l.setOrientation(1);return l;}
    TextView label(String s,int size){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(0xff22342f);t.setPadding(dp(5),dp(4),dp(5),dp(4));return t;}
    Button button(String s,Runnable action){Button b=new Button(this);b.setText(s);b.setAllCaps(false);b.setOnClickListener(v->action.run());return b;}
    void navigate(int days){selected=selected.plusDays(days);refresh();}
    void refresh(){
        root.removeAllViews();
        root.addView(label("Разгром",30));
        LinearLayout nav=new LinearLayout(this);root.addView(nav);
        nav.addView(button("Сегодня",()->{selected=LocalDate.now();week=false;refresh();}));
        nav.addView(button("Неделя",()->{week=true;refresh();}));
        nav.addView(button("Дата",()->pick(selected,date->{selected=date;week=false;refresh();})));
        LocalDate start=week?selected.minusDays(selected.getDayOfWeek().getValue()-1):selected;
        LocalDate end=week?start.plusDays(6):start;
        LinearLayout range=new LinearLayout(this);root.addView(range);
        range.addView(button("‹",()->navigate(week?-7:-1)),dp(48),-2);
        TextView title=label(week?start.format(display)+" – "+end.format(display):selected.format(display),17);
        range.addView(title,new LinearLayout.LayoutParams(0,-2,1));range.addView(button("›",()->navigate(week?7:1)),dp(48),-2);
        ScrollView scroll=new ScrollView(this);list=column();scroll.addView(list);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        try(Cursor r=store.range(start.toString(),end.toString())){
            String last="";
            while(r.moveToNext()){
                final long id=r.getLong(0);String name=r.getString(1),day=r.getString(2),time=r.getString(3);
                int priority=r.getInt(4);boolean done=r.getInt(5)==1,remind=r.getInt(6)==1;
                if(week&&!last.equals(day)){list.addView(label(LocalDate.parse(day).format(display),19));last=day;}
                LinearLayout row=new LinearLayout(this);list.addView(row);CheckBox box=new CheckBox(this);box.setContentDescription("Выполнено: "+name);box.setChecked(done);row.addView(box);
                TextView text=label(name+"\n"+(time.isEmpty()?"Весь день":time)+" · "+levels[priority],16);
                if(done)text.setPaintFlags(text.getPaintFlags()|android.graphics.Paint.STRIKE_THRU_TEXT_FLAG);
                row.addView(text,new LinearLayout.LayoutParams(0,-2,1));
                text.setOnClickListener(v->edit(id,name,LocalDate.parse(day),time,priority,remind));
                box.setOnCheckedChangeListener((b,on)->{ContentValues val=new ContentValues();val.put("done",on?1:0);store.getWritableDatabase().update("tasks",val,"id=?",new String[]{Long.toString(id)});Alarms.sync(this,id);refresh();});
            }
            if(r.getCount()==0)list.addView(label("Задач пока нет",17));
        }
        root.addView(button("+ Добавить задачу",()->edit(0,"",selected,"",1,true)));
    }
    interface DateAction{void accept(LocalDate d);}
    void pick(LocalDate d,DateAction action){new DatePickerDialog(this,(v,y,m,day)->action.accept(LocalDate.of(y,m+1,day)),d.getYear(),d.getMonthValue()-1,d.getDayOfMonth()).show();}
    void edit(long id,String title,LocalDate initial,String oldTime,int priority,boolean remind){
        LinearLayout form=column();form.setPadding(dp(20),dp(8),dp(20),0);
        EditText name=new EditText(this);name.setSingleLine();name.setHint("Название");name.setText(title);form.addView(name);
        LocalDate[] day={initial};String[] time={oldTime};
        Button date=new Button(this);date.setText(day[0].format(display));form.addView(date);
        date.setOnClickListener(v->pick(day[0],d->{day[0]=d;date.setText(d.format(display));}));
        Button clock=new Button(this);clock.setText(time[0].isEmpty()?"Указать время":time[0]);form.addView(clock);
        clock.setOnClickListener(v->{LocalTime t=time[0].isEmpty()?LocalTime.now():LocalTime.parse(time[0]);new TimePickerDialog(this,(w,h,m)->{time[0]=String.format(Locale.ROOT,"%02d:%02d",h,m);clock.setText(time[0]);},t.getHour(),t.getMinute(),true).show();});
        form.addView(button("Без времени",()->{time[0]="";clock.setText("Указать время");}));
        form.addView(label("Приоритет",14));Spinner spin=new Spinner(this);spin.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,levels));spin.setSelection(priority);form.addView(spin);
        CheckBox notify=new CheckBox(this);notify.setText("Напомнить в указанное время");notify.setChecked(remind);form.addView(notify);
        ScrollView pane=new ScrollView(this);pane.addView(form);
        AlertDialog.Builder build=new AlertDialog.Builder(this).setTitle(id==0?"Новая задача":"Изменить задачу").setView(pane).setNegativeButton("Отмена",null).setPositiveButton("Сохранить",null);
        if(id!=0)build.setNeutralButton("Удалить",(dialog,w)->new AlertDialog.Builder(this).setMessage("Удалить задачу?").setNegativeButton("Отмена",null).setPositiveButton("Удалить",(ok,k)->{store.getWritableDatabase().delete("tasks","id=?",new String[]{Long.toString(id)});Alarms.sync(this,id);refresh();}).show());
        AlertDialog dialog=build.show();dialog.getButton(-1).setOnClickListener(v->{
            long saved;
            try{saved=store.save(id,name.getText().toString(),day[0].toString(),time[0],spin.getSelectedItemPosition(),notify.isChecked());}
            catch(IllegalArgumentException ex){name.setError(ex.getMessage());return;}
            Alarms.sync(this,saved);selected=day[0];dialog.dismiss();refresh();
            if(notify.isChecked()&&!time[0].isEmpty()&&Build.VERSION.SDK_INT>=31&&!getSystemService(AlarmManager.class).canScheduleExactAlarms())
                new AlertDialog.Builder(this).setMessage("Для напоминаний точно в срок разрешите точные сигналы в настройках Android. Иначе уведомление может прийти позже.").setNegativeButton("Позже",null).setPositiveButton("Настройки",(a,b)->startActivity(new Intent(android.provider.Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,android.net.Uri.parse("package:"+getPackageName())))).show();
        });
    }
}
