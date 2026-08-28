package com.eris.android;

import android.app.ActivityManager;
import android.app.Notification;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Path;
import android.net.wifi.WifiManager;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Environment;
import android.os.StatFs;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Ejecuta las herramientas de Android que ERIS puede llamar. */
public final class ErisTools {

    private ErisTools() {}

    public static boolean needCheck() {
        return !ErisAccessibilityService.isRunning();
    }

    public static String quickAction(Context ctx, String name) {
        return runTool(ctx, name, new JSONObject());
    }

    public static String runTool(Context ctx, String name, JSONObject args) {
        try {
            if (name.equals("android_status")) return status(ctx);
            if (name.equals("android_battery")) return battery(ctx);
            if (name.equals("android_apps")) return listApps(ctx, args.optString("q", ""));
            if (name.equals("android_app_info")) return appInfo(ctx, args.optString("app", ""));
            if (name.equals("android_open_app")) return openApp(ctx, args.optString("app", ""));
            if (name.equals("android_screen")) return screen();
            if (name.equals("android_screen_indexed")) return screenIndexed();
            if (name.equals("android_foreground")) return foreground();
            if (name.equals("android_windows")) return windows();
            if (name.equals("android_closed")) return closed();
            if (name.equals("android_device")) return device(ctx);
            if (name.equals("android_tap_text")) return tapText(args.optString("text", ""));
            if (name.equals("android_tap_index")) return tapIndex(args.optInt("index", -1));
            if (name.equals("android_tap")) return tap(args.optInt("x", -1), args.optInt("y", -1));
            if (name.equals("android_swipe")) return swipe(
                    args.optInt("x1", 540), args.optInt("y1", 800),
                    args.optInt("x2", 540), args.optInt("y2", 400),
                    args.optInt("ms", 300));
            if (name.equals("android_scroll")) return scroll(args.optString("direction", "down"));
            if (name.equals("android_scroll_to")) return scrollTo(args.optString("text", ""));
            if (name.equals("android_type")) return type(args.optString("text", ""));
            if (name.equals("android_home")) return home();
            if (name.equals("android_back")) return back();
            if (name.equals("android_recent")) return recent();
            if (name.equals("android_notifications")) return notifications();
            if (name.equals("android_memory_save")) return ErisMemory.addFact(ctx, args.optString("fact", ""));
            if (name.equals("android_memory_recall")) return ErisMemory.recallFacts(ctx);
            if (name.equals("android_memory_export")) return ErisMemory.exportSync(ctx);
            if (name.equals("android_memory_import")) return ErisMemory.importSync(ctx);
            return "Herramienta desconocida: " + name;
        } catch (Exception e) {
            return "Error en " + name + ": " + e.getMessage();
        }
    }

    private static String needAccessibility() {
        return "Accesibilidad de ERIS no activada. Activá 'ERIS' en Configuración > Accesibilidad.";
    }

    private static String status(Context ctx) {
        StringBuilder sb = new StringBuilder();
        String bat = battery(ctx);
        if (bat.startsWith("Batería: ")) bat = bat.substring("Batería: ".length());
        sb.append("Batería: ").append(bat).append("\n");
        try {
            WifiManager wm = (WifiManager) ctx.getApplicationContext()
                    .getSystemService(Context.WIFI_SERVICE);
            String ssid = wm != null && wm.getConnectionInfo() != null
                    ? wm.getConnectionInfo().getSSID() : "?";
            sb.append("WiFi: ").append(ssid).append("\n");
        } catch (Exception ignore) { }
        sb.append("Modelo: ").append(Build.MANUFACTURER).append(" ")
                .append(Build.MODEL).append("\n");
        sb.append("Accesibilidad: ").append(
                ErisAccessibilityService.isRunning() ? "ACTIVA (puedo tocar la pantalla)"
                                                     : "INACTIVA (no puedo tocar aún)");
        return sb.toString();
    }

