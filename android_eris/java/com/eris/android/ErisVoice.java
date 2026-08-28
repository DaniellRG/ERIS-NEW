package com.eris.android;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.Voice;
import android.util.Base64;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

import java.util.List;
import java.util.Locale;

import org.json.JSONArray;
import org.json.JSONObject;

/** Voz de ERIS: responder por audio (TTS) y escuchar lo que le dictás (STT). */
public final class ErisVoice {
    public interface Result {
        void onText(String text);
    }

    public static boolean enabled = false;
    private static TextToSpeech tts;
    private static SpeechRecognizer stt;
    private static Result current;
    private static Context appCtx;
    private static android.media.MediaPlayer player;

    private ErisVoice() {}

    private static final String ENGINE = "com.google.android.tts";

    public static final String[] GEMINI_VOICES = {
        "Achernar", "Achird", "Algenib", "Algieba", "Alnilam", "Aoede", "Autonoe",
        "Callirrhoe", "Charon", "Despina", "Enceladus", "Erinome", "Fenrir", "Gacrux",
        "Iapetus", "Kore", "Laomedeia", "Leda", "Orus", "Pulcherrima", "Puck",
        "Rasalgethi", "Sadachbia", "Sadaltager", "Schedar", "Sulafat", "Umbriel",
        "Vindemiatrix", "Zephyr", "Zubenelgenubi"
    };
    private static final String[] GEMINI_GENDER = {
        "F", "M", "M", "M", "M", "F", "F", "F", "M", "F", "M", "F", "M", "F",
        "M", "F", "F", "F", "M", "F", "M", "M", "M", "M", "M", "F", "M",
        "F", "F", "M"
    };
    private static final String[] GEMINI_STYLE = {
        "suave y cálida", "amable", "grave", "fluida", "firme", "cálida y melódica",
        "brillante y alegre", "relajada y amigable", "seria y profesional",
        "suave y gentil", "susurrante", "clara y articulada", "apasionada",
        "madura y serena", "nítida y limpia", "firme y decidida", "alegre y optimista",
        "juvenil y enérgica", "firme y serena", "enérgica", "vivaz y alegre",
        "narradora", "viva y vívida", "erudita", "estable y pareja",
        "cálida y cercana", "relajada", "delicada", "brillante y clara",
        "casual y relajada"
    };

    public static void init(Context ctx) {
        appCtx = ctx.getApplicationContext();
        if (tts == null) {
            tts = new TextToSpeech(ctx.getApplicationContext(),
                    new TextToSpeech.OnInitListener() {
                        @Override
                        public void onInit(int status) {
                            if (status == TextToSpeech.SUCCESS) {
                                tts.setPitch(ErisConfig.voicePitch);
                                tts.setSpeechRate(ErisConfig.voiceRate);
                                android.util.Log.i("ErisVoice", "iniciado (motor "
                                        + ENGINE + "), voces es:");
                                Voice v = pickSpanishVoice();
                                for (Voice sv : tts.getVoices()) {
                                    if (sv.getLocale().getLanguage().equals("es")) {
                                        android.util.Log.i("ErisVoice", "  " + sv.getName()
                                                + " (" + sv.getLocale() + ") score="
                                                + voiceScore(sv));
                                    }
                                }
                                if (v != null) {
                                    tts.setVoice(v);
                                    android.util.Log.i("ErisVoice", "voz elegida: "
                                            + v.getName() + " (" + v.getLocale() + ")");
                                } else {
                                    int r = tts.setLanguage(new Locale("es", "ES"));
                                    if (r == TextToSpeech.LANG_MISSING_DATA
                                            || r == TextToSpeech.LANG_NOT_SUPPORTED) {
                                        tts.setLanguage(Locale.getDefault());
                                    }
                                    android.util.Log.i("ErisVoice",
                                            "sin voz es: lenguaje por defecto");
                                }
                            } else {
                                android.util.Log.e("ErisVoice", "init TTS falló: " + status);
                            }
                            logVoiceState();
                        }
                    }, ENGINE);
        }
    }

