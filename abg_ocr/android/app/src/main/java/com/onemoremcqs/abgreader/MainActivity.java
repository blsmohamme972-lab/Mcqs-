package com.onemoremcqs.abgreader;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.core.content.FileProvider;
import androidx.webkit.WebViewAssetLoader;

import java.io.File;

/** Hosts the ABG reader page from bundled assets; OCR runs offline inside the WebView. */
public class MainActivity extends Activity {
    private static final int PICK = 1;
    private WebView web;
    private ValueCallback<Uri[]> pending;
    private Uri photoUri;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        setContentView(web);

        // Serve assets/ at https://appassets.androidplatform.net/assets/ so workers and fetch() work.
        final WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return loader.shouldInterceptRequest(request.getUrl());
            }

            // The page (and the ML Kit bridge) only ever runs from the bundled assets.
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !"appassets.androidplatform.net".equals(request.getUrl().getHost());
            }
        });
        web.addJavascriptInterface(new OcrBridge(this, web), "AbgNative");
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (pending != null) pending.onReceiveValue(null);
                pending = callback;
                Intent camera = cameraIntent();
                Intent pick;
                if (params.isCaptureEnabled() && camera != null) {
                    pick = camera;
                } else {
                    pick = Intent.createChooser(params.createIntent(), "اختر صورة");
                    if (camera != null) pick.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{camera});
                }
                try {
                    startActivityForResult(pick, PICK);
                } catch (ActivityNotFoundException e) {
                    pending = null;
                    callback.onReceiveValue(null);
                    return false;
                }
                return true;
            }
        });

        if (state == null) web.loadUrl("https://appassets.androidplatform.net/assets/index.html");
        else web.restoreState(state);
    }

    private Intent cameraIntent() {
        try {
            File dir = new File(getCacheDir(), "photos");
            if (!dir.exists() && !dir.mkdirs()) return null;
            File f = new File(dir, "abg_" + System.currentTimeMillis() + ".jpg");
            photoUri = FileProvider.getUriForFile(this, getPackageName() + ".files", f);
            Intent i = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            i.putExtra(MediaStore.EXTRA_OUTPUT, photoUri);
            i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            return i;
        } catch (Exception e) {
            return null;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK || pending == null) return;
        Uri[] result = null;
        if (resultCode == RESULT_OK) {
            if (data != null && data.getData() != null) result = new Uri[]{data.getData()};
            else if (photoUri != null) result = new Uri[]{photoUri};   // camera wrote to EXTRA_OUTPUT
        }
        pending.onReceiveValue(result);
        pending = null;
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
