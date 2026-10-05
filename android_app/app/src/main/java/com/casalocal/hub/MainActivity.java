package com.casalocal.hub;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.util.Base64;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.security.spec.MGF1ParameterSpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.OAEPParameterSpec;
import javax.crypto.spec.PSource;

public class MainActivity extends Activity {
    private static final String PREFS = "casa_local_hub";
    private static final String SERVICE_TYPE = "_casalocal._tcp.";
    private static final byte[] MOBILE_AAD =
            "casa-local-hub-mobile-v1".getBytes(StandardCharsets.UTF_8);

    private final ExecutorService executor = Executors.newCachedThreadPool();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private SharedPreferences preferences;
    private String token = "";
    private NsdManager nsdManager;
    private NsdManager.DiscoveryListener discoveryListener;

    private TextView statusText;
    private EditText coreUrlInput;
    private EditText pairingCodeInput;
    private EditText accessIdInput;
    private EditText accessSecretInput;
    private EditText deviceIdInput;
    private Spinner regionSpinner;
    private Button syncKeysButton;
    private Button refreshDevicesButton;
    private LinearLayout deviceContainer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        preferences = getSharedPreferences(PREFS, MODE_PRIVATE);
        token = preferences.getString("token", "");
        nsdManager = (NsdManager) getSystemService(Context.NSD_SERVICE);

        statusText = findViewById(R.id.statusText);
        coreUrlInput = findViewById(R.id.coreUrlInput);
        pairingCodeInput = findViewById(R.id.pairingCodeInput);
        accessIdInput = findViewById(R.id.accessIdInput);
        accessSecretInput = findViewById(R.id.accessSecretInput);
        deviceIdInput = findViewById(R.id.deviceIdInput);
        regionSpinner = findViewById(R.id.regionSpinner);
        syncKeysButton = findViewById(R.id.syncKeysButton);
        refreshDevicesButton = findViewById(R.id.refreshDevicesButton);
        deviceContainer = findViewById(R.id.deviceContainer);

        accessSecretInput.setInputType(
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
        );

        String savedUrl = preferences.getString(
                "core_url",
                "http://homeassistant.local:8799"
        );
        coreUrlInput.setText(savedUrl);

        findViewById(R.id.findHubButton).setOnClickListener(v -> findHub());
        findViewById(R.id.connectButton).setOnClickListener(v -> connectCore());
        findViewById(R.id.pairButton).setOnClickListener(v -> pairApp());
        syncKeysButton.setOnClickListener(v -> syncTuyaKeys());
        refreshDevicesButton.setOnClickListener(v -> refreshDevices());