    private static int voiceScore(Voice v) {
        String n = v.getName().toLowerCase();
        String l = v.getLocale().toString().toLowerCase();
        if (!l.startsWith("es")) return -1000;
        int s = 0;
        if (n.contains("network")) s += 28;
        else if (n.contains("local")) s += 2;
        if (l.startsWith("es-es")) s += 10;
        else if (l.startsWith("es-mx") || l.startsWith("es-us")
                || l.startsWith("es-ar") || l.startsWith("es-co")) s += 8;
        String code = n.replace("es-", "").replace("-local", "").replace("-network", "");
        String last = code.length() > 0 ? code.substring(code.length() - 1) : "";
        if (last.equals("m")) s -= 15;
        else if (last.equals("f")) s += 30;
        String[] fem = { "-x-eee-", "-x-eea-", "-x-eec-", "-x-eed-",
                "-x-esd-", "-x-esc-", "-x-sfb-", "-x-evf-" };
        for (String c : fem) if (n.contains(c)) s += 25;
        String[] mal = { "-x-eef-", "-x-eeg-", "-x-eeh-", "-x-eei-", "-x-eej-",
                "-x-esm-", "-x-evm-", "-x-eem-", "-x-esf-" };
        for (String c : mal) if (n.contains(c)) s -= 25;
        return s;
    }

    private static Voice pickSpanishVoice() {
        try {
            java.util.List<Voice> voices = new java.util.ArrayList<>(tts.getVoices());
            if (ErisConfig.ttsVoice != null && !ErisConfig.ttsVoice.isEmpty()
                    && !ErisConfig.ttsVoice.endsWith("-local")) {
                for (Voice v : voices) {
                    if (ErisConfig.ttsVoice.equals(v.getName())) {
                        android.util.Log.i("ErisVoice", "usando voz guardada: "
                                + ErisConfig.ttsVoice);
                        return v;
                    }
                }
            }
            java.util.Collections.sort(voices, new java.util.Comparator<Voice>() {
                @Override
                public int compare(Voice a, Voice b) {
                    return voiceScore(b) - voiceScore(a);
                }
            });
            for (Voice v : voices) {
                if (v.getLocale().getLanguage().equals("es")) {
                    if (ErisConfig.ttsVoice != null
                            && ErisConfig.ttsVoice.endsWith("-local")) {
                        ErisConfig.ttsVoice = v.getName();
                        ErisConfig.save(appCtx);
                        android.util.Log.i("ErisVoice", "voz guardada era local; elegida: "
                                + v.getName());
                    }
                    return v;
                }
            }
            return null;
        } catch (Exception e) {
            android.util.Log.e("ErisVoice", "no se pudieron leer voces: " + e.getMessage());
            return null;
        }
    }

    private static boolean isFemalePhoneVoice(Voice v) {
        String n = v.getName().toLowerCase();
        String[] fem = { "eee", "eea", "eec", "eed", "esd", "esc", "sfb",
                "evf", "evb", "efl" };
        String[] mal = { "eef", "eeg", "eeh", "eei", "eej", "esm", "evm", "eem",
                "eeb", "esf" };
        for (String c : mal) if (n.contains("-x-" + c + "-")) return false;
        for (String c : fem) if (n.contains("-x-" + c + "-")) return true;
        String code = n.replace("es-", "").replace("-local", "").replace("-network", "");
        String last = code.length() > 0 ? code.substring(code.length() - 1) : "";
        return last.equals("f");
    }

    public static String[] spanishVoiceNames() {
        if (tts == null) return new String[0];
        try {
            java.util.List<String> out = new java.util.ArrayList<>();
            java.util.List<Voice> voices = new java.util.ArrayList<>(tts.getVoices());
            java.util.Collections.sort(voices, new java.util.Comparator<Voice>() {
                @Override
                public int compare(Voice a, Voice b) {
                    return voiceScore(b) - voiceScore(a);
                }
            });
            for (Voice v : voices) {
                if (v.getLocale().getLanguage().equals("es") && isFemalePhoneVoice(v)) {
                    out.add(v.getName());
                }
            }
            return out.toArray(new String[0]);
        } catch (Exception e) {
            return new String[0];
        }
    }

    public static String[] spanishNaturalNames() {
        if (tts == null) return new String[0];
        try {
            java.util.List<String> out = new java.util.ArrayList<>();
            java.util.List<Voice> voices = new java.util.ArrayList<>(tts.getVoices());
            java.util.Collections.sort(voices, new java.util.Comparator<Voice>() {
                @Override
                public int compare(Voice a, Voice b) {
                    return voiceScore(b) - voiceScore(a);
                }
            });
            for (Voice v : voices) {
                String n = v.getName();
                if (v.getLocale().getLanguage().equals("es") && n.contains("network")
                        && isFemalePhoneVoice(v)) {
                    out.add(n);
                }
            }
            return out.toArray(new String[0]);
        } catch (Exception e) {
            return new String[0];
        }
    }

