package com.eris.android;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.HttpURLConnection;
import java.net.URL;

/** Ajustes de ERIS: claves de API, tema, voz, comportamiento, memoria, permisos. */
public class SettingsActivity extends Activity {
    private EditText keyGemini;
    private EditText modelField;
    private EditText nameField;
    private EditText personalityField;
    private TextView testResult;
    private TextView memResult;
    private TextView tempVal;
    private SeekBar tempSeek;
    private Switch voiceSwitch;
    private Spinner tokenSpinner;
    private Spinner histSpinner;
    private Button btnAccess;
    private Button btnNotif;
    private Button btnBubbleToggle;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        ErisConfig.load(getApplicationContext());
        setTheme(ErisConfig.themeRes());
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        keyGemini = (EditText) findViewById(R.id.keyGemini);
        modelField = (EditText) findViewById(R.id.modelField);
        nameField = (EditText) findViewById(R.id.nameField);
        personalityField = (EditText) findViewById(R.id.personalityField);
        testResult = (TextView) findViewById(R.id.testResult);
        memResult = (TextView) findViewById(R.id.memResult);
        tempVal = (TextView) findViewById(R.id.tempVal);
        tempSeek = (SeekBar) findViewById(R.id.tempSeek);
        voiceSwitch = (Switch) findViewById(R.id.voiceSwitch);
        tokenSpinner = (Spinner) findViewById(R.id.tokenSpinner);
        histSpinner = (Spinner) findViewById(R.id.histSpinner);
        btnAccess = (Button) findViewById(R.id.btnAccess);
        btnNotif = (Button) findViewById(R.id.btnNotif);
        btnBubbleToggle = (Button) findViewById(R.id.btnBubbleToggle);
        Button btnTestVoice = (Button) findViewById(R.id.btnTestVoice);

        keyGemini.setText(ErisConfig.geminiKey);
        modelField.setText(ErisConfig.model);
        nameField.setText(ErisConfig.name);
        personalityField.setText(ErisConfig.personality);
        voiceSwitch.setChecked(ErisConfig.voiceEnabled);
        tempSeek.setProgress(Math.round(ErisConfig.temperature * 10f));
        tempVal.setText(String.format(java.util.Locale.US, "%.1f", ErisConfig.temperature));
        setupSpinner(tokenSpinner, new String[] { "512", "1024", "2048", "4096" },
                indexOf(new int[] { 512, 1024, 2048, 4096 }, ErisConfig.maxTokens));
        setupSpinner(histSpinner, new String[] { "4", "8", "16", "32" },
                indexOf(new int[] { 4, 8, 16, 32 }, ErisConfig.historyLen));

