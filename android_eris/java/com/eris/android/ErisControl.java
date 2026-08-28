package com.eris.android;

import android.content.Context;

import org.json.JSONObject;

/** Nexa: el módulo interno de ERIS para el control del dispositivo.
 *  Es un fragmento de ERIS que reconoce órdenes claras y las ejecuta al instante
 *  (sin esperar a Gemini), y que le da a ERIS el contexto del equipo en cada turno. */
public final class ErisControl {
    public static final String NAME = "Nexa";

    private ErisControl() {}

    /** Contexto actual del equipo que ERIS usa en cada turno para saber qué pasa. */
    public static String context(Context ctx) {
        StringBuilder sb = new StringBuilder();
        sb.append(ErisAccessibilityService.isRunning()
                ? ErisAccessibilityService.windowHistory()
                : "Accesibilidad INACTIVA (no puedo tocar la pantalla).");
        String bat = ErisTools.battery(ctx);
        if (bat.startsWith("Batería: ")) bat = bat.substring("Batería: ".length());
        sb.append("\nBatería: ").append(bat);
        return sb.toString().trim();
    }

    /** Intenta resolver una orden de control al instante. Devuelve null si no es orden rápida. */
    public static String tryFast(Context ctx, String userText) {
        if (userText == null) return null;
        String raw = userText.trim();
        if (raw.isEmpty()) return null;
        String t = normalize(raw);

        String r;

        r = tapIndexMatch(ctx, t);
        if (r != null) return r;

        r = openAppMatch(ctx, raw, t);
        if (r != null) return r;

        r = tapTextMatch(ctx, raw, t);
        if (r != null) return r;

        r = typeMatch(ctx, raw, t);
        if (r != null) return r;

        r = scrollToMatch(ctx, raw, t);
        if (r != null) return r;

        r = appInfoMatch(ctx, raw, t);
        if (r != null) return r;

        r = memorySaveMatch(ctx, raw, t);
        if (r != null) return r;

        r = scrollMatch(ctx, t);
        if (r != null) return r;

        r = homeMatch(ctx, t);
        if (r != null) return r;

        r = backMatch(ctx, t);
        if (r != null) return r;

        r = recentMatch(ctx, t);
        if (r != null) return r;

        r = notificationsMatch(ctx, t);
        if (r != null) return r;

        r = foregroundMatch(ctx, t);
        if (r != null) return r;

        r = windowsMatch(ctx, t);
        if (r != null) return r;

        r = closedMatch(ctx, t);
        if (r != null) return r;

        r = deviceMatch(ctx, t);
        if (r != null) return r;

        r = batteryMatch(ctx, t);
        if (r != null) return r;

        r = appsMatch(ctx, t);
        if (r != null) return r;

        r = screenMatch(ctx, t);
        if (r != null) return r;

        r = memoryRecallMatch(ctx, t);
        if (r != null) return r;

        return null;
    }

    // ---------- ORDENES RAPIDAS (por categoría) ----------

    private static String openAppMatch(Context ctx,String raw, String t) {
        String[] kws = { "abri ", "abre ", "abrir ", "abr ", "open " };
        for (String kw : kws) {
            if (t.startsWith(kw)) {
                String app = raw.substring(kw.length()).trim();
                if (app.isEmpty()) return "¿Qué app querés que abra?";
                String[] arts = { "la ", "el ", "los ", "las ", "un ", "una ", "al " };
                for (String a : arts) {
                    if (app.toLowerCase().startsWith(a)) {
                        app = app.substring(a.length()).trim();
                        break;
                    }
                }
                String low = app.toLowerCase();
                for (String c : new String[] { " porfa", " por favor", " pls", " gracias" }) {
                    if (low.endsWith(c)) {
                        app = app.substring(0, app.length() - c.length()).trim();
                        break;
                    }
                }
                if (app.isEmpty()) return "¿Qué app querés que abra?";
                return ErisTools.runTool(ctx, "android_open_app", arg("app", app));
            }
        }
        return null;
    }

