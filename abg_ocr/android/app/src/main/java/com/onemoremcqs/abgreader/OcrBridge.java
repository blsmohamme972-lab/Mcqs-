package com.onemoremcqs.abgreader;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Rect;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Exposed to the page as window.AbgNative. Runs Google ML Kit text recognition on-device and
 * returns lines and words with boxes in the same shape the page builds from Tesseract.
 */
public class OcrBridge {
    private final Activity activity;
    private final WebView web;
    private final TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);

    OcrBridge(Activity activity, WebView web) {
        this.activity = activity;
        this.web = web;
    }

    @JavascriptInterface
    public void recognize(String jobId, String dataUrl) {
        Bitmap bmp;
        try {
            byte[] bytes = Base64.decode(dataUrl.substring(dataUrl.indexOf(',') + 1), Base64.DEFAULT);
            bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
        } catch (IllegalArgumentException e) {
            bmp = null;
        }
        if (bmp == null) {
            reply(jobId, null, "تعذّر فتح الصورة");
            return;
        }
        recognizer.process(InputImage.fromBitmap(bmp, 0))
                .addOnSuccessListener(text -> {
                    try {
                        reply(jobId, toJson(text).toString(), null);
                    } catch (JSONException e) {
                        reply(jobId, null, e.getMessage());
                    }
                })
                .addOnFailureListener(e -> reply(jobId, null, "Google ML Kit: " + e.getMessage()));
    }

    private static JSONObject toJson(Text text) throws JSONException {
        JSONArray lines = new JSONArray();
        for (Text.TextBlock block : text.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                JSONArray words = new JSONArray();
                for (Text.Element el : line.getElements()) {
                    words.put(new JSONObject()
                            .put("text", el.getText())
                            .put("confidence", el.getConfidence() * 100)
                            .put("bbox", box(el.getBoundingBox())));
                }
                lines.put(new JSONObject()
                        .put("text", line.getText())
                        .put("confidence", line.getConfidence() * 100)
                        .put("bbox", box(line.getBoundingBox()))
                        .put("words", words));
            }
        }
        return new JSONObject().put("text", text.getText()).put("lines", lines);
    }

    private static Object box(Rect r) throws JSONException {
        if (r == null) return JSONObject.NULL;
        return new JSONObject().put("x0", r.left).put("y0", r.top).put("x1", r.right).put("y1", r.bottom);
    }

    private void reply(String jobId, String json, String error) {
        String js = "window.__nativeOcrDone(" + JSONObject.quote(jobId) + ","
                + (json == null ? "null" : json) + ","
                + (error == null ? "null" : JSONObject.quote(error)) + ")";
        activity.runOnUiThread(() -> web.evaluateJavascript(js, null));
    }
}
