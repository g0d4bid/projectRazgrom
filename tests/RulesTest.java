package ru.razgrom.diary;
public final class RulesTest {
    public static void main(String[] args) {
        Rules.validate("Учёба","2028-02-29","23:59",2);
        Rules.validate("Весь день","2026-11-24","",0);
        rejected("2026-02-30","10:00");
        rejected("2026-11-25","24:00");
        System.out.println("Passed 4 Android input validation cases");
    }
    static void rejected(String day,String time){
        try{Rules.validate("Проверка",day,time,1);}
        catch(java.time.DateTimeException | IllegalArgumentException expected){return;}
        throw new AssertionError("Invalid value accepted: "+day+" "+time);
    }
}
