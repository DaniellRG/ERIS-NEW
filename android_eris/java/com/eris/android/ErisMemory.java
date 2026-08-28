package com.eris.android;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;

/** Memoria persistente de ERIS en el teléfono: hechos + historial de chat (JSON). */
public final class ErisMemory {
    private static final String FILE = "eris_memory.json";
    private static JSONObject data = null;

    private ErisMemory() {}

    public static synchronized JSONObject load(Context ctx) {
        if (data != null) return data;
        File f = new File(ctx.getFilesDir(), FILE);
        String raw = "";
        try {
            FileInputStream in = new FileInputStream(f);
            byte[] buf = new byte[(int) f.length()];
            in.read(buf);
            in.close();
            raw = new String(buf, "UTF-8");
        } catch (Exception ignore) { }
        try {
            data = new JSONObject(raw);
        } catch (Exception e) {
            data = new JSONObject();
        }
        if (!data.has("facts")) {
            try { data.put("facts", new JSONArray()); } catch (Exception ignore) {}
        }
        if (!data.has("chats")) {
            try { data.put("chats", new JSONObject()); } catch (Exception ignore) {}
        }
        return data;
    }

    public static synchronized void save(Context ctx) {
        try {
            FileOutputStream out = new FileOutputStream(new File(ctx.getFilesDir(), FILE));
            out.write(data.toString(2).getBytes("UTF-8"));
            out.close();
        } catch (Exception ignore) { }
    }

    /** Borra toda la memoria (hechos + historial). */
    public static synchronized String clear(Context ctx) {
        data = null;
        File f = new File(ctx.getFilesDir(), FILE);
        if (f.exists()) f.delete();
        load(ctx);
        return "Memoria de ERIS borrada.";
    }

    /** Vuelve a leer la memoria desde disco (tras una importación externa). */
    public static synchronized void reload(Context ctx) {
        data = null;
        load(ctx);
    }

    /** Copia la memoria interna a un archivo accesible para sincronizar con la PC. */
    public static synchronized String exportSync(Context ctx) {
        JSONObject d = load(ctx);
        File dir = ctx.getExternalFilesDir(null);
        if (dir == null) return "No hay almacenamiento externo disponible.";
        try {
            if (!dir.exists()) dir.mkdirs();
            File f = new File(dir, FILE);
            FileOutputStream out = new FileOutputStream(f);
            out.write(d.toString(2).getBytes("UTF-8"));
            out.close();
            return "Memoria exportada a " + f.getAbsolutePath();
        } catch (Exception e) {
            return "No pude exportar la memoria.";
        }
    }

    /** Lee el archivo externo y fusiona los hechos con la memoria interna. */
    public static synchronized String importSync(Context ctx) {
        File dir = ctx.getExternalFilesDir(null);
        if (dir == null) return "No hay almacenamiento externo disponible.";
        File f = new File(dir, FILE);
        if (!f.exists()) return "No hay archivo de memoria para importar.";
        try {
            FileInputStream in = new FileInputStream(f);
            byte[] buf = new byte[(int) f.length()];
            in.read(buf);
            in.close();
            JSONObject ext = new JSONObject(new String(buf, "UTF-8"));
            JSONObject cur = load(ctx);
            JSONArray curFacts = cur.optJSONArray("facts");
            JSONArray extFacts = ext.optJSONArray("facts");
            if (extFacts != null && curFacts != null) {
                for (int i = 0; i < extFacts.length(); i++) {
                    String fact = extFacts.optString(i);
                    if (fact.isEmpty()) continue;
                    boolean has = false;
                    for (int j = 0; j < curFacts.length(); j++) {
                        if (curFacts.optString(j).equals(fact)) { has = true; break; }
                    }
                    if (!has) curFacts.put(fact);
                }
                cur.put("facts", curFacts);
            }
            JSONObject extChats = ext.optJSONObject("chats");
            if (extChats != null && extChats.optJSONObject("owner") != null) {
                JSONObject curChats = cur.optJSONObject("chats");
                JSONObject curOwn = curChats != null ? curChats.optJSONObject("owner") : null;
                int extLen = extChats.optJSONObject("owner").optJSONArray("messages") != null
                        ? extChats.optJSONObject("owner").optJSONArray("messages").length() : 0;
                int curLen = curOwn != null && curOwn.optJSONArray("messages") != null
                        ? curOwn.optJSONArray("messages").length() : 0;
                if (extLen > curLen) cur.put("chats", extChats);
            }
            save(ctx);
            return "Memoria importada y fusionada.";
        } catch (Exception e) {
            return "No pude importar la memoria.";
        }
    }

