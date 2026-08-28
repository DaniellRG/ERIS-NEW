package com.eris.android;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.IBinder;
import android.os.SystemClock;
import android.view.ContextThemeWrapper;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.animation.Animation;
import android.view.animation.ScaleAnimation;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Burbuja flotante de ERIS: tocá la burbuja y hablale (por voz), mantenela
 *  apretada para escribir. Minimizable a un puntito y ocultable desde la
 *  notificación, sin apagar a ERIS. */
public class ErisOverlayService extends Service {
    private static final String CHANNEL_ID = "eris_overlay";
    private static final int NOTIF_ID = 1;
    private static final int RC_HIDE = 1;
    private static final int RC_SHOW = 2;

    public static boolean running = false;

    private WindowManager wm;
    private ContextThemeWrapper themed;
    private View bubble;
    private TextView bubbleTv;
    private View panel;
    private WindowManager.LayoutParams bubbleParams;
    private WindowManager.LayoutParams panelParams;
    private LinearLayout messages;
    private ScrollView scroll;
    private EditText input;
    private boolean panelVisible = false;
    private boolean bubbleVisible = false;
    private boolean minimized = false;
    private float touchStartX, touchStartY;
    private int startX, startY;
    private boolean dragged = false;
    private long downTime;

    @Override
    public void onCreate() {
        super.onCreate();
        running = true;
        wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        ErisConfig.load(getApplicationContext());
        ErisVoice.init(getApplicationContext());
        themed = new ContextThemeWrapper(this, ErisConfig.themeRes());
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : null;
        if ("com.eris.android.HIDE_BUBBLE".equals(action)) {
            hideBubble();
        } else if ("com.eris.android.SHOW_BUBBLE".equals(action)) {
            showBubble();
        } else {
            if (bubble == null) buildBubble();
            if (panel == null) buildPanel();
        }
        startForegroundCompat();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        running = false;
        try { if (bubble != null) wm.removeView(bubble); } catch (Exception ignore) { }
        try { if (panel != null && panelVisible) wm.removeView(panel); } catch (Exception ignore) { }
        bubble = null;
        panel = null;
        panelVisible = false;
        bubbleVisible = false;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void startForegroundCompat() {
        createChannel();
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_IMMUTABLE);
        String label = bubbleVisible ? "Ocultar burbuja" : "Mostrar burbuja";
        String act = bubbleVisible ? "com.eris.android.HIDE_BUBBLE"
                : "com.eris.android.SHOW_BUBBLE";
        int rc = bubbleVisible ? RC_HIDE : RC_SHOW;
        Intent a = new Intent(this, ErisOverlayService.class).setAction(act);
        PendingIntent pa = PendingIntent.getService(this, rc, a,
                PendingIntent.FLAG_IMMUTABLE);
        Notification n = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("ERIS activa")
                .setContentText("Tocá la burbuja y hablale, o mantenela para escribir")
                .setSmallIcon(R.drawable.ic_launcher)
                .setContentIntent(pi)
                .addAction(0, label, pa)
                .setOngoing(true)
                .build();
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(NOTIF_ID, n);
        }
    }

    private void createChannel() {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm == null) return;
        NotificationChannel ch = new NotificationChannel(CHANNEL_ID,
                "ERIS flotante", NotificationManager.IMPORTANCE_LOW);
        ch.setDescription("Mantiene la burbuja de ERIS activa");
        nm.createNotificationChannel(ch);
    }

    private int dp(int v) {
        return ErisViews.dp(this, v);
    }

    private void buildBubble() {
        bubble = LayoutInflater.from(themed).inflate(R.layout.overlay_bubble, null);
        bubbleTv = (TextView) bubble;
        int size = ErisConfig.bubbleSize == 0 ? dp(48)
                : (ErisConfig.bubbleSize == 2 ? dp(72) : dp(58));
        bubbleParams = new WindowManager.LayoutParams(
                size, size,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT);
        bubbleParams.gravity = Gravity.TOP | Gravity.START;
        bubbleParams.x = dp(12);
        bubbleParams.y = dp(180);
        bubble.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent e) {
                switch (e.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        touchStartX = e.getRawX();
                        touchStartY = e.getRawY();
                        startX = bubbleParams.x;
                        startY = bubbleParams.y;
                        downTime = SystemClock.uptimeMillis();
                        dragged = false;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        int dx = Math.round(e.getRawX() - touchStartX);
                        int dy = Math.round(e.getRawY() - touchStartY);
                        bubbleParams.x = startX + dx;
                        bubbleParams.y = startY + dy;
                        wm.updateViewLayout(bubble, bubbleParams);
                        if (Math.abs(dx) > 8 || Math.abs(dy) > 8) dragged = true;
                        return true;
                    case MotionEvent.ACTION_UP:
                        if (dragged) return true;
                        boolean longPress = SystemClock.uptimeMillis() - downTime >= 500;
                        if (minimized) {
                            restore();
                            if (!longPress) bubbleTalk();
                        } else if (longPress) {
                            togglePanel();
                        } else {
                            bubbleTalk();
                        }
                        return true;
                }
                return false;
            }
        });
        wm.addView(bubble, bubbleParams);
        bubbleVisible = true;
    }

    private void buildPanel() {
        panel = LayoutInflater.from(themed).inflate(R.layout.overlay_panel, null);
        int w = (int) (getResources().getDisplayMetrics().widthPixels * 0.94f);
        int h = (int) (getResources().getDisplayMetrics().heightPixels * 0.55f);
        panelParams = new WindowManager.LayoutParams(
                w, h,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT);
        panelParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        panelParams.y = dp(120);
        panelParams.softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE;

        messages = (LinearLayout) panel.findViewById(R.id.panelMessages);
        scroll = (ScrollView) panel.findViewById(R.id.panelScroll);
        input = (EditText) panel.findViewById(R.id.panelInput);
        Button sendBtn = (Button) panel.findViewById(R.id.panelSend);
        Button micBtn = (Button) panel.findViewById(R.id.panelMic);
        TextView statusTv = (TextView) panel.findViewById(R.id.panelStatus);
        Button btnEye = (Button) panel.findViewById(R.id.panelEye);
        Button btnVoice = (Button) panel.findViewById(R.id.panelVoice);
        Button btnHide = (Button) panel.findViewById(R.id.panelHide);
        Button btnMin = (Button) panel.findViewById(R.id.panelMin);
        Button btnClose = (Button) panel.findViewById(R.id.panelClose);

        TextView titleTv = (TextView) panel.findViewById(R.id.panelTitle);
        titleTv.setText(ErisConfig.name);
        statusTv.setText(ErisAccessibilityService.isRunning()
                ? "Accesibilidad ACTIVA" : "Accesibilidad INACTIVA");
        btnVoice.setText(ErisVoice.enabled ? "🔊 ON" : "🔇 OFF");

        sendBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { send(); }
        });
        micBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { micListen(); }
        });
        btnEye.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                input.setText("¿Qué hay en pantalla?");
                send();
            }
        });
        btnVoice.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ErisVoice.enabled = !ErisVoice.enabled;
                ErisConfig.voiceEnabled = ErisVoice.enabled;
                ErisConfig.save(ErisOverlayService.this);
                btnVoice.setText(ErisVoice.enabled ? "🔊 ON" : "🔇 OFF");
            }
        });
        btnHide.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { togglePanel(); }
        });
        btnMin.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { minimize(); }
        });
        btnClose.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { stopSelf(); }
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
        input.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent e) {
                if (e.getActionMasked() == MotionEvent.ACTION_DOWN) {
                    setPanelFocusable(true);
                    input.requestFocus();
                }
                return false;
            }
        });
        input.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override
            public void onFocusChange(View v, boolean hasFocus) {
                if (!hasFocus) setPanelFocusable(false);
            }
        });
    }

    private void setPanelFocusable(boolean focusable) {
        try {
            if (focusable) {
                panelParams.flags &= ~WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE;
            } else {
                panelParams.flags |= WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE;
            }
            wm.updateViewLayout(panel, panelParams);
        } catch (Exception ignore) { }
    }

    private void togglePanel() {
        if (minimized) {
            restore();
            return;
        }
        if (panelVisible) {
            try { wm.removeView(panel); } catch (Exception ignore) { }
            panelVisible = false;
        } else {
            try { wm.addView(panel, panelParams); } catch (Exception ignore) { }
            panelVisible = true;
        }
    }

    private void minimize() {
        if (panelVisible) togglePanel();
        stopListenFeedback();
        minimized = true;
        bubble.setAlpha(0.85f);
        bubbleTv.setTextSize(14f);
        int w = getResources().getDisplayMetrics().widthPixels;
        int h = getResources().getDisplayMetrics().heightPixels;
        bubbleParams.x = w - dp(28) - dp(16);
        bubbleParams.y = h - dp(28) - dp(110);
        setBubbleSize(dp(28));
    }

    private void restore() {
        minimized = false;
        bubble.setAlpha(1f);
        bubbleTv.setTextSize(26f);
        int size = ErisConfig.bubbleSize == 0 ? dp(48)
                : (ErisConfig.bubbleSize == 2 ? dp(72) : dp(58));
        setBubbleSize(size);
    }

    private void setBubbleSize(int size) {
        try {
            bubbleParams.width = size;
            bubbleParams.height = size;
            wm.updateViewLayout(bubble, bubbleParams);
        } catch (Exception ignore) { }
    }

    private void hideBubble() {
        try {
            if (bubble != null && bubbleVisible) {
                wm.removeView(bubble);
                bubbleVisible = false;
            }
        } catch (Exception ignore) { }
    }

    private void showBubble() {
        try {
            if (bubble != null && !bubbleVisible) {
                wm.addView(bubble, bubbleParams);
                bubbleVisible = true;
            }
        } catch (Exception ignore) { }
    }

    private void send() {
        String t = input.getText().toString().trim();
        if (t.isEmpty()) return;
        input.setText("");
        input.clearFocus();
        setPanelFocusable(false);
        submitText(t, false);
    }

    private void bubbleTalk() {
        if (ErisChat.isBusy()) return;
        startListenFeedback();
        ErisVoice.listen(getApplicationContext(), new ErisVoice.Result() {
            @Override
            public void onText(String text) {
                stopListenFeedback();
                if (text == null || text.trim().isEmpty()) {
                    addMessage("Sistema", "No te escuché bien, repetí.", false);
                    return;
                }
                submitText(text, true);
            }
        });
    }

    private void submitText(String t, boolean asVoice) {
        if (t.trim().isEmpty() || ErisChat.isBusy()) return;
        if (asVoice) addMessage("Tú", t, true);
        ErisChat.send(getApplicationContext(), t, new ErisChat.Callback() {
            @Override
            public void onReply(String reply) {
                addMessage(ErisConfig.name, reply, false);
                ErisVoice.speak(reply);
            }
        });
    }

    private void micListen() {
        ErisVoice.listen(getApplicationContext(), new ErisVoice.Result() {
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

    private void startListenFeedback() {
        if (bubbleTv == null) return;
        ScaleAnimation a = new ScaleAnimation(1f, 1.18f, 1f, 1.18f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f);
        a.setDuration(450);
        a.setRepeatMode(Animation.REVERSE);
        a.setRepeatCount(Animation.INFINITE);
        bubbleTv.startAnimation(a);
    }

    private void stopListenFeedback() {
        if (bubbleTv != null) bubbleTv.clearAnimation();
    }

    private void addMessage(String who, String text, boolean mine) {
        if (messages == null) return;
        messages.addView(ErisViews.makeMessage(themed != null ? themed : this, who, text, mine));
        if (scroll != null) {
            scroll.post(new Runnable() {
                @Override
                public void run() {
                    scroll.fullScroll(View.FOCUS_DOWN);
                }
            });
        }
    }
}
