package com.eris.android;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONObject;

/** Configuración de ERIS: clave de Gemini, modelo y todas las opciones
 *  ajustables desde la pantalla de Ajustes (persistidas en SharedPreferences). */
public final class ErisConfig {
    public static String geminiKey = "";
    public static String model = "gemini-3.1-flash-lite";
    public static float temperature = 0.7f;
    public static int maxTokens = 2048;
    public static int historyLen = 16;
    public static boolean darkTheme = true;
    public static int accent = 0;
    public static boolean voiceEnabled = false;
    public static String sttLang = "es-AR";
    public static String name = "ERIS";
    public static String personality = "";
    public static int bubbleSize = 1;
    public static String ttsVoice = "";
    public static float voiceRate = 0.92f;
    public static float voicePitch = 1.0f;
    public static String ttsProvider = "phone";
    public static String geminiVoice = "Achernar";

    private static final String PREFS = "eris_settings";
    private static final String[] ACCENTS = { "Violeta", "Azul", "Verde", "Rosa" };
    private static final String[] LANGUAGES = { "es-AR", "es-ES", "en-US" };

    private ErisConfig() {}

    public static void load(Context ctx) {
        try {
            java.io.InputStream in = ctx.getAssets().open("eris_config.json");
            JSONObject o = new JSONObject(readAll(in));
            geminiKey = o.optString("gemini_key", "");
            model = o.optString("model", "gemini-3.1-flash-lite");
        } catch (Exception e) {
            geminiKey = "";
        }
        SharedPreferences p = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (p.contains("gemini_key")) geminiKey = p.getString("gemini_key", geminiKey);
        if (p.contains("model")) model = p.getString("model", model);
        temperature = p.getFloat("temperature", temperature);
        maxTokens = p.getInt("max_tokens", maxTokens);
        historyLen = p.getInt("history_len", historyLen);
        darkTheme = p.getBoolean("dark_theme", darkTheme);
        accent = p.getInt("accent", accent);
        voiceEnabled = p.getBoolean("voice", voiceEnabled);
        sttLang = p.getString("stt_lang", sttLang);
        if (p.contains("name")) name = p.getString("name", name);
        if (p.contains("personality")) personality = p.getString("personality", personality);
        bubbleSize = p.getInt("bubble_size", bubbleSize);
        if (p.contains("tts_voice")) ttsVoice = p.getString("tts_voice", ttsVoice);
        voiceRate = p.getFloat("voice_rate", voiceRate);
        voicePitch = p.getFloat("voice_pitch", voicePitch);
        if (p.contains("tts_provider")) ttsProvider = p.getString("tts_provider", ttsProvider);
        ttsProvider = "gemini";
        if (p.contains("gemini_voice")) geminiVoice = p.getString("gemini_voice", geminiVoice);
        if (!ErisVoice.isFemaleGeminiVoice(geminiVoice)) geminiVoice = "Achernar";
        ErisVoice.enabled = voiceEnabled;
    }

    public static void save(Context ctx) {
        SharedPreferences.Editor e = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit();
        e.putString("gemini_key", geminiKey);
        e.putString("model", model);
        e.putFloat("temperature", temperature);
        e.putInt("max_tokens", maxTokens);
        e.putInt("history_len", historyLen);
        e.putBoolean("dark_theme", darkTheme);
        e.putInt("accent", accent);
        e.putBoolean("voice", voiceEnabled);
        e.putString("stt_lang", sttLang);
        e.putString("name", name);
        e.putString("personality", personality);
        e.putInt("bubble_size", bubbleSize);
        e.putString("tts_voice", ttsVoice);
        e.putFloat("voice_rate", voiceRate);
        e.putFloat("voice_pitch", voicePitch);
        e.putString("tts_provider", ttsProvider);
        e.putString("gemini_voice", geminiVoice);
        e.apply();
        ErisVoice.enabled = voiceEnabled;
    }

    public static void reset(Context ctx) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply();
        load(ctx);
    }

    public static int themeRes() {
        switch (accent % 4) {
            case 1: return darkTheme ? R.style.Theme_ErisDarkBlue : R.style.Theme_ErisLightBlue;
            case 2: return darkTheme ? R.style.Theme_ErisDarkGreen : R.style.Theme_ErisLightGreen;
            case 3: return darkTheme ? R.style.Theme_ErisDarkPink : R.style.Theme_ErisLightPink;
            default: return darkTheme ? R.style.Theme_ErisDarkViolet : R.style.Theme_ErisLightViolet;
        }
    }

    public static String accentName() {
        return ACCENTS[Math.abs(accent) % ACCENTS.length];
    }

    public static String[] accents() {
        return ACCENTS;
    }

    public static String[] languages() {
        return LANGUAGES;
    }

    public static int languageIndex() {
        for (int i = 0; i < LANGUAGES.length; i++) {
            if (LANGUAGES[i].equals(sttLang)) return i;
        }
        return 0;
    }

    private static String readAll(java.io.InputStream in) throws Exception {
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) != -1) bos.write(buf, 0, n);
        in.close();
        return new String(bos.toByteArray(), "UTF-8");
    }
}
