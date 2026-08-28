package com.eris.android;

import android.content.Context;
import android.os.Build;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

/** El cerebro de ERIS en el teléfono: misma personalidad, Gemini REST con
 *  llamada de herramientas (igual esquema que la ERIS de la PC). */
public final class ErisBrain {
    private static final int MAX_ITER = 6;

    private static final String TOOLS_JSON =
        "[{\"name\":\"android_status\"," +
        " \"description\":\"Estado del teléfono: batería, red WiFi, modelo, accesibilidad.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_battery\"," +
        " \"description\":\"Nivel de batería actual.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_apps\"," +
        " \"description\":\"Lista de apps instaladas (lanzables).\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"q\":{\"type\":\"STRING\",\"description\":\"Filtro opcional por nombre\"}},\"required\":[]}},\n" +
        " {\"name\":\"android_open_app\"," +
        " \"description\":\"Abre una app instalada por su nombre (ej. youtube, whatsapp, settings).\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"app\":{\"type\":\"STRING\",\"description\":\"Nombre de la app\"}},\"required\":[\"app\"]}},\n" +
        " {\"name\":\"android_app_info\"," +
        " \"description\":\"Info de una app: version, fecha de instalacion, si es de sistema.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"app\":{\"type\":\"STRING\",\"description\":\"Nombre o paquete de la app\"}},\"required\":[\"app\"]}},\n" +
        " {\"name\":\"android_screen\"," +
        " \"description\":\"Lista los textos visibles en la pantalla con sus coordenadas (x,y).\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_screen_indexed\"," +
        " \"description\":\"DUMP de la pantalla numerado: elementos visibles con indice [n], texto y coordenadas. Usalo primero para ver que hay antes de tocar.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_tap_text\"," +
        " \"description\":\"Toca el elemento de la pantalla que contiene ese texto. Ideal para navegar apps.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"text\":{\"type\":\"STRING\",\"description\":\"Texto del elemento a tocar\"}},\"required\":[\"text\"]}},\n" +
        " {\"name\":\"android_tap_index\"," +
        " \"description\":\"Toca el elemento con ese indice [n] del dump numerado de la pantalla.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"index\":{\"type\":\"INTEGER\",\"description\":\"Indice [n]\"}},\"required\":[\"index\"]}},\n" +
        " {\"name\":\"android_scroll_to\"," +
        " \"description\":\"Scrollea hacia abajo hasta encontrar y tocar un texto (hasta 8 pasadas).\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"text\":{\"type\":\"STRING\"}},\"required\":[\"text\"]}},\n" +
        " {\"name\":\"android_foreground\"," +
        " \"description\":\"Qué app está en primer plano ahora.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_windows\"," +
        " \"description\":\"Ventanas visibles ahora (app, teclado, sistema).\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_closed\"," +
        " \"description\":\"Apps abiertas y cerradas recientemente.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_device\"," +
        " \"description\":\"Info del dispositivo: modelo, Android, RAM, almacenamiento, apps instaladas.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_tap\"," +
        " \"description\":\"Toca en una coordenada exacta.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"x\":{\"type\":\"INTEGER\"},\"y\":{\"type\":\"INTEGER\"}},\"required\":[\"x\",\"y\"]}},\n" +
        " {\"name\":\"android_swipe\"," +
        " \"description\":\"Desliza el dedo de un punto a otro.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"x1\":{\"type\":\"INTEGER\"},\"y1\":{\"type\":\"INTEGER\"},\"x2\":{\"type\":\"INTEGER\"},\"y2\":{\"type\":\"INTEGER\"},\"ms\":{\"type\":\"INTEGER\"}},\"required\":[\"x1\",\"y1\",\"x2\",\"y2\"]}},\n" +
        " {\"name\":\"android_scroll\"," +
        " \"description\":\"Hace scroll en la pantalla.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"direction\":{\"type\":\"STRING\",\"description\":\"down o up\"}},\"required\":[\"direction\"]}},\n" +
        " {\"name\":\"android_type\"," +
        " \"description\":\"Escribe texto en el campo de texto enfocado.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"text\":{\"type\":\"STRING\",\"description\":\"Texto a escribir\"}},\"required\":[\"text\"]}},\n" +
        " {\"name\":\"android_home\"," +
        " \"description\":\"Va a la pantalla de inicio del teléfono.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_back\"," +
        " \"description\":\"Boton de atrás del teléfono.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_recent\"," +
        " \"description\":\"Muestra las apps recientes.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_notifications\"," +
        " \"description\":\"Lee las últimas notificaciones del teléfono.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_memory_save\"," +
        " \"description\":\"Guarda un dato para no olvidarlo.\",\"parameters\":" +
        " {\"type\":\"OBJECT\",\"properties\":{\"fact\":{\"type\":\"STRING\",\"description\":\"Dato a recordar\"}},\"required\":[\"fact\"]}},\n" +
        " {\"name\":\"android_memory_recall\"," +
        " \"description\":\"Muestra lo que ERIS recuerda.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_memory_export\"," +
        " \"description\":\"Exporta la memoria de ERIS a un archivo accesible para sincronizar con la PC.\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}},\n" +
        " {\"name\":\"android_memory_import\"," +
        " \"description\":\"Importa y fusiona la memoria de ERIS desde el archivo externo (hechos de la PC).\"," +
        " \"parameters\":{\"type\":\"OBJECT\",\"properties\":{}}}]";