    private static String tapTextMatch(Context ctx,String raw, String t) {
        String[] kws = { "tocame ", "tocáme ", "toca ", "tocá ", "tocar ", "toque " };
        for (String kw : kws) {
            if (t.startsWith(kw)) {
                String txt = raw.substring(kw.length()).trim();
                if (txt.isEmpty()) return "¿Qué texto querés que toque?";
                return ErisTools.runTool(ctx, "android_tap_text", arg("text", txt));
            }
        }
        return null;
    }

    private static String tapIndexMatch(Context ctx,String t) {
        String[] kws = { "toca el ", "toca la ", "tocá el ", "tocá la ", "tocar el " };
        for (String kw : kws) {
            if (t.startsWith(kw)) {
                String idx = t.substring(kw.length()).trim();
                if (idx.matches("[0-9]+")) {
                    return ErisTools.runTool(ctx, "android_tap_index",
                            arg("index", idx));
                }
            }
        }
        return null;
    }

    private static String typeMatch(Context ctx,String raw, String t) {
        String[] kws = { "escribile ", "escribí ", "escribi ", "escribe ", "escribir ", "tipeá ", "tipea ", "type " };
        for (String kw : kws) {
            if (t.startsWith(kw)) {
                String txt = raw.substring(kw.length()).trim();
                if (txt.isEmpty()) return "¿Qué texto querés que escriba?";
                return ErisTools.runTool(ctx, "android_type", arg("text", txt));
            }
        }
        return null;
    }

    private static String scrollToMatch(Context ctx,String raw, String t) {
        String[] kws = { "buscá ", "busca ", "buscar ", "fijate si esta " };
        for (String kw : kws) {
            if (t.startsWith(kw)) {
                String txt = raw.substring(kw.length()).trim();
                if (txt.isEmpty()) return "¿Qué texto buscás?";
                return ErisTools.runTool(ctx, "android_scroll_to", arg("text", txt));
            }
        }
        return null;
    }

    private static String appInfoMatch(Context ctx,String raw, String t) {
        String[] kws = { "info de ", "informacion de ", "información de ", "detalles de " };
        for (String kw : kws) {
            if (t.startsWith(kw)) {
                String app = raw.substring(kw.length()).trim();
                if (app.isEmpty()) return "¿De qué app querés la info?";
                return ErisTools.runTool(ctx, "android_app_info", arg("app", app));
            }
        }
        return null;
    }

    private static String memorySaveMatch(Context ctx,String raw, String t) {
        String[] kws = { "recorda ", "recordá ", "acordate de ", "guarda ", "anota " };
        for (String kw : kws) {
            if (t.startsWith(kw)) {
                String fact = raw.substring(kw.length()).trim();
                if (fact.isEmpty()) return "¿Qué querés que recuerde?";
                return ErisTools.runTool(ctx, "android_memory_save", arg("fact", fact));
            }
        }
        return null;
    }

    private static String scrollMatch(Context ctx,String t) {
        boolean up = t.contains("subi") || t.contains("subí") || t.contains("arriba")
                || t.contains("up") || (t.contains("arriba"));
        if (t.contains("scrolle") || t.contains("scroll") || t.contains("baja la pagina")
                || t.contains("bajá la página") || t.contains("subi la pagina")
                || t.contains("subí la página") || t.contains("bajar pagina")
                || t.contains("hace scroll")) {
            String dir = up ? "up" : "down";
            return ErisTools.runTool(ctx, "android_scroll", arg("direction", dir));
        }
        return null;
    }

    private static String homeMatch(Context ctx,String t) {
        if (t.startsWith("al inicio") || t.startsWith("anda al inicio")
                || t.startsWith("andá al inicio") || t.startsWith("volve al inicio")
                || t.startsWith("volvé al inicio") || t.equals("inicio")
                || t.startsWith("al home") || t.equals("home")) {
            return ErisTools.runTool(ctx, "android_home", arg("", ""));
        }
        return null;
    }

    private static String backMatch(Context ctx,String t) {
        if (t.startsWith("para atras") || t.startsWith("para atrás")
                || t.equals("atras") || t.equals("atrás")
                || t.startsWith("volve") || t.startsWith("volvé")
                || t.startsWith("anda para atras")) {
            return ErisTools.runTool(ctx, "android_back", arg("", ""));
        }
        return null;
    }