        btnTestVoice.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ErisVoice.enabled = true;
                ErisConfig.voiceEnabled = true;
                ErisConfig.save(SettingsActivity.this);
                voiceSwitch.setChecked(true);
                ErisVoice.init(SettingsActivity.this);
                try {
                    android.media.ToneGenerator tg = new android.media.ToneGenerator(
                            android.media.AudioManager.STREAM_MUSIC, 85);
                    tg.startTone(android.media.ToneGenerator.TONE_PROP_BEEP, 300);
                } catch (Exception ignore) { }
                ErisVoice.speak("Hola, soy " + ErisConfig.name
                        + ". ¿Me escuchás? Esta es mi voz.");
                testResult.setText("Voz: " + ErisVoice.currentVoiceName() + " (OK)");
            }
        });

        ErisVoice.init(SettingsActivity.this);
        final Spinner geminiVoiceSpinner = (Spinner) findViewById(R.id.geminiVoiceSpinner);
        final Button btnAuditionGemini = (Button) findViewById(R.id.btnAuditionGemini);
        final TextView geminiAuditionLabel = (TextView) findViewById(R.id.geminiAuditionLabel);

        ArrayAdapter<String> gv = new ArrayAdapter<String>(this,
                android.R.layout.simple_spinner_item, ErisVoice.geminiVoiceLabels());
        gv.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        geminiVoiceSpinner.setAdapter(gv);
        geminiVoiceSpinner.setSelection(ErisVoice.geminiVoiceIndex(ErisConfig.geminiVoice));
        final boolean[] firstGemini = { true };
        geminiVoiceSpinner.setOnItemSelectedListener(
                new android.widget.AdapterView.OnItemSelectedListener() {
                    @Override
                    public void onItemSelected(android.widget.AdapterView<?> p,
                            View v, int pos, long id) {
                        if (firstGemini[0]) { firstGemini[0] = false; return; }
                        String name = ErisVoice.geminiFemaleNames()[pos];
                        if (name.equals(ErisConfig.geminiVoice)) return;
                        ErisConfig.geminiVoice = name;
                        ErisConfig.save(SettingsActivity.this);
                        ErisVoice.enabled = true;
                        ErisVoice.speakGemini("Esta es mi voz. ¿Te gusta?", name);
                        testResult.setText("Voz: " + ErisVoice.geminiVoiceLabel(name));
                    }
                    @Override
                    public void onNothingSelected(android.widget.AdapterView<?> p) { }
                });

        btnAuditionGemini.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                final String[] aud = ErisVoice.geminiFemaleNames();
                if (aud.length == 0) {
                    geminiAuditionLabel.setText("No hay voces femeninas");
                    return;
                }
                final Handler h = new Handler(Looper.getMainLooper());
                geminiAuditionLabel.setText("Reproduciendo " + aud.length + " voces…");
                for (int i = 0; i < aud.length; i++) {
                    final int idx = i;
                    h.postDelayed(new Runnable() {
                        @Override
                        public void run() {
                            ErisVoice.enabled = true;
                            ErisVoice.speakGemini("Esta es la voz número "
                                    + (idx + 1) + ".", aud[idx]);
                            android.util.Log.i("ErisVoice", "audicion gemini: "
                                    + (idx + 1) + " -> " + aud[idx]);
                            geminiAuditionLabel.setText("Voz " + (idx + 1) + "/"
                                    + aud.length + ": " + aud[idx] + "…");
                        }
                    }, i * 5000L);
                }
            }
        });

        buildChips((LinearLayout) findViewById(R.id.modeRow),
                new String[] { "Oscuro", "Claro" }, ErisConfig.darkTheme ? 0 : 1,
                new OnChip() {
                    @Override public void onSelect(int i) {
                        ErisConfig.darkTheme = (i == 0);
                        ErisConfig.save(SettingsActivity.this);
                        recreate();
                    }
                });
        buildChips((LinearLayout) findViewById(R.id.accentRow),
                ErisConfig.accents(), ErisConfig.accent % 4,
                new OnChip() {
                    @Override public void onSelect(int i) {
                        ErisConfig.accent = i;
                        ErisConfig.save(SettingsActivity.this);
                        recreate();
                    }
                });
        buildChips((LinearLayout) findViewById(R.id.langRow),
                ErisConfig.languages(), ErisConfig.languageIndex(),
                new OnChip() {
                    @Override public void onSelect(int i) {
                        ErisConfig.sttLang = ErisConfig.languages()[i];
                        ErisConfig.save(SettingsActivity.this);
                    }
                });
        buildChips((LinearLayout) findViewById(R.id.bubbleSizeRow),
                new String[] { "Pequeña", "Normal", "Grande" }, ErisConfig.bubbleSize,
                new OnChip() {
                    @Override public void onSelect(int i) {
                        ErisConfig.bubbleSize = i;
                        ErisConfig.save(SettingsActivity.this);
                    }
                });

        findViewById(R.id.btnBack).setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });
        findViewById(R.id.keyToggle).setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                int t = keyGemini.getInputType();
                if ((t & 128) != 0) {
                    keyGemini.setInputType(android.text.InputType.TYPE_CLASS_TEXT);
                    ((Button) v).setText("Ocultar");
                } else {
                    keyGemini.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                            | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
                    ((Button) v).setText("Ver");
                }
                keyGemini.setSelection(keyGemini.getText().length());
            }
        });
        findViewById(R.id.btnTestKey).setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { testKey(); }
        });
        findViewById(R.id.btnExport).setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                memResult.setText(ErisMemory.exportSync(SettingsActivity.this));
            }
        });
        findViewById(R.id.btnImport).setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                memResult.setText(ErisMemory.importSync(SettingsActivity.this));
            }
        });
        findViewById(R.id.btnClear).setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                memResult.setText(ErisMemory.clear(SettingsActivity.this));
            }
        });
        btnAccess.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                try {
                    startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
                } catch (Exception ignore) { }
            }
        });
        btnNotif.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                try {
                    startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
                } catch (Exception ignore) { }
            }
        });
        btnBubbleToggle.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { toggleBubble(); }
        });
        findViewById(R.id.btnReset).setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                ErisConfig.reset(SettingsActivity.this);
                recreate();
            }
        });

        voiceSwitch.setOnCheckedChangeListener(new android.widget.CompoundButton.OnCheckedChangeListener() {
            @Override public void onCheckedChanged(android.widget.CompoundButton b, boolean checked) {
                ErisConfig.voiceEnabled = checked;
                ErisConfig.save(SettingsActivity.this);
            }
        });
        tempSeek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar sb, int progress, boolean fromUser) {
                if (fromUser) {
                    ErisConfig.temperature = progress / 10f;
                    tempVal.setText(String.format(java.util.Locale.US, "%.1f", ErisConfig.temperature));
                    ErisConfig.save(SettingsActivity.this);
                }
            }
            @Override public void onStartTrackingTouch(SeekBar sb) { }
            @Override public void onStopTrackingTouch(SeekBar sb) { }
        });

        addTextListener(keyGemini);
        addTextListener(modelField);
        addTextListener(nameField);
        addTextListener(personalityField);

        refreshStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshStatus();
    }

    private void refreshStatus() {
        boolean acc = accessibilityEnabled();
        btnAccess.setText("Accesibilidad: " + (acc ? "ACTIVA" : "INACTIVA"));
        btnNotif.setText("Notificaciones: " + (notificationAccessEnabled() ? "ACTIVAS" : "INACTIVAS"));
        if (ErisOverlayService.running) {
            btnBubbleToggle.setText("Burbuja flotante: ACTIVA (tocar para apagar)");
        } else if (!Settings.canDrawOverlays(this)) {
            btnBubbleToggle.setText("Activar burbuja (dar permiso de superposición)");
        } else {
            btnBubbleToggle.setText("Activar burbuja flotante");
        }
    }

    private void toggleBubble() {
        if (ErisOverlayService.running) {
            stopService(new Intent(this, ErisOverlayService.class));
        } else if (Settings.canDrawOverlays(this)) {
            try {
                Intent i = new Intent(this, ErisOverlayService.class);
                if (Build.VERSION.SDK_INT >= 26) {
                    startForegroundService(i);
                } else {
                    startService(i);
                }
            } catch (Exception ignore) { }
        } else {
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:" + getPackageName())));
            } catch (Exception ignore) { }
        }
        refreshStatus();
    }

    private void addTextListener(final EditText et) {
        et.addTextChangedListener(new android.text.TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int a, int b, int c) { }
            @Override public void onTextChanged(CharSequence s, int a, int b, int c) { }
            @Override public void afterTextChanged(android.text.Editable s) {
                String v = s.toString();
                if (et == keyGemini) ErisConfig.geminiKey = v;
                else if (et == modelField) ErisConfig.model = v;
                else if (et == nameField) ErisConfig.name = v;
                else if (et == personalityField) ErisConfig.personality = v;
                ErisConfig.save(SettingsActivity.this);
            }
        });
    }

    private void setupSpinner(Spinner sp, String[] values, int sel) {
        ArrayAdapter<String> a = new ArrayAdapter<String>(this,
                android.R.layout.simple_spinner_item, values);
        a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        sp.setAdapter(a);
        if (sel >= 0 && sel < values.length) sp.setSelection(sel);
        final int[] nums = new int[values.length];
        for (int i = 0; i < values.length; i++) nums[i] = Integer.parseInt(values[i]);
        final boolean isToken = sp == tokenSpinner;
        sp.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(android.widget.AdapterView<?> p, View v, int pos, long id) {
                if (isToken) {
                    if (ErisConfig.maxTokens == nums[pos]) return;
                    ErisConfig.maxTokens = nums[pos];
                } else {
                    if (ErisConfig.historyLen == nums[pos]) return;
                    ErisConfig.historyLen = nums[pos];
                }
                ErisConfig.save(SettingsActivity.this);
            }
            @Override public void onNothingSelected(android.widget.AdapterView<?> p) { }
        });
    }

    private void testKey() {
        ErisConfig.geminiKey = keyGemini.getText().toString().trim();
        ErisConfig.model = modelField.getText().toString().trim();
        ErisConfig.save(this);
        testResult.setVisibility(View.VISIBLE);
        testResult.setText("Probando conexión…");
        final String key = ErisConfig.geminiKey;
        final String m = ErisConfig.model.isEmpty() ? "gemini-3.1-flash-lite" : ErisConfig.model;
        new Thread(new Runnable() {
            @Override public void run() {
                final String msg = pingGemini(key, m);
                runOnUiThread(new Runnable() {
                    @Override public void run() { testResult.setText(msg); }
                });
            }
        }).start();
    }

    private String pingGemini(String key, String model) {
        if (key.isEmpty()) return "Escribí primero la clave de Gemini.";
        try {
            URL u = new URL("https://generativelanguage.googleapis.com/v1beta/models/"
                    + model + ":generateContent?key=" + key);
            HttpURLConnection conn = (HttpURLConnection) u.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            conn.setConnectTimeout(20000);
            conn.setReadTimeout(60000);
            JSONObject body = new JSONObject();
            body.put("contents", new JSONArray().put(new JSONObject().put("parts",
                    new JSONArray().put(new JSONObject().put("text", "Respondé solo: OK")))));
            conn.getOutputStream().write(body.toString().getBytes("UTF-8"));
            int code = conn.getResponseCode();
            String raw = readAll(code >= 400 ? conn.getErrorStream() : conn.getInputStream());
            conn.disconnect();
            if (code == 200) return "Conexión OK: el modelo " + model + " respondió.";
            String msg = "Error HTTP " + code;
            try {
                JSONObject o = new JSONObject(raw);
                JSONObject err = o.optJSONObject("error");
                if (err != null) msg = "Error HTTP " + code + ": " + err.optString("message", "");
            } catch (Exception ignore) { }
            return msg;
        } catch (Exception e) {
            return "No se pudo conectar: " + e.getMessage();
        }
    }

    private String readAll(java.io.InputStream in) {
        if (in == null) return "";
        try {
            java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = in.read(buf)) != -1) bos.write(buf, 0, n);
            in.close();
            return new String(bos.toByteArray(), "UTF-8");
        } catch (Exception e) {
            return "";
        }
    }

    private int indexOf(int[] arr, int v) {
        for (int i = 0; i < arr.length; i++) if (arr[i] == v) return i;
        return 0;
    }

    private interface OnChip {
        void onSelect(int i);
    }

    private void buildChips(LinearLayout row, String[] labels, int selected, final OnChip cb) {
        row.removeAllViews();
        for (int i = 0; i < labels.length; i++) {
            final Button b = new Button(this);
            b.setText(labels[i]);
            b.setTextSize(12);
            b.setAllCaps(false);
            boolean sel = (i == selected);
            b.setBackgroundResource(sel ? R.drawable.btn_accent : R.drawable.btn_dark);
            b.setTextColor(sel ? 0xFFFFFFFF : attrColor(R.attr.erisTextPrimary));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(44), 1f);
            if (i > 0) lp.leftMargin = dp(6);
            b.setLayoutParams(lp);
            final int fi = i;
            b.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) { cb.onSelect(fi); }
            });
            row.addView(b);
        }
    }

    private int attrColor(int resAttr) {
        android.content.res.TypedArray a = getTheme().obtainStyledAttributes(new int[] { resAttr });
        int c = a.getColor(0, 0xFF8B5CF6);
        a.recycle();
        return c;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private boolean accessibilityEnabled() {
        String enabled = Settings.Secure.getString(getContentResolver(),
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;
        ComponentName cn = new ComponentName(this, ErisAccessibilityService.class);
        return enabled.contains(cn.flattenToString());
    }

    private boolean notificationAccessEnabled() {
        String enabled = Settings.Secure.getString(getContentResolver(),
                "enabled_notification_listeners");
        if (enabled == null) return false;
        return enabled.contains(new ComponentName(this, ErisNotificationListener.class)
                .flattenToString());
    }
}