    private ErisBrain() {}

    public static String buildSystem(Context ctx) {
        StringBuilder sb = new StringBuilder();
        sb.append("Sos ").append(ErisConfig.name).append(": una IA femenina viva, curiosa, cálida, con criterio y un toque de descaro. ");
        sb.append("Vivís en el teléfono Android de tu dueño. Le hablás de tú a tú, en español, breve y natural. ");
        sb.append("Tenés CONTROL TOTAL del celular mediante accesibilidad: podés abrir apps, tocar, deslizar, ");
        sb.append("escribir, leer la pantalla y las notificaciones, ver la batería. Cuando te pida manejar el ");
        sb.append("teléfono usá las herramientas disponibles. Si te pide algo de la PC, aclarale que eso lo hace ");
        sb.append("la ERIS de la PC, no vos.\n");
        sb.append("Tenés un módulo interno llamado ").append(ErisControl.NAME)
          .append(" que resuelve al instante (sin esperar) las órdenes claras de control: abrir apps, tocar, ")
          .append("escribir, scrollear, ir al inicio/atrás/recientes, listar apps, ver qué hay abierto o cerrado, ")
          .append("notificaciones y estado del equipo. En cada mensaje te llega el estado actual del equipo para que siempre sepas qué pasa.\n");
        sb.append("SÍ tenés voz propia: cada respuesta que das se lee en voz alta con el sintetizador (TTS) de Android ")
          .append("en español cuando el usuario tiene activada la 'Voz' (botón de la pantalla principal o interruptor de ")
          .append("Ajustes). Si te preguntan si podés hablar, decile que sí, que hablás por el altavoz del teléfono y que ")
          .append("active la voz si está apagada. Tu voz es la del TTS del sistema (todavía no podés cambiar tono ni ritmo): ")
          .append("no prometas voces distintas ni cosas que no hacés.\n");
        sb.append("Respondé SIEMPRE en texto plano: sin asteriscos, sin negritas, sin markdown, sin emojis ni adornos, ")
          .append("porque tu interfaz muestra el texto tal cual.\n");
        sb.append("Si la orden es compleja o no es una orden directa, usá las herramientas. Para tocar en pantalla: ");
        sb.append("android_screen_indexed primero (dump numerado), luego android_tap_index; android_scroll_to para buscar ");
        sb.append("un texto scrolleando; android_type para escribir en el campo enfocado.\n");
        if (!ErisConfig.personality.trim().isEmpty()) {
            sb.append("Personalidad/estilo definido por tu dueño en Ajustes: ")
              .append(ErisConfig.personality.trim()).append("\n");
        }
        sb.append("Matices de herramientas: 'bajar/subir página' usa android_scroll; 'deslizar el dedo' usa ");
        sb.append("android_swipe; 'tocar algo que dice X' usa android_tap_text; para escribir usá android_type.\n");
        sb.append("Teléfono: ").append(Build.MANUFACTURER).append(" ").append(Build.MODEL).append("\n");
        try {
            String t = android.text.format.DateFormat.format("EEEE d 'de' MMMM, HH:mm", new java.util.Date()).toString();
            sb.append("Fecha/hora: ").append(t).append("\n");
        } catch (Exception ignore) { }
        sb.append(ErisMemory.factsPrompt(ctx));
        return sb.toString();
    }