    private static String recentMatch(Context ctx,String t) {
        if (t.contains("recientes") || t.contains("recents")) {
            return ErisTools.runTool(ctx, "android_recent", arg("", ""));
        }
        return null;
    }

    private static String notificationsMatch(Context ctx,String t) {
        if (t.contains("notificaciones") || t.contains("notifica")) {
            return ErisTools.runTool(ctx, "android_notifications", arg("", ""));
        }
        return null;
    }

    private static String foregroundMatch(Context ctx,String t) {
        if (t.contains("app en foco") || t.contains("en foco")
                || t.contains("que hay abierto") || t.contains("que hay ahora")
                || t.contains("primer plano") || t.contains("que app esta")
                || t.contains("qué app está") || t.contains("que app esta abierta")) {
            return ErisTools.runTool(ctx, "android_foreground", arg("", ""));
        }
        return null;
    }

    private static String windowsMatch(Context ctx,String t) {
        if (t.contains("ventanas")) {
            return ErisTools.runTool(ctx, "android_windows", arg("", ""));
        }
        return null;
    }

    private static String closedMatch(Context ctx,String t) {
        if (t.contains("se abrio") || t.contains("se cerro")
                || t.contains("cerradas") || t.contains("abiertas recientemente")
                || t.contains("historial") || t.contains("que cerraste")) {
            return ErisTools.runTool(ctx, "android_closed", arg("", ""));
        }
        return null;
    }

    private static String deviceMatch(Context ctx,String t) {
        if (t.contains("estado del telefono") || t.contains("estado del equipo")
                || t.contains("estado del dispositivo") || t.contains("que tiene el celular")
                || t.contains("que tiene el telefono") || t.contains("info del equipo")
                || t.contains("info del telefono") || t.contains("informacion del equipo")
                || t.contains("info del dispositivo")) {
            return ErisTools.runTool(ctx, "android_device", arg("", ""));
        }
        return null;
    }

    private static String batteryMatch(Context ctx,String t) {
        if (t.contains("bateria")) {
            return ErisTools.runTool(ctx, "android_battery", arg("", ""));
        }
        return null;
    }

    private static String appsMatch(Context ctx,String t) {
        if (t.contains("que apps") || t.contains("que aplicaciones")
                || t.contains("apps instaladas") || t.contains("apps que tengo")
                || t.contains("lista de apps") || t.contains("listame las apps")
                || t.contains("listame los programas") || t.equals("apps")
                || t.contains("aplicaciones que tengo")) {
            return ErisTools.runTool(ctx, "android_apps", arg("q", ""));
        }
        return null;
    }

    private static String screenMatch(Context ctx,String t) {
        if (t.contains("que hay en pantalla") || t.contains("que ves")
                || t.contains("que aparece") || t.contains("pantalla actual")
                || t.contains("dump") || t.contains("mirar la pantalla")
                || t.equals("pantalla")) {
            return ErisTools.runTool(ctx, "android_screen_indexed", arg("", ""));
        }
        return null;
    }

    private static String memoryRecallMatch(Context ctx,String t) {
        if (t.contains("que recordas") || t.contains("que recuerdas")
                || t.contains("tu memoria") || t.contains("que te acordas")) {
            return ErisTools.runTool(ctx, "android_memory_recall", arg("", ""));
        }
        return null;
    }

    // ---------- helpers ----------

    private static JSONObject arg(String k, String v) {
        JSONObject o = new JSONObject();
        try {
            o.put(k, v);
        } catch (Exception ignore) { }
        return o;
    }

    private static String normalize(String s) {
        String lower = s.toLowerCase();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < lower.length(); i++) {
            char c = lower.charAt(i);
            switch (c) {
                case 'á': sb.append('a'); break;
                case 'é': sb.append('e'); break;
                case 'í': sb.append('i'); break;
                case 'ó': sb.append('o'); break;
                case 'ú': sb.append('u'); break;
                case 'ü': sb.append('u'); break;
                case 'ñ': sb.append('n'); break;
                default: sb.append(c);
            }
        }
        return sb.toString();
    }
}
