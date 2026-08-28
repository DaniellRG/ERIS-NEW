package com.eris.android;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

/** Envía un mensaje al cerebro de ERIS y devuelve la respuesta por callback.
 *  Permite un solo mensaje en curso a la vez (compartido entre la app y la burbuja). */
public final class ErisChat {
    public interface Callback {
        void onReply(String reply);
    }

    private static boolean busy = false;

    private ErisChat() {}

    public static boolean isBusy() {
        return busy;
    }

    public static void send(final Context ctx, final String userText, final Callback cb) {
        if (userText == null || userText.trim().isEmpty() || busy) return;
        busy = true;
        new Thread(new Runnable() {
            @Override
            public void run() {
                String reply;
                try {
                    reply = ErisBrain.reply(ctx, userText.trim());
                    ErisMemory.addTurn(ctx, userText.trim(), reply);
                } catch (Exception e) {
                    reply = "Se me cortó el hilo, perdón. " + e.getMessage();
                } finally {
                    busy = false;
                }
                if (cb != null) {
                    final String r = reply;
                    new Handler(Looper.getMainLooper()).post(new Runnable() {
                        @Override
                        public void run() {
                            cb.onReply(r);
                        }
                    });
                }
            }
        }).start();
    }
}
