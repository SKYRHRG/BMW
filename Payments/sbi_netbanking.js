// Payments/sbi_netbanking.js

console.log("OCEAN: SBI Netbanking script loaded.");

// ✨ OTP भरने का सिग्नल सुनने के लिए लिस्नर (बिना देरी के) ✨
document.addEventListener('OTP_FILLED', () => {
    console.log("OCEAN: SBI Page - 'OTP_FILLED' signal received.");
    
    const confirmButton = document.querySelector('button#confirmButton');
    
    if (confirmButton) {
        console.log("OCEAN: SBI Confirm button found. Clicking it immediately.");
        // setTimeout हटा दिया गया है ताकि तुरंत क्लिक हो
        confirmButton.click();
    } else {
        console.warn("OCEAN: SBI Confirm button not found on this page.");
    }
});

// --- स्वचालन प्रक्रिया तुरंत शुरू करें ---
automateSbiFlow();

function automateSbiFlow() {
    chrome.storage.local.get('other_preferences', (data) => {
        const preferences = data.other_preferences;

        if (preferences && preferences.paymentmethod === 'SBINETBANKING' && preferences.sbi_username) {
            console.log("OCEAN: SBI Netbanking flow started.");
            runSbiAutomation(preferences); // अपडेटेड फंक्शन को कॉल करें
        } else {
            console.log("OCEAN: Not an SBI Netbanking flow or details are missing.");
        }
    });
}

function runSbiAutomation(prefs) {
    // एक तेज़ अंतराल पर जाँच करें
    const sbiInterval = setInterval(() => {
        
        // --- चरण 1: लॉगिन पेज ---
        // पेज पर लॉगिन फॉर्म ढूंढें
        const usernameInput = document.querySelector('#username');
        if (usernameInput && usernameInput.value === "") { // केवल तभी भरें जब खाली हो
            console.log("OCEAN: Login page detected. Filling details...");
            usernameInput.value = prefs.sbi_username;
            document.querySelector('#label2').value = prefs.sbi_password;
            document.querySelector('input.btn.btn-Yellow[value="Login"]').click();
            // यहाँ clearInterval नहीं करेंगे ताकि अगले पेज पर तुरंत काम हो
            return; 
        }

        // --- चरण 2: खाता चयन (Account Selection) ---
        // अकाउंट रेडियो बटन ढूंढें और अगर चयनित नहीं है तो क्लिक करें
        const accountRadio = document.querySelector('#drd0');
        if (accountRadio && !accountRadio.checked) {
            console.log("OCEAN: Account selection radio button detected. Clicking...");
            accountRadio.click();
            return;
        }

        // --- चरण 3: भुगतान की पुष्टि (OTP से पहले) ---
        // प्री-OTP कन्फर्म बटन ढूंढें और क्लिक करें
        const preOtpConfirmButton = document.querySelector('button#Go.btn.btn-Yellow');
        if (preOtpConfirmButton) {
            console.log("OCEAN: Pre-OTP confirm button detected. Clicking...");
            preOtpConfirmButton.click();
            // यह अंतिम चरण है, इसलिए अब अंतराल को साफ़ कर दें
            clearInterval(sbiInterval);
            return;
        }

    }, 200); // 🚀 हर 0.2 सेकंड में पृष्ठ की जांच करें (पहले 1 सेकंड था)
}