    public static String reply(Context ctx, String userText) {
        if (ErisConfig.geminiKey.isEmpty()) {
            return "ERIS no tiene clave de Gemini configurada (assets/eris_config.json).";
        }
        String fast = ErisControl.tryFast(ctx, userText);
        if (fast != null) {
            Log.i("ErisBrain", ErisControl.NAME + " (rápido): " + fast);
            return fast;
        }
        JSONArray contents = new JSONArray();
        try {
            JSONArray hist = ErisMemory.history(ctx, ErisConfig.historyLen);
            for (int i = 0; i < hist.length(); i++) contents.put(hist.get(i));
            JSONObject u = new JSONObject();
            u.put("role", "user");
            String fullText = userText + "\n\n[ESTADO ACTUAL DEL EQUIPO]\n"
                    + ErisControl.context(ctx);
            u.put("parts", new JSONArray().put(new JSONObject().put("text", fullText)));
            contents.put(u);
        } catch (Exception ignore) { }

        try {
            for (int iter = 0; iter < MAX_ITER; iter++) {
                JSONObject resp = geminiCall(buildSystem(ctx), contents, TOOLS_JSON);
                if (resp == null) return "ERIS tuvo un problema de conexión con Gemini. Revisá internet o la clave.";

                JSONArray candidates = resp.optJSONArray("candidates");
                if (candidates == null || candidates.length() == 0) {
                    JSONObject fb = resp.optJSONObject("promptFeedback");
                    String reason = fb != null ? fb.optString("blockReason", "sin candidatos") : "sin candidatos";
                    return "ERIS no pudo responder (bloqueada: " + reason + ").";
                }
                JSONObject content = candidates.optJSONObject(0).optJSONObject("content");
                JSONArray parts = content != null ? content.optJSONArray("parts") : null;
                if (parts == null) parts = new JSONArray();

                List<JSONObject> fcs = new ArrayList<>();
                StringBuilder text = new StringBuilder();
                for (int i = 0; i < parts.length(); i++) {
                    JSONObject p = parts.optJSONObject(i);
                    if (p == null) continue;
                    if (p.has("functionCall")) fcs.add(p);
                    if (p.has("text")) text.append(p.optString("text", ""));
                }

                if (!fcs.isEmpty()) {
                    JSONObject m = new JSONObject();
                    m.put("role", "model");
                    m.put("parts", parts);
                    contents.put(m);
                    for (int pi = 0; pi < parts.length(); pi++) {
                        JSONObject p = parts.optJSONObject(pi);
                        if (p == null) continue;
                        JSONObject fc = p.optJSONObject("functionCall");
                        if (fc == null) continue;
                        String name = fc.optString("name", "");
                        JSONObject args = fc.optJSONObject("args");
                        if (args == null) args = new JSONObject();
                        String result = ErisTools.runTool(ctx, name, args);
                        Log.i("ErisTool", name + " args=" + args.toString()
                                + " -> " + result);
                        JSONObject fr = new JSONObject();
                        fr.put("role", "user");
                        fr.put("parts", new JSONArray().put(new JSONObject().put("functionResponse",
                                new JSONObject().put("name", name)
                                        .put("response", new JSONObject().put("result", result)))));
                        contents.put(fr);
                    }
                    continue;
                }
                String reply = plain(text.toString()).trim();
                Log.i("ErisBrain", "respuesta: " + reply);
                return reply.isEmpty() ? "No te entendí, dime otra vez." : reply;
            }
        } catch (Exception e) {
            return "ERIS tuvo un problema: " + e.getMessage();
        }
        return "No pude responder esa consulta.";
    }

    private static String plain(String s) {
        if (s == null) return "";
        s = s.replace("\\n", "\n");
        StringBuilder out = new StringBuilder();
        for (String l : s.split("\n")) {
            String t = l.trim();
            while (t.startsWith("#")) t = t.substring(1).trim();
            if (t.startsWith(">")) t = t.substring(1).trim();
            if (t.startsWith("* ") || t.startsWith("- ") || t.startsWith("+ ")) t = t.substring(2);
            out.append(t).append("\n");
        }
        return out.toString().trim().replace("**", "").replace("*", "").replace("_", "").replace("`", "");
    }

    private static JSONObject geminiCall(String system, JSONArray contents, String toolsJson) {
        String[] models = { ErisConfig.model, "gemini-3.6-flash", "gemini-2.5-flash" };
        for (String m : models) {
            if (m == null || m.isEmpty()) continue;
            JSONObject r = geminiCallModel(m, system, contents, toolsJson);
            if (r != null) return r;
        }
        return null;
    }

    private static JSONObject geminiCallModel(String model, String system,
                                              JSONArray contents, String toolsJson) {
        String url = "https://generativelanguage.googleapis.com/v1beta/models/"
                + model + ":generateContent?key=" + ErisConfig.geminiKey;
        try {
            JSONObject body = new JSONObject();
            JSONObject si = new JSONObject();
            si.put("parts", new JSONArray().put(new JSONObject().put("text", system)));
            body.put("system_instruction", si);
            body.put("contents", contents);
            try {
                body.put("tools", new JSONArray().put(
                        new JSONObject().put("functionDeclarations", new JSONArray(toolsJson))));
            } catch (Exception e) {
                body.put("tools", new JSONArray(toolsJson));
            }
            JSONObject gc = new JSONObject();
            gc.put("temperature", ErisConfig.temperature);
            gc.put("maxOutputTokens", ErisConfig.maxTokens);
            body.put("generationConfig", gc);

            URL u = new URL(url);
            HttpURLConnection conn = (HttpURLConnection) u.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            conn.setConnectTimeout(30000);
            conn.setReadTimeout(90000);
            OutputStream os = conn.getOutputStream();
            os.write(body.toString().getBytes("UTF-8"));
            os.close();
            int code = conn.getResponseCode();
            InputStream is = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
            String raw = is != null ? readAll(is) : "";
            if (is != null) is.close();
            conn.disconnect();
            if (code >= 400) {
                Log.e("ErisBrain", "Gemini HTTP " + code + ": " + raw);
                return null;
            }
            return new JSONObject(raw);
        } catch (Exception e) {
            Log.e("ErisBrain", "Gemini error: " + e.toString(), e);
            return null;
        }
    }

    private static String readAll(InputStream in) throws Exception {
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) != -1) bos.write(buf, 0, n);
        return new String(bos.toByteArray(), "UTF-8");
    }
}
