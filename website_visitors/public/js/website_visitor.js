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
            const FingerprintJS = await import('https://fpjscdn.net/v3/f4mouJmq9iqfBP6lH6O6');
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

    async function getSessionId() {
        const cachedSessionId = sessionStorage.getItem("sessionId");
        if (cachedSessionId){
            return cachedSessionId;
        }

        const sessionId = crypto.randomUUID();
        sessionStorage.setItem("sessionId", sessionId);
        return sessionId;
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
                form.submit();  // Continue normal form submission
            });
        })
    }

    function sendUserActivityEvent(fingerprintData, domain, websiteToken, sessionId, pageInfo, eventType, useBeacon = false) {
        const payload = {
            fingerprint: fingerprintData,
            website_token: websiteToken,
            session_id: sessionId,
            page_info: pageInfo,
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
        const sessionId = await getSessionId();

        let pageUrl = window.location.href;
        let pageOpenTime = new Date().toISOString();
        let hasExitedPage = false;
        let isNavigating = false;
        let debounceTimeout = null;

        function sendPageVisitEvent(eventType, pageCloseTime = null) {
            const pageInfo = {
                page_url: pageUrl,
                page_open_time: pageOpenTime,
                ...(pageCloseTime ? { page_close_time: pageCloseTime } : {})
            };
            sendUserActivityEvent(fingerprintData, domain, websiteToken, sessionId, pageInfo, eventType);
        }
        
        // Tracks initial page load
        sendPageVisitEvent("On Website Page");

        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "hidden" && !hasExitedPage && !isNavigating) {
                hasExitedPage = true;
                sendPageVisitEvent("Left Website Page", new Date().toISOString());
            } else if (document.visibilityState === "visible") {
                hasExitedPage = false;
                sendPageVisitEvent("On Website Page");
            }
        });

        function handlePageChange(newUrl) {
            if (newUrl !== pageUrl) {
                if (!hasExitedPage) {
                    isNavigating = true;
                    sendPageVisitEvent("Left Website Page", new Date().toISOString());
                }
    
                clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    pageUrl = newUrl;
                    pageOpenTime = new Date().toISOString();
                    hasExitedPage = false;
                    isNavigating = false;
                    sendPageVisitEvent("On Website Page");
                }, 200); // Delay to prevent instant double logging
            }
        }

        // Detect back/forward navigation
        window.addEventListener("popstate", function () {
            handlePageChange(window.location.href);
        });

        // Detect link clicks
        document.addEventListener("click", function (event) {
            const target = event.target.closest("a");
            if (target && target.href && target.origin === window.location.origin) {
                handlePageChange(target.href);
            }
        });
    }

    document.addEventListener("DOMContentLoaded", async function() {
        await getFingerprint();
        await getScriptSrc();
        await getSessionId();
        onFormSubmit()
        trackUserActivity();
    });
})();