    public static void setVoiceByName(String name) {
        if (tts == null || name == null) return;
        try {
            for (Voice v : tts.getVoices()) {
                if (name.equals(v.getName())) {
                    tts.setVoice(v);
                    android.util.Log.i("ErisVoice", "cambiado a: " + v.getName());
                    return;
                }
            }
        } catch (Exception e) {
            android.util.Log.e("ErisVoice", "setVoiceByName: " + e.getMessage());
        }
    }

    public static void applyTone() {
        if (tts == null) return;
        try {
            tts.setPitch(ErisConfig.voicePitch);
            tts.setSpeechRate(ErisConfig.voiceRate);
        } catch (Exception ignore) { }
    }

    public static String voiceLabel(String name) {
        if (name == null || name.isEmpty()) return "Voz por defecto";
        String n = name.toLowerCase();
        String country;
        if (n.startsWith("es-es")) country = "España";
        else if (n.startsWith("es-mx")) country = "México";
        else if (n.startsWith("es-ar")) country = "Argentina";
        else if (n.startsWith("es-co")) country = "Colombia";
        else if (n.startsWith("es-us")) country = "Latino";
        else country = "Español";
        String code = n.replace("es-", "").replace("-local", "").replace("-network", "");
        String last = code.length() > 0 ? code.substring(code.length() - 1) : "";
        String[] fem = { "eee", "eea", "eec", "eed", "esd", "esc", "sfb",
                "evf", "evb", "efl" };
        String[] mal = { "eef", "eeg", "eeh", "eei", "eej", "esm", "evm", "eem",
                "eeb", "esf" };
        boolean knownFemale = false, knownMale = false;
        for (String c : fem) if (n.contains("-x-" + c + "-")) knownFemale = true;
        for (String c : mal) if (n.contains("-x-" + c + "-")) knownMale = true;
        String gender;
        if (knownFemale) gender = "Mujer";
        else if (knownMale) gender = "Hombre";
        else if (last.equals("f")) gender = "Mujer";
        else if (last.equals("m")) gender = "Hombre";
        else gender = "";
        String quality = n.contains("network") ? "Natural" : "Local";
        StringBuilder b = new StringBuilder(country);
        if (!gender.isEmpty()) b.append(" · ").append(gender);
        b.append(" · ").append(quality);
        return b.toString();
    }

    public static String[] spanishVoiceLabels() {
        String[] names = spanishVoiceNames();
        String[] labels = new String[names.length];
        for (int i = 0; i < names.length; i++) labels[i] = voiceLabel(names[i]);
        return labels;
    }

    public static String[] geminiVoiceLabels() {
        java.util.List<String> out = new java.util.ArrayList<>();
        for (int i = 0; i < GEMINI_VOICES.length; i++) {
            if (!GEMINI_GENDER[i].equals("F")) continue;
            out.add(GEMINI_VOICES[i] + " · Mujer · " + GEMINI_STYLE[i]);
        }
        return out.toArray(new String[0]);
    }

    public static String geminiVoiceLabel(String name) {
        for (int i = 0; i < GEMINI_VOICES.length; i++) {
            if (GEMINI_VOICES[i].equals(name)) {
                String g = GEMINI_GENDER[i].equals("F") ? "Mujer" : "Hombre";
                return GEMINI_VOICES[i] + " · " + g + " · " + GEMINI_STYLE[i];
            }
        }
        return name;
    }

    public static boolean isFemaleGeminiVoice(String name) {
        for (int i = 0; i < GEMINI_VOICES.length; i++) {
            if (GEMINI_VOICES[i].equals(name)) return GEMINI_GENDER[i].equals("F");
        }
        return false;
    }

    public static int geminiVoiceIndex(String name) {
        String[] fem = geminiFemaleNames();
        for (int i = 0; i < fem.length; i++) {
            if (fem[i].equals(name)) return i;
        }
        return 0;
    }

    public static String[] geminiFemaleNames() {
        java.util.List<String> out = new java.util.ArrayList<>();
        for (int i = 0; i < GEMINI_VOICES.length; i++) {
            if (GEMINI_GENDER[i].equals("F")) out.add(GEMINI_VOICES[i]);
        }
        return out.toArray(new String[0]);
    }