    public static synchronized String addFact(Context ctx, String fact) {
        JSONObject d = load(ctx);
        JSONArray facts = d.optJSONArray("facts");
        if (facts == null) facts = new JSONArray();
        try {
            for (int i = 0; i < facts.length(); i++) {
                if (facts.getString(i).equals(fact)) return "Eso ya lo tenía en memoria.";
            }
            facts.put(fact);
            d.put("facts", facts);
            save(ctx);
            return "Anotado, no se me olvida: " + fact;
        } catch (Exception e) {
            return "No pude guardarlo.";
        }
    }

    public static synchronized String recallFacts(Context ctx) {
        JSONObject d = load(ctx);
        JSONArray facts = d.optJSONArray("facts");
        if (facts == null || facts.length() == 0) return "No tengo nada guardado aún.";
        StringBuilder sb = new StringBuilder("Recuerdo:\n");
        try {
            for (int i = 0; i < facts.length(); i++) {
                sb.append(" - ").append(facts.getString(i)).append("\n");
            }
        } catch (Exception ignore) { }
        return sb.toString();
    }

    public static synchronized String factsPrompt(Context ctx) {
        JSONObject d = load(ctx);
        JSONArray facts = d.optJSONArray("facts");
        if (facts == null || facts.length() == 0) return "";
        StringBuilder sb = new StringBuilder("\nDATOS QUE EL USUARIO TE PIDIO RECORDAR:\n");
        try {
            int n = Math.min(facts.length(), 20);
            for (int i = Math.max(0, facts.length() - n); i < facts.length(); i++) {
                sb.append(" - ").append(facts.getString(i)).append("\n");
            }
        } catch (Exception ignore) { }
        return sb.toString();
    }

    public static synchronized JSONArray history(Context ctx, int max) {
        JSONObject d = load(ctx);
        JSONObject chats = d.optJSONObject("chats");
        JSONArray arr = new JSONArray();
        if (chats == null) return arr;
        JSONObject own = chats.optJSONObject("owner");
        if (own == null) return arr;
        JSONArray msgs = own.optJSONArray("messages");
        if (msgs == null) return arr;
        try {
            for (int i = Math.max(0, msgs.length() - max); i < msgs.length(); i++) {
                arr.put(msgs.get(i));
            }
        } catch (Exception ignore) { }
        return arr;
    }

    public static synchronized void addTurn(Context ctx, String userText, String erisText) {
        JSONObject d = load(ctx);
        JSONObject chats = d.optJSONObject("chats");
        if (chats == null) chats = new JSONObject();
        JSONObject own = chats.optJSONObject("owner");
        if (own == null) own = new JSONObject();
        JSONArray msgs = own.optJSONArray("messages");
        if (msgs == null) msgs = new JSONArray();
        try {
            JSONObject u = new JSONObject();
            u.put("role", "user");
            u.put("parts", new JSONArray().put(new JSONObject().put("text", userText)));
            JSONObject m = new JSONObject();
            m.put("role", "model");
            m.put("parts", new JSONArray().put(new JSONObject().put("text", erisText)));
            msgs.put(u);
            msgs.put(m);
            while (msgs.length() > 60) {
                JSONArray n = new JSONArray();
                for (int i = msgs.length() - 60; i < msgs.length(); i++) n.put(msgs.get(i));
                msgs = n;
            }
            own.put("messages", msgs);
            chats.put("owner", own);
            d.put("chats", chats);
            save(ctx);
        } catch (Exception ignore) { }
    }
}