    public static String battery(Context ctx) {
        try {
            BatteryManager bm = (BatteryManager) ctx.getSystemService(Context.BATTERY_SERVICE);
            int pct = bm != null ? bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) : -1;
            return pct >= 0 ? "Batería: " + pct + "%" : "Batería: ?";
        } catch (Exception e) {
            return "No pude leer la batería: " + e.getMessage();
        }
    }

    private static String listApps(Context ctx, String q) {
        PackageManager pm = ctx.getPackageManager();
        Intent main = new Intent(Intent.ACTION_MAIN);
        main.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> ris = pm.queryIntentActivities(main, 0);
        List<String> names = new ArrayList<String>();
        String query = q.trim().toLowerCase();
        for (ResolveInfo ri : ris) {
            try {
                String label = ri.loadLabel(pm).toString();
                String pkg = ri.activityInfo.packageName;
                if (!query.isEmpty() && !label.toLowerCase().contains(query)
                        && !pkg.toLowerCase().contains(query)) continue;
                names.add(label);
            } catch (Exception ignore) { }
        }
        Collections.sort(names, String.CASE_INSENSITIVE_ORDER);
        if (names.isEmpty()) return "No encontré apps con ese nombre.";
        int max = Math.min(names.size(), 30);
        StringBuilder sb = new StringBuilder("Apps (").append(max).append(" de ")
                .append(names.size()).append("):\n");
        for (int i = 0; i < max; i++) sb.append(" - ").append(names.get(i)).append("\n");
        return sb.toString().trim();
    }

    private static String appInfo(Context ctx, String app) {
        String found = findAppPackage(ctx, app);
        if (found == null) return "No encontré la app '" + app + "'.";
        try {
            PackageManager pm = ctx.getPackageManager();
            ApplicationInfo ai = pm.getApplicationInfo(found, 0);
            android.content.pm.PackageInfo pi = pm.getPackageInfo(found, 0);
            StringBuilder sb = new StringBuilder("App: ").append(pm.getApplicationLabel(ai)).append("\n");
            sb.append("Paquete: ").append(found).append("\n");
            sb.append("Versión: ").append(pi.versionName).append(" (").append(pi.versionCode).append(")\n");
            sb.append("Instalada: ").append(java.text.DateFormat.getDateTimeInstance()
                    .format(new java.util.Date(pi.firstInstallTime))).append("\n");
            sb.append("Actualizada: ").append(java.text.DateFormat.getDateTimeInstance()
                    .format(new java.util.Date(pi.lastUpdateTime))).append("\n");
            sb.append("Sistema: ").append((ai.flags & ApplicationInfo.FLAG_SYSTEM) != 0 ? "sí" : "no").append("\n");
            Intent launch = pm.getLaunchIntentForPackage(found);
            sb.append("Lanzable: ").append(launch != null ? "sí" : "no").append("\n");
            return sb.toString().trim();
        } catch (Exception e) {
            return "No pude leer info de '" + app + "': " + e.getMessage();
        }
    }

    private static String openApp(Context ctx, String q) {
        if (q.trim().isEmpty()) return "Decime qué app querés abrir.";
        PackageManager pm = ctx.getPackageManager();
        String target = findAppPackage(ctx, q);
        if (target == null) return "No encontré la app '" + q + "'.";
        String shown = target;
        try {
            ApplicationInfo ai = pm.getApplicationInfo(target, 0);
            CharSequence l = pm.getApplicationLabel(ai);
            if (l != null) shown = l.toString();
        } catch (Exception ignore) { }
        try {
            Intent launch = pm.getLaunchIntentForPackage(target);
            if (launch == null) return "La app '" + shown + "' no tiene lanzador.";
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            ctx.startActivity(launch);
            return "Abriendo " + shown + "...";
        } catch (Exception e) {
            return "No pude abrir " + shown + ": " + e.getMessage();
        }
    }

    /** Busca el paquete de una app por nombre o paquete, con matching flexible. */
    private static String findAppPackage(Context ctx, String q) {
        if (q == null || q.trim().isEmpty()) return null;
        PackageManager pm = ctx.getPackageManager();
        Intent main = new Intent(Intent.ACTION_MAIN);
        main.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> ris = pm.queryIntentActivities(main, 0);
        String target = null;
        String query = q.trim().toLowerCase();
        int bestScore = Integer.MAX_VALUE;
        for (ResolveInfo ri : ris) {
            try {
                String label = ri.loadLabel(pm).toString();
                String pkg = ri.activityInfo.packageName;
                String labelL = label.toLowerCase();
                String pkgL = pkg.toLowerCase();
                int score = Integer.MAX_VALUE;
                if (labelL.equals(query)) score = 0;
                else if (labelL.startsWith(query)) score = 1;
                else if (labelL.contains(query)) score = 2;
                else if (pkgL.equals(query)) score = 3;
                else if (pkgL.contains(query)) score = 4;
                if (score < bestScore) {
                    bestScore = score;
                    target = pkg;
                }
            } catch (Exception ignore) { }
        }
        if (target == null) {
            String[] tokens = query.split("\\s+");
            for (ResolveInfo ri : ris) {
                try {
                    String label = ri.loadLabel(pm).toString().toLowerCase();
                    boolean all = true;
                    for (String tok : tokens) {
                        if (!label.contains(tok)) { all = false; break; }
                    }
                    if (all && target == null) target = ri.activityInfo.packageName;
                } catch (Exception ignore) { }
            }
        }
        return target;
    }

    private static String screen() {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        String out = ErisAccessibilityService.screenText();
        if (out.isEmpty()) return "No veo textos en la pantalla actual.";
        return "Elementos en pantalla:\n" + out;
    }

    private static String tapText(String text) {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        if (text.trim().isEmpty()) return "Decime qué texto tocar.";
        return ErisAccessibilityService.tapText(text);
    }

    private static String tap(int x, int y) {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        if (x < 0 || y < 0) return "Coordenadas inválidas (x,y).";
        Path p = new Path();
        p.moveTo(x, y);
        ErisAccessibilityService.fireGesture(p, 80);
        return "Toque en (" + x + "," + y + ").";
    }

    private static String swipe(int x1, int y1, int x2, int y2, int ms) {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        Path p = new Path();
        p.moveTo(x1, y1);
        p.lineTo(x2, y2);
        ErisAccessibilityService.fireGesture(p, ms > 0 ? ms : 300);
        return "Deslizamiento hecho.";
    }

    private static String scroll(String direction) {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        String d = direction.toLowerCase();
        Path p = new Path();
        if (d.equals("up") || d.equals("arriba")) {
            p.moveTo(540, 500);
            p.lineTo(540, 1700);
        } else {
            p.moveTo(540, 1700);
            p.lineTo(540, 500);
        }
        ErisAccessibilityService.fireGesture(p, 400);
        return "Scroll " + direction + " hecho.";
    }

    private static String type(String text) {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        if (text.isEmpty()) return "No hay texto que escribir.";
        return ErisAccessibilityService.typeText(text);
    }

    private static String home() {
        return ErisAccessibilityService.isRunning()
                && ErisAccessibilityService.globalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
                ? "Volví al inicio." : needAccessibility();
    }

    private static String back() {
        return ErisAccessibilityService.isRunning()
                && ErisAccessibilityService.globalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK)
                ? "Fui para atrás." : needAccessibility();
    }

    private static String recent() {
        return ErisAccessibilityService.isRunning()
                && ErisAccessibilityService.globalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_RECENTS)
                ? "Mostrando apps recientes." : needAccessibility();
    }

    private static String notifications() {
        if (!ErisNotificationListener.isActive())
            return "Permiso de notificaciones no activado para ERIS. Activá 'ERIS' en "
                    + "Configuración > Apps > ERIS > Notificaciones > Acceso a notificaciones.";
        List<String> ns = ErisNotificationListener.getRecent();
        if (ns == null || ns.isEmpty())
            return "No hay notificaciones en este momento.";
        StringBuilder sb = new StringBuilder("Notificaciones:\n");
        int n = Math.min(ns.size(), 12);
        for (int i = 0; i < n; i++) sb.append(" - ").append(ns.get(i)).append("\n");
        return sb.toString().trim();
    }

    private static String foreground() {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        return ErisAccessibilityService.foregroundInfo();
    }

    private static String windows() {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        return ErisAccessibilityService.windowList();
    }

    private static String closed() {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        return ErisAccessibilityService.windowHistory();
    }

    private static String screenIndexed() {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        return ErisAccessibilityService.screenIndexed();
    }

    private static String tapIndex(int index) {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        if (index < 0) return "Decime el índice [n] del elemento a tocar.";
        return ErisAccessibilityService.tapIndex(index);
    }

    private static String scrollTo(String text) {
        if (!ErisAccessibilityService.isRunning()) return needAccessibility();
        if (text.trim().isEmpty()) return "Decime qué texto buscar.";
        return ErisAccessibilityService.scrollToText(text);
    }

    private static String device(Context ctx) {
        StringBuilder sb = new StringBuilder();
        sb.append("Marca: ").append(Build.MANUFACTURER).append("\n");
        sb.append("Modelo: ").append(Build.MODEL).append("\n");
        sb.append("Android: ").append(Build.VERSION.RELEASE)
                .append(" (API ").append(Build.VERSION.SDK_INT).append(")\n");
        try {
            ActivityManager am = (ActivityManager) ctx.getSystemService(Context.ACTIVITY_SERVICE);
            if (am != null) {
                ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
                am.getMemoryInfo(mi);
                sb.append("RAM total: ").append(mi.totalMem / 1048576).append(" MB\n");
                sb.append("RAM disponible: ").append(mi.availMem / 1048576).append(" MB\n");
            }
        } catch (Exception ignore) { }
        try {
            StatFs fs = new StatFs(Environment.getDataDirectory().getPath());
            sb.append("Almacenamiento: ").append(fs.getTotalBytes() / 1048576)
                    .append(" MB total, ").append(fs.getAvailableBytes() / 1048576)
                    .append(" MB libres\n");
        } catch (Exception ignore) { }
        try {
            PackageManager pm = ctx.getPackageManager();
            int n = pm.getInstalledApplications(0).size();
            int launchable = pm.queryIntentActivities(
                    new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0).size();
            sb.append("Apps instaladas: ").append(n).append(" (").append(launchable)
                    .append(" con lanzador)\n");
        } catch (Exception ignore) { }
        String bat = battery(ctx);
        if (bat.startsWith("Batería: ")) bat = bat.substring("Batería: ".length());
        sb.append("Batería: ").append(bat).append("\n");
        try {
            WifiManager wm = (WifiManager) ctx.getApplicationContext()
                    .getSystemService(Context.WIFI_SERVICE);
            if (wm != null && wm.getConnectionInfo() != null) {
                String ssid = wm.getConnectionInfo().getSSID();
                sb.append("WiFi: ").append(ssid == null ? "?" : ssid).append("\n");
            }
        } catch (Exception ignore) { }
        sb.append("Accesibilidad: ")
                .append(ErisAccessibilityService.isRunning() ? "ACTIVA (puedo tocar)" : "INACTIVA");
        return sb.toString();
    }
}