    public static String currentVoiceName() {
        if ("gemini".equals(ErisConfig.ttsProvider)) {
            return geminiVoiceLabel(ErisConfig.geminiVoice);
        }
        if (tts == null) return "";
        try {
            Voice v = tts.getVoice();
            return v != null ? v.getName() : "";
        } catch (Exception e) {
            return "";
        }
    }

    public static boolean voiceDataOk() {
        if (tts == null) return true;
        try {
            Voice v = tts.getVoice();
            if (v == null) return false;
            java.util.Set<String> f = v.getFeatures();
            return f == null || !f.contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED);
        } catch (Exception e) {
            return true;
        }
    }

    public static void logVoiceState() {
        try {
            Voice v = tts != null ? tts.getVoice() : null;
            android.util.Log.i("ErisVoice", "voz activa: "
                    + (v != null ? v.getName() : "ninguna")
                    + " instalada=" + voiceDataOk());
        } catch (Exception e) {
            android.util.Log.e("ErisVoice", "estado de voz: " + e.getMessage());
        }
    }

    public static void speak(String text) {
        if (!enabled || text == null || text.isEmpty()) return;
        ensureAudible();
        android.util.Log.i("ErisVoice", "speak: voz=" + ErisConfig.geminiVoice
                + (tts == null ? ", tts=null" : ""));
        speakGemini(text, ErisConfig.geminiVoice);
    }

    public static void speakGemini(String text, String voice) {
        if (ErisConfig.geminiKey.isEmpty() || appCtx == null) {
            fallbackToPhone(text);
            return;
        }
        android.util.Log.i("ErisVoice", "gemini tts (" + voice + "): "
                + (text.length() > 80 ? text.substring(0, 80) + "…" : text));
        new Thread(new Runnable() {
            @Override
            public void run() {
                byte[] pcm = null;
                String[] models = { "gemini-3.1-flash-tts-preview",
                        "gemini-2.5-flash-preview-tts" };
                for (String m : models) {
                    pcm = geminiTtsCall(m, text, voice);
                    if (pcm != null) break;
                }
                final byte[] audio = pcm;
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override
                    public void run() {
                        if (audio != null) playAudio(audio);
                        else fallbackToPhone(text);
                    }
                });
            }
        }).start();
    }

    private static byte[] geminiTtsCall(String model, String text, String voice) {
        try {
            String url = "https://generativelanguage.googleapis.com/v1beta/models/"
                    + model + ":generateContent?key=" + ErisConfig.geminiKey;
            JSONObject body = new JSONObject();
            body.put("contents", new JSONArray().put(new JSONObject().put("parts",
                    new JSONArray().put(new JSONObject().put("text", text)))));
            JSONObject gc = new JSONObject();
            gc.put("responseModalities", new JSONArray().put("AUDIO"));
            JSONObject spc = new JSONObject();
            spc.put("voiceConfig", new JSONObject().put("prebuiltVoiceConfig",
                    new JSONObject().put("voiceName", voice)));
            gc.put("speechConfig", spc);
            body.put("generationConfig", gc);

            HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            conn.setConnectTimeout(20000);
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
                android.util.Log.e("ErisVoice", "gemini tts HTTP " + code + ": " + raw);
                return null;
            }
            JSONObject resp = new JSONObject(raw);
            JSONArray cands = resp.optJSONArray("candidates");
            if (cands == null || cands.length() == 0) return null;
            JSONObject c0 = cands.optJSONObject(0).optJSONObject("content");
            JSONArray parts = c0 != null ? c0.optJSONArray("parts") : null;
            if (parts == null || parts.length() == 0) return null;
            String b64 = parts.optJSONObject(0).optJSONObject("inlineData")
                    .optString("data", "");
            if (b64.isEmpty()) return null;
            return Base64.decode(b64, Base64.DEFAULT);
        } catch (Exception e) {
            android.util.Log.e("ErisVoice", "gemini tts error: " + e.getMessage());
            return null;
        }
    }

    private static void playAudio(byte[] pcm) {
        try {
            if (pcm == null || pcm.length == 0) return;
            byte[] wav = wrapWav(pcm);
            android.util.Log.i("ErisVoice", "gemini tts ok, audio: " + pcm.length
                    + " bytes (PCM 24kHz)");
            File f = new File(appCtx.getCacheDir(), "eris_gemini_tts.wav");
            FileOutputStream fos = new FileOutputStream(f);
            fos.write(wav);
            fos.close();
            if (tts != null) tts.stop();
            stopPlayer();
            player = new android.media.MediaPlayer();
            player.setAudioAttributes(new android.media.AudioAttributes.Builder()
                    .setUsage(android.media.AudioAttributes.USAGE_ASSISTANT)
                    .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build());
            player.setDataSource(f.getAbsolutePath());
            player.prepare();
            player.start();
            player.setOnCompletionListener(new android.media.MediaPlayer.OnCompletionListener() {
                @Override
                public void onCompletion(android.media.MediaPlayer mp) {
                    try { mp.release(); } catch (Exception ignore) { }
                    if (player == mp) player = null;
                }
            });
        } catch (Exception e) {
            android.util.Log.e("ErisVoice", "playAudio: " + e.getMessage());
        }
    }

    private static void stopPlayer() {
        try {
            if (player != null) {
                player.stop();
                player.release();
                player = null;
            }
        } catch (Exception ignore) { }
    }

    private static void fallbackToPhone(String text) {
        android.util.Log.w("ErisVoice",
                "gemini tts no disponible; ERIS queda en silencio (sin voz local)");
    }

    private static byte[] wrapWav(byte[] pcm) {
        ByteArrayOutputStream bos = new ByteArrayOutputStream(pcm.length + 44);
        writeAscii(bos, "RIFF");
        writeIntLE(bos, 36 + pcm.length);
        writeAscii(bos, "WAVE");
        writeAscii(bos, "fmt ");
        writeIntLE(bos, 16);
        writeShortLE(bos, 1);
        writeShortLE(bos, 1);
        writeIntLE(bos, 24000);
        writeIntLE(bos, 48000);
        writeShortLE(bos, 2);
        writeShortLE(bos, 16);
        writeAscii(bos, "data");
        writeIntLE(bos, pcm.length);
        bos.write(pcm, 0, pcm.length);
        return bos.toByteArray();
    }

    private static void writeAscii(ByteArrayOutputStream b, String s) {
        for (int i = 0; i < s.length(); i++) b.write(s.charAt(i));
    }

    private static void writeIntLE(ByteArrayOutputStream b, int v) {
        b.write(v & 0xFF);
        b.write((v >>> 8) & 0xFF);
        b.write((v >>> 16) & 0xFF);
        b.write((v >>> 24) & 0xFF);
    }

    private static void writeShortLE(ByteArrayOutputStream b, int v) {
        b.write(v & 0xFF);
        b.write((v >>> 8) & 0xFF);
    }

    private static String readAll(InputStream in) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) != -1) bos.write(buf, 0, n);
        return new String(bos.toByteArray(), "UTF-8");
    }

    private static void ensureAudible() {
        try {
            if (appCtx == null) return;
            android.media.AudioManager am = (android.media.AudioManager)
                    appCtx.getSystemService(Context.AUDIO_SERVICE);
            int cur = am.getStreamVolume(android.media.AudioManager.STREAM_MUSIC);
            if (cur <= 0) {
                int max = am.getStreamMaxVolume(android.media.AudioManager.STREAM_MUSIC);
                am.setStreamVolume(android.media.AudioManager.STREAM_MUSIC,
                        Math.max(1, max * 3 / 5), 0);
                android.util.Log.i("ErisVoice",
                        "volumen multimedia estaba en 0, lo subí para poder hablar");
            }
        } catch (Exception ignore) { }
    }

    public static void listen(Context ctx, Result cb) {
        if (stt == null) {
            stt = SpeechRecognizer.createSpeechRecognizer(ctx.getApplicationContext());
        }
        current = cb;
        stt.setRecognitionListener(new RecognitionListener() {
            @Override public void onReadyForSpeech(Bundle p) { }
            @Override public void onBeginningOfSpeech() { }
            @Override public void onRmsChanged(float v) { }
            @Override public void onBufferReceived(byte[] b) { }
            @Override public void onEndOfSpeech() { }
            @Override public void onError(int e) {
                if (current != null) { current.onText(""); current = null; }
            }
            @Override public void onResults(Bundle r) {
                List<String> m = r.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                String t = (m != null && !m.isEmpty()) ? m.get(0) : "";
                if (current != null) { current.onText(t); current = null; }
            }
            @Override public void onPartialResults(Bundle p) { }
            @Override public void onEvent(int e, Bundle p) { }
        });
        Intent i = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, ErisConfig.sttLang);
        i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        stt.startListening(i);
    }
}
