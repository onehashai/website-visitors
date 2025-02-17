(function() {
    async function getFingerprint() {
        const cachedVisitorId = sessionStorage.getItem("visitorId");
        const cachedRequestId = sessionStorage.getItem("requestId");

        if (cachedVisitorId && cachedRequestId){
            return {
                'visitorId': cachedVisitorId,
                'requestId': cachedRequestId
            };
        }

        try {
            const FingerprintJS = await import(`https://fpjscdn.net/v3/${frappe.boot.fingerprint_api_key}`);
            const fp = await FingerprintJS.load({ region: "ap" });
            const result = await fp.get({ extendedResult: true });
            visitorId = result.visitorId;
            requestId = result.requestId;
            sessionStorage.setItem("visitorId", visitorId);
            sessionStorage.setItem("requestId", requestId);
            return {
                'visitorId': visitorId,
                'requestId': requestId
            }
        } catch (error) {
            console.error("FingerprintJS error:", error);
        }
    }

    async function getScriptSrc() {
        cachedWebsiteVisitorSrc = sessionStorage.getItem("websiteVisitorSrc");
        if (cachedWebsiteVisitorSrc){
            return cachedWebsiteVisitorSrc
        }
        const scripts = document.getElementsByTagName("script");
        
        for (let script of scripts) {
            if (script.src.includes("website_visitor.js")) {
                sessionStorage.setItem("websiteVisitorSrc", script.src);
                return script.src;
            }
        }
        return null;
    }

    async function extractDomainAndToken(url) {
        const urlObj = new URL(url);
        const domain = urlObj.hostname;
        const websiteToken = new URLSearchParams(urlObj.search).get('token');
        return { domain, websiteToken };
    }

    function sendFormData(fingerprint, domain, websiteToken, formData) {
        const payload = {
            fingerprint: fingerprint,
            website_token: websiteToken,
            form_data: formData,
        };
    
        try {
            fetch(`http://t1.localhost/api/method/website_visitors.website_visitors.doctype.api.handle_form_submission`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json" 
                },
                body: JSON.stringify(payload),
            });
        } catch (error) {
            console.error("Error sending form data:", error);
        }
    }

    function onFormSubmit() {
        document.querySelectorAll("form").forEach(form => {
            form.addEventListener("submit", async function(event) {
                event.preventDefault();  // Prevent form submission temporarily

                let formDataObj = {};
                let formData = new FormData(form);

                formData.forEach((value, key) => {
                    formDataObj[key] = value;
                });

                const fingerprint = await getFingerprint()
                const scriptSrc = await getScriptSrc()
                const { domain, websiteToken } = await extractDomainAndToken(scriptSrc);
                sendFormData(fingerprint, domain, websiteToken, formDataObj);
                form.submit();  // Continue normal form submission after capturing email
            });
        })
    }

    function sendUserActivityEvent(fingerprintData, domain, websiteToken, eventType, useBeacon = false) {
        const payload = {
            fingerprint: fingerprintData,
            website_token: websiteToken,
            event: eventType
        };

        if (useBeacon) {
            const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
            navigator.sendBeacon(`http://t1.localhost/api/method/website_visitors.website_visitors.doctype.api.track_activity`, blob);
        } else {
            fetch(`http://t1.localhost/api/method/website_visitors.website_visitors.doctype.api.track_activity`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });
        }
    }

    async function trackUserActivity() {
        const fingerprintData = await getFingerprint()
        const scriptSrc = await getScriptSrc()
        const { domain, websiteToken } = await extractDomainAndToken(scriptSrc);
        if (!sessionStorage.getItem("hasTrackedActivity")) {
            sendUserActivityEvent(fingerprintData, domain, websiteToken, "On Website");
            sessionStorage.setItem("hasTrackedActivity", "true");
        }

        window.addEventListener("pagehide", function(e) {
            sendUserActivityEvent(fingerprintData, domain, websiteToken, "Left Website", useBeacon = true);
        });
    }

    document.addEventListener("DOMContentLoaded", async function() {
        await getFingerprint();
        await getScriptSrc();
        onFormSubmit()
        trackUserActivity();
    });
})();
