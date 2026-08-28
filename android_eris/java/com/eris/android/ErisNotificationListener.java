package com.eris.android;

import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import java.util.ArrayList;
import java.util.List;

/** Escucha las notificaciones del teléfono para que ERIS pueda leerlas. */
public class ErisNotificationListener extends NotificationListenerService {
    private static final List<String> RECENT = new ArrayList<String>();
    private static final int MAX = 20;
    private static boolean isActive = false;

    public static boolean isActive() {
        return isActive;
    }

    public static List<String> getRecent() {
        synchronized (RECENT) {
            return new ArrayList<String>(RECENT);
        }
    }

    @Override
    public void onListenerConnected() {
        isActive = true;
        synchronized (RECENT) {
            RECENT.clear();
            try {
                StatusBarNotification[] act = getActiveNotifications();
                if (act != null) {
                    for (int i = act.length - 1; i >= 0; i--) seed(act[i]);
                }
            } catch (Exception ignore) { }
        }
    }

    @Override
    public void onListenerDisconnected() {
        isActive = false;
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        synchronized (RECENT) {
            seed(sbn);
        }
    }

    private static void seed(StatusBarNotification sbn) {
        String pkg = sbn.getPackageName();
        String title = "";
        String text = "";
        try {
            CharSequence t = sbn.getNotification().extras
                    .getCharSequence(android.app.Notification.EXTRA_TITLE);
            CharSequence x = sbn.getNotification().extras
                    .getCharSequence(android.app.Notification.EXTRA_TEXT);
            title = t != null ? t.toString() : "";
            text = x != null ? x.toString() : "";
        } catch (Exception ignore) { }
        String line = pkg + (title.isEmpty() ? "" : ": " + title)
                + (text.isEmpty() ? "" : " - " + text);
        RECENT.add(0, line);
        while (RECENT.size() > MAX) RECENT.remove(RECENT.size() - 1);
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) { }
}
