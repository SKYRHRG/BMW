// Payments/mobikwik_wallet.js

console.log("OCEAN: Mobikwik script loaded and ready.");

/**
 * यह फंक्शन पेज लोड होने पर चलता है और जांचता है कि
 * Mobikwik फ्लो के किस चरण में हम हैं।
 */
function initializeMobikwikFlow() {
    // चरण 1: क्या हम मोबाइल नंबर वाले पेज पर हैं?
    const mobileInput = document.querySelector('input#logininput');
    if (mobileInput) {
        console.log("OCEAN: Mobile number page detected.");
        fillMobileDetails(); // मोबाइल नंबर भरो और सबमिट करो
        return; 
    }

    // चरण 3: क्या हम फाइनल ट्रांजैक्शन OTP वाले पेज पर हैं?
    const finalPayButton = document.querySelector('input[value="Pay Now"]');
    if (finalPayButton) {
        console.log("OCEAN: Final Transaction OTP page detected. Waiting for OTP signal to click 'Pay Now'.");
        // यहाँ कुछ क्लिक नहीं करना है, सिर्फ OTP सिग्नल का इंतजार करना है।
        return;
    }

    // चरण 2: क्या हम पहले (लॉगिन) OTP वाले पेज पर हैं?
    const firstOtpSubmit = document.querySelector('input#verifyotpid');
    if (firstOtpSubmit) {
        console.log("OCEAN: First (Login) OTP page detected. Waiting for OTP signal.");
        return;
    }

    console.log("OCEAN: Waiting for a known Mobikwik page element...");
}

/**
 * यह फंक्शन मोबाइल नंबर और सबमिट बटन ढूंढकर कार्रवाई करता है।
 */
function fillMobileDetails() {
    chrome.storage.local.get('other_preferences', (data) => {
        const preferences = data.other_preferences;

        if (preferences && preferences.paymentmethod === 'MOBIKWIKWAL' && preferences.mobikwik_mobile) {
            const mobileInput = document.querySelector('input#logininput');
            const submitButton = document.querySelector('input#signinFrm.trigButtn');

            if (mobileInput && submitButton) {
                console.log("OCEAN: Filling Mobikwik mobile number.");
                mobileInput.value = preferences.mobikwik_mobile;
                
                // इनपुट इवेंट भेजें ताकि वेबसाइट रिएक्ट कर सके
                mobileInput.dispatchEvent(new Event('input', { bubbles: true }));

                // सबमिट बटन पर क्लिक करें
                submitButton.click();
                console.log("OCEAN: Mobile number submitted. Waiting for OTP page.");
            }
        }
    });
}

/**
 * OTP भरने का सिग्नल सुनना।
 * यह लिस्नर अब स्मार्ट है और दोनों OTP पेजों को हैंडल कर सकता है।
 */
document.addEventListener('OTP_FILLED', () => {
    console.log("OCEAN: 'OTP_FILLED' signal received.");
    
    // प्राथमिकता 1: क्या "Pay Now" बटन मौजूद है? (यह फाइनल OTP पेज होगा)
    const finalPayButton = document.querySelector('input[value="Pay Now"]');
    if (finalPayButton) {
        console.log("OCEAN: Final 'Pay Now' button found. Clicking it.");
        setTimeout(() => {
            finalPayButton.click();
        }, 500); // 0.5 सेकंड का विलंब
        return; // काम खत्म
    }

    // प्राथमिकता 2: अगर ऊपर वाला बटन नहीं मिला, तो क्या पहला OTP सबमिट बटन है?
    const firstOtpSubmit = document.querySelector('input#verifyotpid');
    if (firstOtpSubmit) {
        console.log("OCEAN: First OTP Submit button found. Clicking it.");
        setTimeout(() => {
            firstOtpSubmit.click();
        }, 500); // 0.5 सेकंड का विलंब
        return; // काम खत्म
    }

    console.warn("OCEAN: No known submit/pay button found after OTP was filled.");
});


// --- स्वचालन प्रक्रिया शुरू करें ---
// पेज के पूरी तरह लोड होने के लिए थोड़ा इंतज़ार करें
setTimeout(initializeMobikwikFlow, 1000);