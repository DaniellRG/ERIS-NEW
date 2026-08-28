package com.eris.android;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Intent;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Servicio de accesibilidad de ERIS: ejecuta gestos y lee la pantalla del teléfono. */
public class ErisAccessibilityService extends AccessibilityService {
    private static final String TAG = "ErisAccessibility";
    private static ErisAccessibilityService instance;
    private static Handler mainHandler;

    private static final int MAX_HIST = 25;
    private static final Object histLock = new Object();
    private static String currentPkg = null;
    private static String currentTitle = "";
    private static final List<String> openedHist = new ArrayList<String>();
    private static final List<String> closedHist = new ArrayList<String>();

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        mainHandler = new Handler(Looper.getMainLooper());
        Log.i(TAG, "Servicio de accesibilidad de ERIS conectado.");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        try {
            if (event.getEventType() != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) return;
            CharSequence pkg = event.getPackageName();
            if (pkg == null) return;
            String p = pkg.toString();
            if (p.startsWith("com.eris.android")) return;
            CharSequence title = (event.getText() != null && event.getText().size() > 0)
                    ? event.getText().get(0) : null;
            String t = title != null ? title.toString().trim() : "";
            String label = labelFor(p);
            synchronized (histLock) {
                if (currentPkg != null && !currentPkg.equals(p)) {
                    closedHist.add(0, labelFor(currentPkg) + " (se cerró)");
                    if (closedHist.size() > MAX_HIST) closedHist.remove(closedHist.size() - 1);
                }
                currentPkg = p;
                currentTitle = t;
                String entry = t.isEmpty() || t.equalsIgnoreCase(label)
                        ? label : label + " — " + t;
                if (openedHist.isEmpty() || !openedHist.get(0).equals(entry)) {
                    openedHist.add(0, entry);
                    if (openedHist.size() > MAX_HIST) openedHist.remove(openedHist.size() - 1);
                }
            }
        } catch (Exception ignore) { }
    }

    @Override
    public void onInterrupt() { }

    @Override
    public boolean onUnbind(Intent intent) {
        if (instance == this) instance = null;
        return super.onUnbind(intent);
    }

    @Override
    public void onDestroy() {
        if (instance == this) instance = null;
        super.onDestroy();
    }

    public static boolean isRunning() {
        return instance != null;
    }

    /** Ejecuta una tarea en el hilo principal (requisito del servicio) y espera el resultado. */
    private static synchronized Object sync(Callable<Object> task, long timeoutMs) {
        if (instance == null || mainHandler == null) return null;
        final CountDownLatch latch = new CountDownLatch(1);
        final Object[] result = { null };
        final Callable<Object> t = task;
        mainHandler.post(new Runnable() {
            @Override
            public void run() {
                try {
                    result[0] = t.call();
                } catch (Exception e) {
                    result[0] = "ERROR: " + e.getMessage();
                }
                latch.countDown();
            }
        });
        try {
            latch.await(timeoutMs, TimeUnit.MILLISECONDS);
        } catch (Exception ignore) { }
        return result[0];
    }

    public static void fireGesture(final Path path, final long durationMs) {
        sync(new Callable<Object>() {
            @Override
            public Object call() {
                GestureDescription.Builder b = new GestureDescription.Builder();
                b.addStroke(new GestureDescription.StrokeDescription(path, 0, durationMs));
                instance.dispatchGesture(b.build(), null, null);
                return null;
            }
        }, 3000);
    }

    public static boolean globalAction(final int action) {
        Object r = sync(new Callable<Object>() {
            @Override
            public Object call() {
                return instance.performGlobalAction(action);
            }
        }, 3000);
        return r instanceof Boolean && (Boolean) r;
    }

    /** Devuelve la raíz de la ventana de la app visible bajo la burbuja de ERIS
     *  (salta las ventanas de com.eris.android). Con esto ERIS "ve" la app real. */
    public static AccessibilityNodeInfo getAppWindowRoot() {
        try {
            List<AccessibilityWindowInfo> wins = instance.getWindows();
            if (wins != null) {
                for (AccessibilityWindowInfo w : wins) {
                    if (w.getType() != AccessibilityWindowInfo.TYPE_APPLICATION) continue;
                    AccessibilityNodeInfo r = w.getRoot();
                    if (r == null) continue;
                    CharSequence pkg = r.getPackageName();
                    if (pkg != null && pkg.toString().startsWith("com.eris.android")) {
                        r.recycle();
                        continue;
                    }
                    return r;
                }
            }
        } catch (Exception ignore) { }
        return instance.getRootInActiveWindow();
    }

    /** Devuelve los textos visibles en pantalla con sus coordenadas (máx 30). */
    public static String screenText() {
        Object res = sync(new Callable<Object>() {
            @Override
            public Object call() {
                AccessibilityNodeInfo root = getAppWindowRoot();
                if (root == null) return "";
                List<String> lines = new ArrayList<String>();
                collect(root, lines);
                StringBuilder sb = new StringBuilder();
                for (String l : lines) sb.append(l).append("\n");
                return sb.toString().trim();
            }
        }, 6000);
        return res == null ? "" : res.toString();
    }

    private static void collect(AccessibilityNodeInfo node, List<String> lines) {
        if (node == null || lines.size() >= 30) return;
        CharSequence t = node.getText();
        CharSequence cd = node.getContentDescription();
        String label = (t != null && t.length() > 0)
                ? t.toString()
                : (cd != null ? cd.toString() : "");
        if (!label.trim().isEmpty()) {
            Rect r = new Rect();
            node.getBoundsInScreen(r);
            if (r.width() > 0 && r.height() > 0) {
                int cx = (r.left + r.right) / 2;
                int cy = (r.top + r.bottom) / 2;
                lines.add(label.replace('\n', ' ').replace('\r', ' ')
                        + " (" + cx + "," + cy + ")");
            }
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            collect(node.getChild(i), lines);
        }
    }

    /** Busca el nodo cuyo texto contiene el query y lo toca.
     *  Prioriza coincidencias exactas y labels cortos (evita tocar textos largos). */
    public static String tapText(final String query) {
        Object res = sync(new Callable<Object>() {
            @Override
            public Object call() {
                AccessibilityNodeInfo root = getAppWindowRoot();
                if (root == null) return "No puedo ver la pantalla.";
                String q = query.toLowerCase();
                AccessibilityNodeInfo target = findBest(root, q, true);
                if (target == null) target = findBest(root, q, false);
                if (target == null) return "No encontré '" + query + "' en pantalla.";
                Rect r = new Rect();
                target.getBoundsInScreen(r);
                int cx = (r.left + r.right) / 2;
                int cy = (r.top + r.bottom) / 2;
                String label = labelOf(target);
                boolean clicked = target.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                return (clicked ? "Toqué '" : "No pude tocar '")
                        + label + "' (" + cx + "," + cy + ").";
            }
        }, 8000);
        return res == null ? "No pude leer la pantalla." : res.toString();
    }

    private static String labelOf(AccessibilityNodeInfo node) {
        CharSequence t = node.getText();
        CharSequence cd = node.getContentDescription();
        String label = (t != null && t.length() > 0)
                ? t.toString()
                : (cd != null ? cd.toString() : "");
        return label.trim();
    }

    private static AccessibilityNodeInfo findBest(AccessibilityNodeInfo node,
                                                  String q, boolean exact) {
        if (node == null) return null;
        AccessibilityNodeInfo best = null;
        int bestLen = Integer.MAX_VALUE;
        boolean bestClickable = false;
        String label = labelOf(node);
        boolean m = exact ? label.toLowerCase().equals(q)
                          : label.toLowerCase().contains(q);
        if (m) {
            best = node;
            bestLen = label.length();
            bestClickable = node.isClickable();
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo c = findBest(node.getChild(i), q, exact);
            if (c == null) continue;
            int cl = labelOf(c).length();
            boolean cc = c.isClickable();
            if (cl < bestLen || (cl == bestLen && cc && !bestClickable)) {
                best = c;
                bestLen = cl;
                bestClickable = cc;
            }
        }
        return best;
    }

    /** Escribe texto en un campo de texto de la app visible (o el enfocado). */
    public static String typeText(final String text) {
        Object res = sync(new Callable<Object>() {
            @Override
            public Object call() {
                AccessibilityNodeInfo root = getAppWindowRoot();
                if (root == null) return "No puedo ver la pantalla.";
                AccessibilityNodeInfo target = null;
                AccessibilityNodeInfo focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
                if (focused != null && focused.isEditable()) target = focused;
                if (target == null) target = findEditable(root);
                if (target == null) return "No hay un campo de texto enfocado para escribir.";
                Bundle b = new Bundle();
                b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
                boolean ok = target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, b);
                return ok ? "Texto escrito." : "No pude escribir en el campo.";
            }
        }, 6000);
        return res == null ? "No pude escribir." : res.toString();
    }

    private static AccessibilityNodeInfo findEditable(AccessibilityNodeInfo node) {
        if (node == null) return null;
        if (node.isEditable()) return node;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo r = findEditable(node.getChild(i));
            if (r != null) return r;
        }
        return null;
    }

    public static String labelFor(String pkg) {
        try {
            android.content.pm.ApplicationInfo ai = instance.getPackageManager()
                    .getApplicationInfo(pkg, 0);
            CharSequence l = instance.getPackageManager().getApplicationLabel(ai);
            return l != null ? l.toString() : pkg;
        } catch (Exception e) {
            return pkg;
        }
    }

    /** Paquete de la app visible actualmente (o null si está en el inicio). */
    public static String currentApp() {
        synchronized (histLock) {
            return currentPkg;
        }
    }

    /** App en foco con etiqueta + título de ventana. */
    public static String foregroundInfo() {
        synchronized (histLock) {
            if (currentPkg == null) return "Ninguna app en foco (inicio del teléfono).";
            String label = labelFor(currentPkg);
            if (!currentTitle.isEmpty() && !currentTitle.equalsIgnoreCase(label)) {
                return "App en foco: " + label + " (" + currentPkg + "), pantalla '" + currentTitle + "'.";
            }
            return "App en foco: " + label + " (" + currentPkg + ").";
        }
    }

    /** Historial de apps abiertas y cerradas recientemente (para que Nyx "sepa" qué pasó). */
    public static String windowHistory() {
        StringBuilder sb = new StringBuilder();
        synchronized (histLock) {
            sb.append("App en foco: ").append(currentPkg != null ? labelFor(currentPkg) : "inicio")
                    .append("\n");
            sb.append("Abiertas recientemente:\n");
            if (openedHist.isEmpty()) sb.append(" - ninguna\n");
            int n = Math.min(openedHist.size(), 8);
            for (int i = 0; i < n; i++) sb.append(" - ").append(openedHist.get(i)).append("\n");
            sb.append("Cerradas/salidas recientemente:\n");
            if (closedHist.isEmpty()) sb.append(" - ninguna\n");
            n = Math.min(closedHist.size(), 8);
            for (int i = 0; i < n; i++) sb.append(" - ").append(closedHist.get(i)).append("\n");
        }
        return sb.toString().trim();
    }

    /** Lista de ventanas visibles en este momento (tipo, app, bounds, activa). */
    public static String windowList() {
        Object res = sync(new Callable<Object>() {
            @Override
            public Object call() {
                StringBuilder sb = new StringBuilder("Ventanas en pantalla:\n");
                try {
                    List<AccessibilityWindowInfo> wins = instance.getWindows();
                    if (wins == null || wins.isEmpty()) {
                        sb.append(" - ninguna ventana");
                        return sb.toString();
                    }
                    for (AccessibilityWindowInfo w : wins) {
                        int type = w.getType();
                        String t = type == AccessibilityWindowInfo.TYPE_APPLICATION ? "app"
                                : type == AccessibilityWindowInfo.TYPE_INPUT_METHOD ? "teclado"
                                : type == AccessibilityWindowInfo.TYPE_SYSTEM ? "sistema"
                                : type == AccessibilityWindowInfo.TYPE_SPLIT_SCREEN_DIVIDER ? "divisor"
                                : "tipo" + type;
                        String pkg = "?";
                        AccessibilityNodeInfo root = w.getRoot();
                        if (root != null) {
                            CharSequence p = root.getPackageName();
                            if (p != null) pkg = labelFor(p.toString());
                            root.recycle();
                        }
                        Rect r = new Rect();
                        w.getBoundsInScreen(r);
                        sb.append(" - ").append(t).append(" '").append(pkg)
                                .append("' ").append(r.left).append(",").append(r.top)
                                .append(" ").append(r.width()).append("x").append(r.height())
                                .append(w.isActive() ? " [ACTIVA]" : "").append("\n");
                    }
                } catch (Exception ignore) {
                    sb.append(" - no pude leerlas\n");
                }
                return sb.toString().trim();
            }
        }, 6000);
        return res == null ? "" : res.toString();
    }

    private static String nodeId(AccessibilityNodeInfo node) {
        try {
            String id = node.getViewIdResourceName();
            return id != null ? id : "";
        } catch (Exception e) {
            return "";
        }
    }

    private static void indexedNodes(AccessibilityNodeInfo node,
                                     List<AccessibilityNodeInfo> out, int cap) {
        if (node == null || out.size() >= cap) return;
        String label = labelOf(node);
        String id = nodeId(node);
        if (!label.isEmpty() || !id.isEmpty()) {
            Rect r = new Rect();
            node.getBoundsInScreen(r);
            if (r.width() > 0 && r.height() > 0) out.add(node);
        }
        for (int i = 0; i < node.getChildCount() && out.size() < cap; i++) {
            indexedNodes(node.getChild(i), out, cap);
        }
    }

    private static void recycleAll(List<AccessibilityNodeInfo> nodes) {
        for (AccessibilityNodeInfo n : nodes) {
            try { n.recycle(); } catch (Exception ignore) { }
        }
    }

    /** Pantalla actual numerada: [indice] etiqueta (x,y) [id] [click] — para que Nyx navegue. */
    public static String screenIndexed() {
        Object res = sync(new Callable<Object>() {
            @Override
            public Object call() {
                AccessibilityNodeInfo root = getAppWindowRoot();
                if (root == null) return "No puedo ver la pantalla (sin accesibilidad).";
                List<AccessibilityNodeInfo> nodes = new ArrayList<AccessibilityNodeInfo>();
                indexedNodes(root, nodes, 45);
                if (nodes.isEmpty()) return "No veo elementos en la pantalla actual.";
                StringBuilder sb = new StringBuilder("Elementos en pantalla (usá el índice [n] para tocar):\n");
                for (int i = 0; i < nodes.size(); i++) {
                    AccessibilityNodeInfo n = nodes.get(i);
                    Rect r = new Rect();
                    n.getBoundsInScreen(r);
                    int cx = (r.left + r.right) / 2;
                    int cy = (r.top + r.bottom) / 2;
                    String label = labelOf(n);
                    String id = nodeId(n);
                    String shortId = "";
                    if (!id.isEmpty()) {
                        int slash = id.lastIndexOf('/');
                        shortId = slash >= 0 ? id.substring(slash + 1) : id;
                    }
                    sb.append("[").append(i).append("] ");
                    if (!label.isEmpty()) sb.append('"').append(label.replace('\n', ' ').replace('\r', ' ')).append('"');
                    else sb.append("(sin texto)");
                    sb.append(" (").append(cx).append(",").append(cy).append(")");
                    if (!shortId.isEmpty()) sb.append(" id=").append(shortId);
                    if (n.isClickable()) sb.append(" click");
                    sb.append("\n");
                }
                recycleAll(nodes);
                return sb.toString().trim();
            }
        }, 8000);
        return res == null ? "No pude leer la pantalla." : res.toString();
    }

    /** Toca el elemento con el índice del dump numerado. */
    public static String tapIndex(final int idx) {
        Object res = sync(new Callable<Object>() {
            @Override
            public Object call() {
                AccessibilityNodeInfo root = getAppWindowRoot();
                if (root == null) return "No puedo ver la pantalla.";
                List<AccessibilityNodeInfo> nodes = new ArrayList<AccessibilityNodeInfo>();
                indexedNodes(root, nodes, 45);
                if (idx < 0 || idx >= nodes.size()) {
                    recycleAll(nodes);
                    return "El índice " + idx + " no existe. Mirá el dump actual de la pantalla.";
                }
                AccessibilityNodeInfo target = nodes.get(idx);
                Rect r = new Rect();
                target.getBoundsInScreen(r);
                String label = labelOf(target);
                boolean ok = target.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                recycleAll(nodes);
                return ok ? "Toqué el elemento " + idx + " ('" + label + "')."
                        : "No pude tocar el elemento " + idx + ".";
            }
        }, 8000);
        return res == null ? "No pude tocar." : res.toString();
    }

    /** Scrollea (gesto) hasta encontrar el texto y lo toca. Hasta 8 intentos. */
    public static String scrollToText(final String text) {
        Object res = sync(new Callable<Object>() {
            @Override
            public Object call() {
                if (text.trim().isEmpty()) return "Decime qué texto buscar.";
                String q = text.toLowerCase();
                for (int step = 0; step < 8; step++) {
                    AccessibilityNodeInfo root = getAppWindowRoot();
                    if (root != null) {
                        AccessibilityNodeInfo t = findBest(root, q, true);
                        if (t == null) t = findBest(root, q, false);
                        if (t != null) {
                            Rect r = new Rect();
                            t.getBoundsInScreen(r);
                            String label = labelOf(t);
                            boolean ok = t.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                            recycleTree(root);
                            return (ok ? "Toqué '" : "No pude tocar '") + label + "'.";
                        }
                        recycleTree(root);
                    }
                    Path p = new Path();
                    p.moveTo(540, 1700);
                    p.lineTo(540, 500);
                    GestureDescription.Builder b = new GestureDescription.Builder();
                    b.addStroke(new GestureDescription.StrokeDescription(p, 0, 400));
                    instance.dispatchGesture(b.build(), null, null);
                    try { Thread.sleep(500); } catch (Exception ignore) { }
                }
                return "No encontré '" + text + "' (scrolleé y no apareció).";
            }
        }, 15000);
        return res == null ? "No pude buscar en la pantalla." : res.toString();
    }

    private static void recycleTree(AccessibilityNodeInfo node) {
        if (node == null) return;
        for (int i = 0; i < node.getChildCount(); i++) {
            recycleTree(node.getChild(i));
        }
        try { node.recycle(); } catch (Exception ignore) { }
    }
}