        updatePairedUi();
        if (!token.isEmpty()) {
            connectCore();
        }
    }

    @Override
    protected void onDestroy() {
        stopDiscovery();
        executor.shutdownNow();
        super.onDestroy();
    }

    private String coreUrl() {
        String value = coreUrlInput.getText().toString().trim();
        while (value.endsWith("/")) {
            value = value.substring(0, value.length() - 1);
        }
        return value;
    }

    private void saveCoreUrl() {
        preferences.edit().putString("core_url", coreUrl()).apply();
    }

    private void updatePairedUi() {
        boolean paired = !token.isEmpty();
        syncKeysButton.setEnabled(paired);
        refreshDevicesButton.setEnabled(paired);
        if (paired) {
            statusText.setText(R.string.paired);
            statusText.setTextColor(getColor(R.color.ok));
        }
    }

    private void setWorking() {
        statusText.setText(R.string.status_working);
        statusText.setTextColor(getColor(R.color.muted));
    }

    private void connectCore() {
        if (coreUrl().isEmpty()) {
            toast(R.string.connect_failed);
            return;
        }
        saveCoreUrl();
        setWorking();
        runNetwork(
                () -> request("GET", "/health", null, false),
                result -> {
                    if ("casa-local-core".equals(result.optString("service"))) {
                        if (token.isEmpty()) {
                            statusText.setText(R.string.connected);
                            statusText.setTextColor(getColor(R.color.ok));
                        } else {
                            statusText.setText(R.string.paired);
                            statusText.setTextColor(getColor(R.color.ok));
                            refreshDevices();
                        }
                    } else {
                        toast(R.string.connect_failed);
                    }
                },
                error -> {
                    statusText.setText(R.string.not_connected);
                    statusText.setTextColor(getColor(R.color.warn));
                    toast(R.string.connect_failed);
                }
        );
    }

    private void pairApp() {
        String code = pairingCodeInput.getText().toString().trim();
        if (code.length() != 8) {
            toast(R.string.enter_pair_code);
            return;
        }

        setWorking();
        runNetwork(
                () -> {
                    JSONObject payload = new JSONObject();
                    payload.put("code", code);
                    payload.put("label", "Casa Local Hub Android");
                    return request("POST", "/api/v1/pairing/complete", payload, false);
                },
                result -> {
                    String newToken = result.optString("token", "");
                    if (newToken.isEmpty()) {
                        toast(R.string.pair_failed);
                        return;
                    }
                    token = newToken;
                    preferences.edit().putString("token", token).apply();
                    pairingCodeInput.setText("");
                    updatePairedUi();
                    refreshDevices();
                },
                error -> toast(R.string.pair_failed)
        );
    }

    private void syncTuyaKeys() {
        if (token.isEmpty()) {
            toast(R.string.pair_first);
            return;
        }

        String apiKey = accessIdInput.getText().toString().trim();
        String apiSecret = accessSecretInput.getText().toString().trim();
        String region = String.valueOf(regionSpinner.getSelectedItem()).trim();
        String deviceId = deviceIdInput.getText().toString().trim();

        if (apiKey.isEmpty() || apiSecret.isEmpty() || region.isEmpty() || deviceId.isEmpty()) {
            toast(R.string.enter_all_fields);
            return;
        }

        setWorking();
        syncKeysButton.setEnabled(false);

        runNetwork(
                () -> {
                    JSONObject keyInfo = request(
                            "GET",
                            "/api/v1/mobile/public-key",
                            null,
                            true
                    );

                    JSONObject credentials = new JSONObject();
                    credentials.put("api_key", apiKey);
                    credentials.put("api_secret", apiSecret);
                    credentials.put("region", region);
                    credentials.put("device_id", deviceId);

                    JSONObject encrypted = encryptForCore(
                            keyInfo.getString("public_key_pem"),
                            credentials.toString().getBytes(StandardCharsets.UTF_8)
                    );
                    return request(
                            "POST",
                            "/api/v1/mobile/tuya/cloud-sync",
                            encrypted,
                            true
                    );
                },
                result -> {
                    accessSecretInput.setText("");
                    int found = result.optInt("cloud_devices", 0);
                    int matched = result.optInt("matched", 0);
                    int validated = result.optInt("communication_validated", 0);
                    Toast.makeText(
                            this,
                            getString(R.string.keys_summary, found, matched, validated),
                            Toast.LENGTH_LONG
                    ).show();
                    statusText.setText(R.string.paired);
                    statusText.setTextColor(getColor(R.color.ok));
                    syncKeysButton.setEnabled(true);
                    refreshDevices();
                },
                error -> {
                    accessSecretInput.setText("");
                    syncKeysButton.setEnabled(true);
                    toast(R.string.cloud_sync_failed);
                }
        );
    }

    private JSONObject encryptForCore(String publicKeyPem, byte[] plaintext) throws Exception {
        String cleanPem = publicKeyPem
                .replace("-----BEGIN PUBLIC KEY-----", "")
                .replace("-----END PUBLIC KEY-----", "")
                .replaceAll("\\s", "");
        byte[] der = Base64.decode(cleanPem, Base64.DEFAULT);
        PublicKey publicKey = KeyFactory.getInstance("RSA")
                .generatePublic(new X509EncodedKeySpec(der));

        KeyGenerator generator = KeyGenerator.getInstance("AES");
        generator.init(256);
        SecretKey aesKey = generator.generateKey();

        byte[] iv = new byte[12];
        new SecureRandom().nextBytes(iv);

        Cipher aes = Cipher.getInstance("AES/GCM/NoPadding");
        aes.init(Cipher.ENCRYPT_MODE, aesKey, new GCMParameterSpec(128, iv));
        aes.updateAAD(MOBILE_AAD);
        byte[] ciphertext = aes.doFinal(plaintext);

        OAEPParameterSpec oaepSpec = new OAEPParameterSpec(
                "SHA-256",
                "MGF1",
                MGF1ParameterSpec.SHA256,
                PSource.PSpecified.DEFAULT
        );
        Cipher rsa = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
        rsa.init(Cipher.ENCRYPT_MODE, publicKey, oaepSpec);
        byte[] encryptedKey = rsa.doFinal(aesKey.getEncoded());

        JSONObject result = new JSONObject();
        result.put("encrypted_key", Base64.encodeToString(encryptedKey, Base64.NO_WRAP));
        result.put("iv", Base64.encodeToString(iv, Base64.NO_WRAP));
        result.put("ciphertext", Base64.encodeToString(ciphertext, Base64.NO_WRAP));
        return result;
    }

    private void refreshDevices() {
        if (token.isEmpty()) {
            renderNoDevices();
            return;
        }

        runNetwork(
                () -> request("GET", "/api/v1/mobile/devices", null, true),
                result -> renderDevices(result.optJSONArray("devices")),
                error -> renderNoDevices()
        );
    }

    private void renderNoDevices() {
        deviceContainer.removeAllViews();
        TextView text = new TextView(this);
        text.setText(R.string.no_devices);
        text.setTextColor(getColor(R.color.muted));
        text.setPadding(0, dp(10), 0, dp(10));
        deviceContainer.addView(text);
    }

    private void renderDevices(JSONArray devices) {
        deviceContainer.removeAllViews();
        if (devices == null || devices.length() == 0) {
            renderNoDevices();
            return;
        }

        for (int index = 0; index < devices.length(); index++) {
            JSONObject device = devices.optJSONObject(index);
            if (device != null) {
                deviceContainer.addView(createDeviceCard(device));
            }
        }
    }

    private View createDeviceCard(JSONObject device) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(14), dp(14), dp(14));

        GradientDrawable background = new GradientDrawable();
        background.setColor(getColor(R.color.surface2));
        background.setCornerRadius(dp(17));
        background.setStroke(dp(1), getColor(R.color.line));
        card.setBackground(background);

        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        cardParams.setMargins(0, dp(7), 0, dp(7));
        card.setLayoutParams(cardParams);

        String name = device.optString("friendly_name", "");
        if (name.isEmpty()) {
            name = device.optString("name", "");
        }
        if (name.isEmpty()) {
            name = "Dispositivo local";
        }

        TextView title = new TextView(this);
        title.setText(name);
        title.setTextColor(getColor(R.color.text));
        title.setTextSize(17);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        card.addView(title);

        JSONObject metadata = device.optJSONObject("metadata");
        JSONObject validation = metadata != null ? metadata.optJSONObject("validation") : null;
        String communication = validation != null
                ? validation.optString("communication", "not_tested")
                : "not_tested";
        String control = validation != null
                ? validation.optString("control", "not_tested")
                : "not_tested";
        boolean integratable = validation != null
                && validation.optBoolean("integratable", false);

        TextView state = new TextView(this);
        if (integratable && "passed".equals(control)) {
            state.setText(R.string.device_validated);
            state.setTextColor(getColor(R.color.ok));
        } else if ("passed".equals(communication)) {
            state.setText(R.string.communication_validated);
            state.setTextColor(getColor(R.color.warn));
        } else if ("credentials_required".equals(device.optString("capability"))) {
            state.setText(R.string.credentials_required);
            state.setTextColor(getColor(R.color.warn));
        } else {
            state.setText(R.string.discovered);
            state.setTextColor(getColor(R.color.muted));
        }
        state.setPadding(0, dp(5), 0, 0);
        card.addView(state);

        String protocol = device.optString("protocol", "—");
        String address = device.optString("address", "—");
        TextView details = new TextView(this);
        details.setText(protocol + " · " + address);
        details.setTextColor(getColor(R.color.muted));
        details.setTextSize(12);
        details.setPadding(0, dp(7), 0, 0);
        card.addView(details);

        JSONObject profile = metadata != null ? metadata.optJSONObject("tuya_profile") : null;
        JSONObject lastDps = metadata != null ? metadata.optJSONObject("last_dps") : null;
        String switchDps = profile != null
                ? profile.optString("primary_switch_dps", "")
                : "";

        boolean isTuya = protocol.startsWith("tuya");
        boolean canControl = isTuya
                && "passed".equals(communication)
                && !switchDps.isEmpty();

        if (canControl) {
            boolean currentOn = false;
            boolean hasCurrent = false;
            if (lastDps != null && lastDps.has(switchDps)) {
                Object current = lastDps.opt(switchDps);
                if (current instanceof Boolean) {
                    currentOn = (Boolean) current;
                    hasCurrent = true;
                }
            }

            boolean targetValue = !hasCurrent || !currentOn;
            Button controlButton = new Button(this);
            controlButton.setAllCaps(false);
            controlButton.setTextColor(getColor(R.color.text));
            controlButton.setBackgroundResource(R.drawable.button_secondary);
            if (integratable) {
                controlButton.setText(
                        currentOn ? R.string.turn_off : R.string.turn_on
                );
            } else {
                controlButton.setText(
                        currentOn ? R.string.test_off : R.string.test_on
                );
            }

            String stableId = device.optString("stable_id");
            controlButton.setOnClickListener(
                    v -> sendControl(stableId, switchDps, targetValue)
            );

            LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    dp(48)
            );
            buttonParams.setMargins(0, dp(10), 0, 0);
            controlButton.setLayoutParams(buttonParams);
            card.addView(controlButton);
        }

        return card;
    }

    private void sendControl(String stableId, String dps, boolean value) {
        runNetwork(
                () -> {
                    JSONObject payload = new JSONObject();
                    payload.put("dps", dps);
                    payload.put("value", value);
                    String encodedId = URLEncoder.encode(
                            stableId,
                            StandardCharsets.UTF_8.toString()
                    );
                    return request(
                            "POST",
                            "/api/v1/devices/" + encodedId + "/tuya/control",
                            payload,
                            true
                    );
                },
                result -> {
                    if (result.optBoolean("control_validated", false)) {
                        toast(R.string.control_validated);
                    }
                    refreshDevices();
                },
                error -> toast(R.string.control_failed)
        );
    }

    private void findHub() {
        if (nsdManager == null) {
            toast(R.string.hub_not_found);
            return;
        }

        stopDiscovery();
        statusText.setText(R.string.status_working);
        statusText.setTextColor(getColor(R.color.muted));

        discoveryListener = new NsdManager.DiscoveryListener() {
            @Override
            public void onDiscoveryStarted(String serviceType) {
            }

            @Override
            public void onServiceFound(NsdServiceInfo serviceInfo) {
                if (!SERVICE_TYPE.equals(serviceInfo.getServiceType())) {
                    return;
                }
                nsdManager.resolveService(
                        serviceInfo,
                        new NsdManager.ResolveListener() {
                            @Override
                            public void onResolveFailed(
                                    NsdServiceInfo serviceInfo,
                                    int errorCode
                            ) {
                            }

                            @Override
                            public void onServiceResolved(NsdServiceInfo resolved) {
                                InetAddress host = resolved.getHost();
                                if (host == null) {
                                    return;
                                }
                                String url = "http://"
                                        + host.getHostAddress()
                                        + ":"
                                        + resolved.getPort();
                                mainHandler.post(() -> {
                                    coreUrlInput.setText(url);
                                    saveCoreUrl();
                                    toast(R.string.hub_found);
                                    stopDiscovery();
                                    connectCore();
                                });
                            }
                        }
                );
            }

            @Override
            public void onServiceLost(NsdServiceInfo serviceInfo) {
            }

            @Override
            public void onDiscoveryStopped(String serviceType) {
            }

            @Override
            public void onStartDiscoveryFailed(String serviceType, int errorCode) {
                mainHandler.post(() -> toast(R.string.hub_not_found));
                stopDiscovery();
            }

            @Override
            public void onStopDiscoveryFailed(String serviceType, int errorCode) {
            }
        };

        try {
            nsdManager.discoverServices(
                    SERVICE_TYPE,
                    NsdManager.PROTOCOL_DNS_SD,
                    discoveryListener
            );
            mainHandler.postDelayed(() -> {
                if (discoveryListener != null) {
                    toast(R.string.hub_not_found);
                    stopDiscovery();
                }
            }, 9000);
        } catch (Exception error) {
            toast(R.string.hub_not_found);
            stopDiscovery();
        }
    }

    private void stopDiscovery() {
        if (nsdManager != null && discoveryListener != null) {
            try {
                nsdManager.stopServiceDiscovery(discoveryListener);
            } catch (Exception ignored) {
            }
        }
        discoveryListener = null;
    }

    private JSONObject request(
            String method,
            String path,
            JSONObject body,
            boolean authenticated
    ) throws Exception {
        URL url = new URL(coreUrl() + path);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(25000);
        connection.setRequestProperty("Accept", "application/json");

        if (authenticated) {
            if (token.isEmpty()) {
                throw new IOException("Not paired");
            }
            connection.setRequestProperty("Authorization", "Bearer " + token);
        }

        if (body != null) {
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(bytes);
            }
        }

        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 300
                ? connection.getInputStream()
                : connection.getErrorStream();
        String response = readStream(stream);
        connection.disconnect();

        if (status < 200 || status >= 300) {
            throw new IOException("HTTP " + status + ": " + response);
        }
        if (response == null || response.trim().isEmpty()) {
            return new JSONObject();
        }
        return new JSONObject(response);
    }

    private String readStream(InputStream stream) throws IOException {
        if (stream == null) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(stream, StandardCharsets.UTF_8)
        )) {
            String line;
            while ((line = reader.readLine()) != null) {
                builder.append(line);
            }
        }
        return builder.toString();
    }

    private interface NetworkTask {
        JSONObject run() throws Exception;
    }

    private interface SuccessHandler {
        void accept(JSONObject value);
    }

    private interface ErrorHandler {
        void accept(Exception error);
    }

    private void runNetwork(
            NetworkTask task,
            SuccessHandler success,
            ErrorHandler failure
    ) {
        executor.execute(() -> {
            try {
                JSONObject value = task.run();
                mainHandler.post(() -> success.accept(value));
            } catch (Exception error) {
                mainHandler.post(() -> failure.accept(error));
            }
        });
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }

    private void toast(int resourceId) {
        Toast.makeText(this, resourceId, Toast.LENGTH_LONG).show();
    }
}
