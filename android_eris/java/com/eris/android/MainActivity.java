package com.eris.android;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Pantalla principal de ERIS en el teléfono: chat + estado + activación de accesibilidad. */
public class MainActivity extends Activity {
    private LinearLayout messages;
    private ScrollView scroll;
    private View statusDot;
    private boolean thinking = false;
    private EditText input;
    private boolean notifHintAdded = false;
    private static boolean askedPostNotif = false;
    private Button bubbleBtn;
    private Button voiceBtn;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        ErisConfig.load(getApplicationContext());
        setTheme(ErisConfig.themeRes());
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        statusDot = findViewById(R.id.statusDot);
        messages = findViewById(R.id.messages);
        scroll = findViewById(R.id.scroll);
        input = findViewById(R.id.input);
        Button sendBtn = findViewById(R.id.sendBtn);
        Button micBtn = findViewById(R.id.micBtn);
        bubbleBtn = findViewById(R.id.bubbleBtn);
        voiceBtn = findViewById(R.id.voiceBtn);
        Button exportBtn = findViewById(R.id.exportBtn);
        Button importBtn = findViewById(R.id.importBtn);
        Button settingsBtn = findViewById(R.id.settingsBtn);

        settingsBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(MainActivity.this, SettingsActivity.class));
            }
        });

        ErisVoice.init(this);
        if (Build.VERSION.SDK_INT >= 33 && !askedPostNotif
                && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
            askedPostNotif = true;
            requestPermissions(new String[] { android.Manifest.permission.POST_NOTIFICATIONS }, 3);
        }

        sendBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                send();
            }
        });
        micBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                micListen();
            }
        });
        bubbleBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                toggleBubble();
            }
        });
        voiceBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ErisVoice.enabled = !ErisVoice.enabled;
                ErisConfig.voiceEnabled = ErisVoice.enabled;
                ErisConfig.save(MainActivity.this);
                updateVoiceBtn();
            }
        });
        exportBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                addMessage("Sistema", ErisMemory.exportSync(MainActivity.this), false);
            }
        });
        importBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                addMessage("Sistema", ErisMemory.importSync(MainActivity.this), false);
            }
        });

        input.setOnEditorActionListener(new android.widget.TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(android.widget.TextView v, int actionId,
                                          android.view.KeyEvent event) {
                if (actionId == android.view.inputmethod.EditorInfo.IME_ACTION_SEND
                        || (event != null && event.getKeyCode()
                            == android.view.KeyEvent.KEYCODE_ENTER && event.getAction()
                            == android.view.KeyEvent.ACTION_DOWN)) {
                    send();
                    return true;
                }
                return false;
            }
        });

        updateStatus();
        if (!accessibilityEnabled()) {
            addMessage("Sistema", "Necesito que actives la accesibilidad para poder tocar tu pantalla. "
                    + "Apretá el botón y activá 'ERIS'.", false);
            Button go = actionButton("Activar accesibilidad", Settings.ACTION_ACCESSIBILITY_SETTINGS);
            messages.addView(go);
        } else {
            addMessage(ErisConfig.name, "Hola, soy yo, " + ErisConfig.name + ". Estoy instalada en tu celular y ya puedo "
                    + "manejar la pantalla. ¿Qué hacemos?", false);
        }
        ensureNotifHint();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
        updateBubbleBtn();
        updateVoiceBtn();
        if (accessibilityEnabled()) {
            View first = messages.getChildCount() > 0 ? messages.getChildAt(0) : null;
            if (first != null && "sistema".equals(first.getTag())) {
                messages.removeAllViews();
                addMessage(ErisConfig.name, "¡Listo! Ya puedo tocar tu pantalla. ¿Qué hacemos?", false);
            } else if (messages.getChildCount() == 0) {
                addMessage(ErisConfig.name, "¡Listo! Ya puedo tocar tu pantalla. ¿Qué hacemos?", false);
            }
        }
        ensureNotifHint();
    }

    private void toggleBubble() {
        if (ErisOverlayService.running) {
            stopService(new Intent(this, ErisOverlayService.class));
        } else if (Settings.canDrawOverlays(this)) {
            startBubble();
        } else {
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:" + getPackageName())));
            } catch (Exception ignore) { }
        }
        updateBubbleBtn();
    }

    private void startBubble() {
        try {
            Intent i = new Intent(this, ErisOverlayService.class);
            if (Build.VERSION.SDK_INT >= 26) {
                startForegroundService(i);
            } else {
                startService(i);
            }
        } catch (Exception ignore) { }
    }

    private void updateBubbleBtn() {
        if (bubbleBtn == null) return;
        if (ErisOverlayService.running) {
            bubbleBtn.setText("Burbuja: ON");
        } else if (!Settings.canDrawOverlays(this)) {
            bubbleBtn.setText("Burbuja: dar permiso");
        } else {
            bubbleBtn.setText("Burbuja: OFF");
        }
    }

    private void updateVoiceBtn() {
        if (voiceBtn == null) return;
        voiceBtn.setText(ErisVoice.enabled ? "🔊 Voz ON" : "🔇 Voz OFF");
    }

    private void micListen() {
        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] { android.Manifest.permission.RECORD_AUDIO }, 2);
            return;
        }
        ErisVoice.listen(this, new ErisVoice.Result() {
            @Override
            public void onText(String text) {
                if (text == null || text.trim().isEmpty()) {
                    addMessage("Sistema", "No te escuché bien, repetí.", false);
                    return;
                }
                input.setText(text);
                send();
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
                                           int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 2 && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            micListen();
        }
    }

    private void ensureNotifHint() {
        if (notifHintAdded || notificationAccessEnabled()) return;
        notifHintAdded = true;
        addMessage("Sistema", "Si querés que lea tus notificaciones, dame permiso de "
                + "notificaciones (botón de abajo).", false);
        Button go = actionButton("Activar notificaciones", Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
        messages.addView(go);
    }

    private Button actionButton(String text, String action) {
        final Button b = new Button(this);
        b.setText(text);
        b.setTextColor(0xFFFFFFFF);
        b.setAllCaps(false);
        b.setTextSize(14);
        b.setBackgroundResource(R.drawable.btn_accent);
        b.setPadding(ErisViews.dp(this, 16), ErisViews.dp(this, 10),
                ErisViews.dp(this, 16), ErisViews.dp(this, 10));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.bottomMargin = ErisViews.dp(this, 8);
        lp.leftMargin = ErisViews.dp(this, 2);
        b.setLayoutParams(lp);
        b.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                try {
                    startActivity(new Intent(action));
                } catch (Exception ignore) { }
            }
        });
        return b;
    }

    private boolean notificationAccessEnabled() {
        String enabled = Settings.Secure.getString(getContentResolver(),
                "enabled_notification_listeners");
        if (enabled == null) return false;
        return enabled.contains(new ComponentName(this, ErisNotificationListener.class)
                .flattenToString());
    }

    private void updateStatus() {
        int color;
        if (!accessibilityEnabled()) {
            color = 0xFFE53935;
        } else if (thinking) {
            color = 0xFFFFB300;
        } else {
            color = 0xFF43A047;
        }
        statusDot.setBackgroundTintList(
                android.content.res.ColorStateList.valueOf(color));
    }

    private boolean accessibilityEnabled() {
        String enabled = Settings.Secure.getString(getContentResolver(),
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;
        ComponentName cn = new ComponentName(this, ErisAccessibilityService.class);
        return enabled.contains(cn.flattenToString());
    }

    private void send() {
        String text = input.getText().toString().trim();
        if (text.isEmpty() || ErisChat.isBusy()) return;
        input.setText("");
        addMessage("Tú", text, true);
        final String userText = text;
        InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (imm != null) imm.hideSoftInputFromWindow(input.getWindowToken(), 0);

        thinking = true;
        updateStatus();
        ErisChat.send(getApplicationContext(), userText, new ErisChat.Callback() {
            @Override
            public void onReply(String reply) {
                addMessage(ErisConfig.name, reply, false);
                ErisVoice.speak(reply);
                thinking = false;
                updateStatus();
            }
        });
    }

    private void addMessage(String who, String text, boolean mine) {
        messages.addView(ErisViews.makeMessage(this, who, text, mine));
        scroll.post(new Runnable() {
            @Override
            public void run() {
                scroll.fullScroll(View.FOCUS_DOWN);
            }
        });
    }
}
