// 🔁 OTP Page पर script load होते ही Remarks को smartly भरने का logic
chrome.storage.local.get('hdfc_stage', (data) => {
    if (data.hdfc_stage === "logged_in") {
        console.log("OCEAN: OTP Page detected. Waiting for remarks field to appear...");

        let retryCount = 0;
        const maxRetries = 20; // 10 seconds

        const remarksInterval = setInterval(() => {
            const remarksInput = document.querySelector('#TranRequestManagerFG\\.CP_REMARKS_SINGLE');

            if (remarksInput) {
                clearInterval(remarksInterval);
                remarksInput.value = "joker";
                remarksInput.dispatchEvent(new Event('input', { bubbles: true }));
                console.log("OCEAN: Remarks input filled early with 'joker'. ✅");
            } else {
                retryCount++;
                if (retryCount > maxRetries) {
                    clearInterval(remarksInterval);
                    console.warn("OCEAN: Remarks input not found after waiting.");
                }
            }
        }, 100);
    }
});


// ✨ OTP भरने का सिग्नल सुनने के लिए लिस्नर ✨
document.addEventListener('OTP_FILLED', () => {
    console.log("OCEAN: HDFC Page - 'OTP_FILLED' signal received.");

    // ✅ Remarks पहले ही भरा जा चुका होगा ऊपर वाले ब्लॉक में

    // ✅ अब Pay बटन क्लिक करें
    const finalPayButton = document.getElementById('SUBMIT_TRANSACTION');
    
    if (finalPayButton) {
        console.log("OCEAN: HDFC Final Pay button found. Clicking it.");
        setTimeout(() => {
            finalPayButton.click();

            // ✅ Payment के बाद stage reset करें
            chrome.storage.local.remove('hdfc_stage', () => {
                console.log("OCEAN: hdfc_stage reset after payment.");
            });

        }, 100);
    } else {
        console.warn("OCEAN: HDFC Final Pay button not found on this page.");
    }
});


// --- 🔁 Login Automation शुरू करें ---
automateHdfcFlow();

function automateHdfcFlow() {
    chrome.storage.local.get('other_preferences', (data) => {
        const preferences = data.other_preferences;
        
        if (preferences && preferences.paymentmethod === 'HDFCNETBANKING' && preferences.hdfc_username) { 
            console.log("OCEAN: HDFC Netbanking flow started. Details found.");
            initiateStep1(preferences); 
        } else {
            console.log("OCEAN: Not an HDFC Netbanking flow or details are missing.");
        }
    });
}

function initiateStep1(prefs) {
    const step1Interval = setInterval(() => {
        const userIdInput = document.getElementById('AuthenticationFG.USER_PRINCIPAL'); 

        if (userIdInput) {
            console.log("OCEAN: Step 1 - User ID input found. Clicking it...");
            clearInterval(step1Interval);
            userIdInput.click();
            initiateStep2(prefs);
        }
    }, 100); 
}

function initiateStep2(prefs) {
    const step2Interval = setInterval(() => {
        const userIdInput = document.getElementById('AuthenticationFG.USER_PRINCIPAL');
        const passwordInput = document.getElementById('AuthenticationFG.ACCESS_CODE');
        const loginButton = document.getElementById('VALIDATE_CREDENTIALS');

        if (userIdInput && passwordInput && loginButton) {
            console.log("OCEAN: Step 2 - All login elements are visible.");
            clearInterval(step2Interval);

            // --- Fill User ID ---
            userIdInput.value = prefs.hdfc_username;
            userIdInput.dispatchEvent(new Event('input', { bubbles: true }));
            userIdInput.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
            console.log("OCEAN: HDFC User ID filled and events dispatched.");

            // --- Fill Password ---
            passwordInput.value = prefs.hdfc_password;
            passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
            passwordInput.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
            console.log("OCEAN: HDFC Password filled and events dispatched.");

            // --- Login Click ---
            setTimeout(() => {
                console.log("OCEAN: Clicking the login button.");
                loginButton.click();
                console.log("OCEAN: HDFC login flow completed.");

                // ✅ Stage set for next page
                chrome.storage.local.set({ hdfc_stage: "logged_in" }, () => {
                    console.log("OCEAN: hdfc_stage set to 'logged_in'.");
                });

            }, 100);
        }
    }, 100);
}
