package com.eris.android;

import android.content.Context;
import android.graphics.Color;
import android.view.Gravity;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Vista de burbuja de mensaje compartida entre la app y el panel flotante. */
public final class ErisViews {
    private ErisViews() {}

    public static LinearLayout makeMessage(Context ctx, String who, String text, boolean mine) {
        boolean system = "Sistema".equals(who);

        LinearLayout wrap = new LinearLayout(ctx);
        wrap.setOrientation(LinearLayout.VERTICAL);
        wrap.setPadding(0, 0, 0, dp(ctx, 8));
        wrap.setTag(who.toLowerCase());

        if (!system) {
            TextView label = new TextView(ctx);
            label.setText(who.toUpperCase());
            label.setTextSize(11);
            label.setLetterSpacing(0.08f);
            label.setTextColor(mine ? Color.parseColor("#B39DFF") : Color.parseColor("#8B7FD1"));
            LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
            llp.gravity = mine ? Gravity.END : Gravity.START;
            llp.bottomMargin = dp(ctx, 2);
            label.setLayoutParams(llp);
            wrap.addView(label);
        }

        TextView bubble = new TextView(ctx);
        bubble.setText(text);
        bubble.setTextSize(15.5f);
        bubble.setLineSpacing(0, 1.08f);
        bubble.setPadding(dp(ctx, 14), dp(ctx, 10), dp(ctx, 14), dp(ctx, 10));

        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        int marginSide = dp(ctx, 40);
        if (system) {
            bubble.setTextColor(Color.parseColor("#D9D4F5"));
            bubble.setBackgroundResource(R.drawable.bubble_system);
            blp.gravity = Gravity.CENTER_HORIZONTAL;
            marginSide = dp(ctx, 24);
        } else {
            bubble.setTextColor(Color.WHITE);
            if (mine) {
                bubble.setBackgroundResource(R.drawable.bubble_mine);
            } else {
                bubble.setBackgroundResource(R.drawable.bubble_eris);
            }
            blp.gravity = mine ? Gravity.END : Gravity.START;
        }
        blp.setMargins(mine ? marginSide : dp(ctx, 2), 0, mine ? dp(ctx, 2) : marginSide, 0);
        bubble.setLayoutParams(blp);
        bubble.setMaxWidth((int) (ctx.getResources().getDisplayMetrics().widthPixels * (system ? 0.7f : 0.85f)));

        if (!system && !mine) {
            final TextView tv = bubble;
            final String full = text;
            final int n = full.length();
            if (n > 0) {
                tv.setText("");
                final long dur = Math.min(3000L, 600L + n * 18L);
                final int steps = Math.max(10, Math.min(60, n / 4));
                final long stepMs = Math.max(20L, dur / steps);
                final int chunk = Math.max(1, n / steps);
                final android.os.Handler h = new android.os.Handler(android.os.Looper.getMainLooper());
                final int[] pos = { 0 };
                h.postDelayed(new Runnable() {
                    @Override
                    public void run() {
                        pos[0] = Math.min(n, pos[0] + chunk);
                        if (pos[0] >= n) tv.setText(full);
                        else {
                            tv.setText(full.substring(0, pos[0]));
                            h.postDelayed(this, stepMs);
                        }
                    }
                }, stepMs);
            }
        }

        wrap.addView(bubble);
        return wrap;
    }

    public static int dp(Context ctx, int v) {
        return Math.round(v * ctx.getResources().getDisplayMetrics().density);
    }
}
