"""Exercise the installed APK through Android's accessibility tree (API 30 emulator)."""
import re
import subprocess
import time
from datetime import datetime, timedelta
from xml.etree import ElementTree

PACKAGE = "ru.razgrom.diary.python"
ACTIVITY = PACKAGE + "/ru.razgrom.diary.Main"

def adb(*args):
    return subprocess.check_output(["adb", *args], text=True, errors="replace")

def shell(*args):
    return adb("shell", *args)

def tree():
    shell("uiautomator", "dump", "/sdcard/window.xml")
    return ElementTree.fromstring(shell("cat", "/sdcard/window.xml"))

def node(label, prefix=False):
    until = time.monotonic() + 25
    while time.monotonic() < until:
        for item in tree().iter("node"):
            for key in ("text", "content-desc"):
                value = item.get(key,"")
                if (prefix and value.startswith(label)) or value == label:
                    return item
        # A crashed app cannot expose the expected screen.
        if not shell("pidof", PACKAGE).strip():
            raise RuntimeError("App exited while looking for " + label)
    raise AssertionError("Missing control: " + label)

def tap(label, prefix=False):
    x,y,X,Y = map(int,re.findall(r"\d+",node(label,prefix).get("bounds")))
    shell("input","tap",str((x+X)//2),str((y+Y)//2))

def field(label, value):
    for item in tree().iter("node"):
        if item.get("content-desc")==label and item.get("class")=="android.widget.EditText":
            x,y,X,Y = map(int,re.findall(r"\d+",item.get("bounds")))
            shell("input","tap",str((x+X)//2),str((y+Y)//2))
            shell("input","text",value)
            shell("input","keyevent","4")
            return
    raise AssertionError(label)

def launch():
    shell("am","start","-W","-n",ACTIVITY)
    node("+ Добавить задачу")

def create(title, clock=None):
    tap("+ Добавить задачу")
    node("Сохранить")
    field("Название",title)
    if clock:
        field("Время (ЧЧ:ММ)", clock)
    tap("Сохранить")
    node(title)

def main():
    shell("wm","size","1080x2400")
    shell("wm","density","320")
    shell("svc","wifi","disable")
    shell("svc","data","disable")
    launch()
    node("На этот день задач нет")
    create("OfflineTask")
    tap("Неделя")
    node("Предыдущая неделя")
    # Select the only day with one task.
    target = next(n.get("text") for n in tree().iter("node") if re.search(r" · 1$",n.get("text","")))
    tap(target)
    tap("Выполнить ·",True)
    node("Выполнена ·",True)
    shell("am","force-stop",PACKAGE)
    launch()
    node("OfflineTask")
    node("Выполнена ·",True)
    tap("OfflineTask")
    tap("Удалить")
    tap("Удалить")
    node("На этот день задач нет")
    print("PASS TC-12 offline create, week selection, completion, restart, deletion",flush=True)
    tap("Настройки")
    tap("15")
    tap("Сохранить настройки")
    tap("Настройки")
    assert node("15").get("checked")=="true"
    tap("0")
    tap("Сохранить настройки")
    clock=datetime.fromisoformat(shell("date","+%Y-%m-%dT%H:%M:%S").strip())
    due=clock+timedelta(minutes=2)
    if due.date()!=clock.date():
        raise RuntimeError("Run outside the midnight transition")
    create("AlarmProbe",due.strftime("%H:%M"))
    shell("input","keyevent","3")
    shell("am","kill",PACKAGE)
    until=time.monotonic()+145
    while time.monotonic()<until:
        if "AlarmProbe" in shell("dumpsys","notification","--noredact"):
            print("PASS TC-11 notification received with app in background",flush=True)
            return
        time.sleep(2)
    raise AssertionError("Notification not received")

if __name__=="__main__":
    main()
