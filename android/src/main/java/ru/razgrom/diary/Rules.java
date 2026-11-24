package ru.razgrom.diary;
import java.time.LocalDate;
import java.time.LocalTime;
final class Rules {
    static void validate(String title, String day, String time, int priority) {
        if (title.trim().isEmpty() || title.trim().length()>120) throw new IllegalArgumentException("Введите название до 120 символов");
        LocalDate.parse(day);
        if (!time.isEmpty()) {
            if (!time.matches("[0-9]{2}:[0-9]{2}")) throw new IllegalArgumentException("Введите время в формате ЧЧ:ММ");
            LocalTime.parse(time);
        }
        if (priority<0 || priority>2) throw new IllegalArgumentException("Проверьте приоритет");
    }
}
