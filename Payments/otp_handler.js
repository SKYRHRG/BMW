console.log("OTP Handler script loaded and ready.");

// बैकग्राउंड स्क्रिप्ट से संदेश सुनने के लिए लिस्नर
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    // जांचें कि क्या यह OTP भरने का संदेश है
    if (request.type === 'FILL_OTP' && request.otp) {
        console.log(`OTP (${request.otp}) प्राप्त हुआ। इसे पेज पर भरने का प्रयास किया जा रहा है।`);
        fillOtpOnPage(request.otp);
        sendResponse({status: "OTP received by handler"});
    }
    return true;
});

function fillOtpOnPage(otp) {
    const otpSelectors = [
        '#TranRequestManagerFG\\.ONE_TIME_PASSWORD__',   // ✅ HDFC/ICICI-specific
        'input[name="TranRequestManagerFG.ONE_TIME_PASSWORD__"]',
        'input[name="securityPassword"]',
        'input#otpinput',
        'input[autocomplete="one-time-code"]',
        'input[id*="otp"]',
        'input[name*="otp"]',
        'input[id*="OTP"]',
        'input[name*="OTP"]'
    ];

    let otpInput = null;
    for (const selector of otpSelectors) {
        otpInput = document.querySelector(selector);
        if (otpInput) {
            console.log(`OTP इनपुट फील्ड मिला: ${selector}`);
            break;
        }
    }

    if (otpInput) {
        // ✅ Native setter for React/Angular compatibility
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(otpInput, otp);

        // ✅ Dispatch input events
        otpInput.dispatchEvent(new Event('input', { bubbles: true }));
        otpInput.dispatchEvent(new Event('change', { bubbles: true }));
        otpInput.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));

        console.log("✅ OTP सफलतापूर्वक भरा गया और इवेंट्स भेजे गए।");

        // ✅ Signal that OTP is filled
        document.dispatchEvent(new CustomEvent('OTP_FILLED'));
        console.log("✅ Custom event 'OTP_FILLED' dispatched.");
    } else {
        console.warn("❌ OTP input field नहीं मिला।");
    }
}