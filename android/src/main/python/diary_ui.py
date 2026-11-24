from dataclasses import replace
from datetime import date, timedelta
import sqlite3

from java import static_proxy, dynamic_proxy, Override, jvoid, jint
from android.app import Activity, AlertDialog
from android.content import Context, Intent, DialogInterface
from android.net import Uri
from android.os import Build, Bundle
from android.view import View
from android.widget import LinearLayout, TextView, Button, CheckBox, EditText, ScrollView, RadioGroup, RadioButton
from diary_alarms import preferences, repository, reschedule, sync
from razgrom_core import Task, week_of

LEVELS = ("Низкий", "Средний", "Высокий")
DAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

class Click(dynamic_proxy(View.OnClickListener)):
    def __init__(self, action):
        super().__init__()
        self.action = action

    def onClick(self, view):
        self.action()

class Confirm(dynamic_proxy(DialogInterface.OnClickListener)):
    def __init__(self, action):
        super().__init__()
        self.action = action

    def onClick(self, dialog, which):
        self.action()

class Main(static_proxy(Activity, package="ru.razgrom.diary")):
    @Override(jvoid, [Bundle])
    def onCreate(self, state):
        Activity.onCreate(self, state)
        self.repo = repository(self)
        self.day = date.today()
        self.home()
        if Build.VERSION.SDK_INT >= 33 and self.checkSelfPermission("android.permission.POST_NOTIFICATIONS") != 0:
            self.requestPermissions(["android.permission.POST_NOTIFICATIONS"], 1)

    @Override(jvoid, [])
    def onDestroy(self):
        self.repo.close()
        Activity.onDestroy(self)

    @Override(jvoid, [])
    def onBackPressed(self):
        if self.page == "day":
            Activity.onBackPressed(self)
        else:
            self.home()

    def screen(self, key, heading):
        self.page = key
        scroll = ScrollView(self)
        scroll.setFitsSystemWindows(True)
        self.panel = LinearLayout(self)
        self.panel.setOrientation(1)
        pad = int(16 * self.getResources().getDisplayMetrics().density)
        self.panel.setPadding(pad, pad, pad, pad)
        scroll.addView(self.panel)
        self.setContentView(scroll)
        self.label(heading, 26)

    def label(self, value, size=16):
        item = TextView(self)
        item.setText(value)
        item.setTextSize(float(size))
        self.panel.addView(item)
        return item

    def button(self, title, action, parent=None):
        widget = Button(self)
        widget.setAllCaps(False)
        widget.setText(title)
        widget.setOnClickListener(Click(action))
        (parent if parent is not None else self.panel).addView(widget)
        return widget

    def check(self, title, checked):
        widget = CheckBox(self)
        widget.setText(title)
        widget.setChecked(checked)
        self.panel.addView(widget)
        return widget

    def field(self, title, value):
        self.label(title)
        edit = EditText(self)
        edit.setSingleLine(True)
        edit.setContentDescription(title)
        edit.setText(value)
        self.panel.addView(edit)
        return edit

    def choices(self, title, values, selected):
        self.label(title)
        group = RadioGroup(self)
        group.setOrientation(0)
        ids = []
        for index, value in enumerate(values):
            option = RadioButton(self)
            option.setId(View.generateViewId())
            ids.append(option.getId())
            option.setText(value)
            group.addView(option)
        group.check(ids[selected])
        self.panel.addView(group)
        return lambda: ids.index(group.getCheckedRadioButtonId())

    def select_day(self, day):
        self.day = day
        self.home()

    def home(self):
        self.screen("day", "Сегодня" if self.day == date.today() else "План на день")
        self.label(self.day.strftime("%d.%m.%Y"))
        self.button("+ Добавить задачу", lambda: self.form(Task("", self.day.isoformat())))
        bar = LinearLayout(self)
        self.panel.addView(bar)
        self.button("Сегодня", lambda: self.select_day(date.today()), bar)
        self.button("Неделя", lambda: self.week(self.day), bar)
        self.button("Настройки", self.settings, bar)
        tasks = self.repo.for_day(self.day.isoformat())
        if not tasks:
            self.label("На этот день задач нет")
        for task in tasks:
            self.button(task.title, lambda t=task: self.form(t))
            status = ("Выполнена" if task.is_done else "Выполнить")
            box = self.check(f"{status} · {task.due_time or 'Весь день'} · {LEVELS[task.priority]}", task.is_done)
            box.setOnClickListener(Click(lambda t=task: self.toggle(t)))

    def toggle(self, task):
        self.repo.set_done(task.id, not task.is_done)
        sync(self, task.id, self.repo.get(task.id))
        self.home()

    def week(self, anchor):
        first, last = week_of(anchor)
        monday = date.fromisoformat(first)
        counts = self.repo.count_by_day(first, last)
        self.screen("week", "Неделя")
        self.label(f"{first} — {last}")
        for i, name in enumerate(DAYS):
            day = monday + timedelta(days=i)
            self.button(f"{name} {day:%d.%m} · {counts.get(day.isoformat(), 0)}",
                        lambda d=day: self.select_day(d))
        self.button("Предыдущая неделя", lambda: self.week(monday - timedelta(days=7)))
        self.button("Следующая неделя", lambda: self.week(monday + timedelta(days=7)))
        self.button("Сегодня", lambda: self.select_day(date.today()))

    def form(self, task):
        self.screen("form", "Новая задача" if task.id is None else "Изменить задачу")
        title = self.field("Название", task.title)
        day = self.field("Дата (ГГГГ-ММ-ДД)", task.due_date)
        clock = self.field("Время (ЧЧ:ММ)", task.due_time or "")
        priority = self.choices("Приоритет", LEVELS, task.priority)
        remind = self.check("Напомнить", task.remind)
        error = self.label("")

        def save():
            edited = replace(task, title=str(title.getText().toString()).strip(),
                             due_date=str(day.getText().toString()).strip(),
                             due_time=str(clock.getText().toString()).strip() or None,
                             priority=priority(), remind=remind.isChecked())
            if not 1 <= len(edited.title) <= 120:
                title.setError("Введите от 1 до 120 символов")
                return
            try:
                if task.id is None:
                    self.repo.create(edited)
                else:
                    self.repo.update(edited)
            except sqlite3.IntegrityError as exc:
                error.setText(str(exc))
                return
            sync(self, edited.id, edited)
            self.select_day(date.fromisoformat(edited.due_date))

        self.button("Сохранить", save)
        self.button("Отмена", self.home)
        if task.id is not None:
            def remove():
                self.repo.delete(task.id)
                sync(self, task.id, None)
                self.home()
            self.button("Удалить", lambda: AlertDialog.Builder(self).setMessage("Удалить задачу?")
                        .setNegativeButton("Отмена", None).setPositiveButton("Удалить", Confirm(remove)).show())

    def settings(self):
        self.screen("settings", "Настройки уведомлений")
        prefs = preferences(self)
        enabled = self.check("Уведомления включены", prefs.getBoolean("enabled", True))
        offsets = [0, 5, 15, 30, 60]
        selected = self.choices("За сколько минут напомнить", [str(x) for x in offsets],
                                offsets.index(prefs.getInt("minutes", 0)))
        def save():
            prefs.edit().putBoolean("enabled", enabled.isChecked()).putInt("minutes", offsets[selected()]).apply()
            reschedule(self, self.repo)
            self.home()
        self.button("Сохранить настройки", save)
        if Build.VERSION.SDK_INT >= 31 and not self.getSystemService(Context.ALARM_SERVICE).canScheduleExactAlarms():
            self.label("Для доставки точно в срок разрешите точные сигналы в Android.")
            self.button("Разрешить точные сигналы", lambda: self.startActivity(Intent(
                "android.settings.REQUEST_SCHEDULE_EXACT_ALARM", Uri.parse("package:" + self.getPackageName()))))
